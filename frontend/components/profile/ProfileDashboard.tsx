"use client";

import axios from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from "react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import { useAuth } from "@/components/providers/AuthProvider";
import PrivateKeyExportModal from "./PrivateKeyExportModal";
import UserAvatar from "./UserAvatar";
import { api } from "@/lib/api/client";
import type { Community, FanoraUser } from "@/lib/api/types";

const fieldClass =
  "w-full rounded-xl border border-jacarta-100 bg-white px-4 py-3 text-jacarta-700 outline-none transition-all placeholder:text-jacarta-300 focus:border-accent focus:ring-2 focus:ring-accent/10 dark:border-white/10 dark:bg-white/[.06] dark:text-white";

function errorMessage(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail || "保存失败，请稍后再试。";
  return "保存失败，请稍后再试。";
}

function shortAddress(address: string) {
  return `${address.slice(0, 8)}…${address.slice(-6)}`;
}

export default function ProfileDashboard() {
  const router = useRouter();
  const { user, status, refreshUser, logout, exportPrivateKey } = useAuth();
  const [form, setForm] = useState({
    display_name: "",
    username: "",
    avatar_url: "",
    bio: "",
    locale: "zh-CN",
    profile_visibility: "public" as "public" | "private",
  });
  const [communities, setCommunities] = useState<Community[]>([]);
  const [saving, setSaving] = useState(false);
  const [joining, setJoining] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [showPrivateKeyExport, setShowPrivateKeyExport] = useState(false);

  useEffect(() => {
    if (status === "anonymous" || status === "error") router.replace("/login");
  }, [router, status]);

  useEffect(() => {
    if (!user) return;
    setForm({
      display_name: user.display_name || "",
      username: user.username || "",
      avatar_url: user.avatar_url || "",
      bio: user.bio || "",
      locale: user.locale || "zh-CN",
      profile_visibility: user.profile_visibility,
    });
    api.get<Community[]>("/communities").then((response) => setCommunities(response.data)).catch(() => undefined);
  }, [user]);

  const joinedIds = useMemo(() => new Set(user?.communities.map((community) => community.id) || []), [user]);

  const updateField = (field: keyof typeof form, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setNotice(null);
  };

  const selectAvatar = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!(["image/jpeg", "image/png", "image/webp", "image/gif"].includes(file.type)) || file.size > 1024 * 1024) {
      setNotice({ kind: "error", text: "头像仅支持 JPEG、PNG、WebP 或 GIF，且不能超过 1 MB。" });
      return;
    }
    const reader = new FileReader();
    reader.onload = () => updateField("avatar_url", String(reader.result || ""));
    reader.readAsDataURL(file);
  };

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    try {
      await api.patch<FanoraUser>("/users/me", {
        ...form,
        username: form.username || null,
        avatar_url: form.avatar_url || null,
        bio: form.bio || null,
      });
      await refreshUser();
      setNotice({ kind: "success", text: "资料已同步到 Fanora 身份。" });
    } catch (error) {
      setNotice({ kind: "error", text: errorMessage(error) });
    } finally {
      setSaving(false);
    }
  };

  const join = async (community: Community) => {
    setJoining(community.id);
    setNotice(null);
    try {
      await api.post(`/communities/${community.id}/join`);
      await refreshUser();
      setNotice({ kind: "success", text: `已加入 ${community.name}。` });
    } catch (error) {
      setNotice({ kind: "error", text: errorMessage(error) });
    } finally {
      setJoining(null);
    }
  };

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#F8F7FF] pt-24 dark:bg-jacarta-900">
        <div className="flex items-center gap-3 text-jacarta-500 dark:text-jacarta-200">
          <span className="h-6 w-6 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
          正在读取你的 Fanora 身份…
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#F8F7FF] pb-24 pt-32 dark:bg-jacarta-900">
      <div className="mx-auto max-w-6xl px-6">
        <section className="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-[#5D32D5] via-accent to-[#45BFEF] p-8 text-white shadow-accent-volume md:p-12">
          <div className="absolute -right-20 -top-24 h-72 w-72 animate-pulse rounded-full border-[42px] border-white/10" />
          <div className="relative flex flex-col justify-between gap-8 md:flex-row md:items-end">
            <div className="flex items-center gap-6">
              <UserAvatar
                avatarUrl={user.avatar_url}
                seed={user.id}
                displayName={user.display_name}
                className="h-24 w-24 rounded-3xl border-4 border-white/30 shadow-xl"
              />
              <div>
                <div className="mb-2 flex flex-wrap gap-2">
                  {user.roles.map((role) => (
                    <span key={role} className="rounded-full bg-white/15 px-3 py-1 text-xs font-bold uppercase tracking-wider backdrop-blur">{role}</span>
                  ))}
                </div>
                <h1 className="font-display text-3xl font-semibold md:text-5xl">{user.display_name || "完善你的 Fanora 身份"}</h1>
                <button
                  type="button"
                  onClick={() => navigator.clipboard.writeText(user.primary_wallet.address)}
                  className="mt-3 font-mono text-sm text-white/75 transition-colors hover:text-white"
                >
                  {shortAddress(user.primary_wallet.address)} · 主钱包
                </button>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="min-w-24 rounded-2xl bg-black/10 p-4 backdrop-blur">
                <p className="text-xs text-white/65">等级</p>
                <p className="mt-1 font-display text-lg font-semibold">{user.level}</p>
              </div>
              <div className="min-w-24 rounded-2xl bg-black/10 p-4 backdrop-blur">
                <p className="text-xs text-white/65">Fan Token</p>
                <FanTokenAmount
                  amount={user.fan_token_balance}
                  className="mt-1 justify-center font-display text-lg font-semibold"
                />
              </div>
              <div className="min-w-24 rounded-2xl bg-black/10 p-4 backdrop-blur">
                <p className="text-xs text-white/65">类型</p>
                <p className="mt-1 font-display text-lg font-semibold">{user.fan_type}</p>
              </div>
            </div>
          </div>
        </section>

        {notice && (
          <div className={`mt-6 animate-[fadeIn_.25s_ease-out] rounded-2xl border px-5 py-4 text-sm font-medium ${notice.kind === "success" ? "border-green/20 bg-green/10 text-green" : "border-red/20 bg-red/10 text-red"}`}>
            {notice.text}
          </div>
        )}

        <div className="mt-8 grid gap-8 lg:grid-cols-[1.15fr_.85fr]">
          <form onSubmit={save} className="rounded-[2rem] bg-white p-7 shadow-sm dark:bg-jacarta-800 md:p-9">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[.18em] text-accent">Identity profile</p>
                <h2 className="mt-2 font-display text-2xl font-semibold text-jacarta-700 dark:text-white">维护用户信息</h2>
              </div>
              <span className={`h-3 w-3 rounded-full ${user.onboarding_completed ? "bg-green" : "animate-pulse bg-orange"}`} />
            </div>
            <div className="mt-8 grid gap-6 sm:grid-cols-2">
              <label className="text-sm font-semibold text-jacarta-700 dark:text-white">
                昵称
                <input required minLength={2} maxLength={80} value={form.display_name} onChange={(event) => updateField("display_name", event.target.value)} className={`${fieldClass} mt-2`} placeholder="你希望大家如何称呼你" />
              </label>
              <label className="text-sm font-semibold text-jacarta-700 dark:text-white">
                用户名
                <input minLength={3} maxLength={40} pattern="[a-z0-9_]+" value={form.username} onChange={(event) => updateField("username", event.target.value.toLowerCase())} className={`${fieldClass} mt-2`} placeholder="fanora_name" />
              </label>
            </div>
            <label className="mt-6 block text-sm font-semibold text-jacarta-700 dark:text-white">
              个人简介
              <textarea rows={4} maxLength={280} value={form.bio} onChange={(event) => updateField("bio", event.target.value)} className={`${fieldClass} mt-2 resize-none`} placeholder="分享你支持的创作者和加入社区的故事…" />
              <span className="mt-1 block text-right text-xs font-normal text-jacarta-400">{form.bio.length}/280</span>
            </label>
            <div className="mt-6 grid gap-6 sm:grid-cols-2">
              <label className="text-sm font-semibold text-jacarta-700 dark:text-white">
                头像
                <span className="mt-2 flex cursor-pointer items-center justify-center rounded-xl border border-dashed border-accent/40 bg-accent/5 px-4 py-3 text-accent transition-colors hover:bg-accent/10">
                  选择图片（最大 1 MB）
                  <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={selectAvatar} className="hidden" />
                </span>
              </label>
              <label className="text-sm font-semibold text-jacarta-700 dark:text-white">
                公开范围
                <select value={form.profile_visibility} onChange={(event) => updateField("profile_visibility", event.target.value)} className={`${fieldClass} mt-2`}>
                  <option value="public">公开粉丝资料</option>
                  <option value="private">仅自己可见</option>
                </select>
              </label>
            </div>
            <button disabled={saving} type="submit" className="group relative mt-8 flex min-w-44 items-center justify-center overflow-hidden rounded-full bg-accent px-8 py-3.5 font-semibold text-white shadow-accent-volume transition-all hover:-translate-y-0.5 hover:bg-accent-dark disabled:cursor-wait disabled:opacity-70">
              {saving && <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white/35 border-t-white" />}
              {saving ? "正在同步…" : "保存个人资料"}
            </button>
          </form>

          <aside className="space-y-8">
            <section className="rounded-[2rem] bg-white p-7 shadow-sm dark:bg-jacarta-800">
              <p className="text-xs font-bold uppercase tracking-[.18em] text-accent">Wallet identity</p>
              <h2 className="mt-2 font-display text-xl font-semibold text-jacarta-700 dark:text-white">强制钱包身份已激活</h2>
              <div className="mt-5 rounded-2xl border border-green/20 bg-green/5 p-5">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-green text-lg text-white">✓</span>
                  <div>
                    <p className="font-semibold text-jacarta-700 dark:text-white">{user.primary_wallet.wallet_type === "embedded" ? "Web3Auth 嵌入式钱包" : "外部钱包"}</p>
                    <p className="mt-1 text-xs text-jacarta-500 dark:text-jacarta-300">私钥由钱包提供商管理，Fanora 不保存。</p>
                  </div>
                </div>
              </div>
              {user.primary_wallet.wallet_type === "embedded" ? (
                <button
                  type="button"
                  onClick={() => setShowPrivateKeyExport(true)}
                  className="mt-4 w-full rounded-xl border border-orange/30 bg-orange/5 py-3 text-sm font-semibold text-orange transition-all hover:-translate-y-0.5 hover:bg-orange/10"
                >
                  导出钱包私钥
                </button>
              ) : (
                <p className="mt-4 rounded-xl bg-jacarta-50 px-4 py-3 text-center text-xs leading-5 text-jacarta-500 dark:bg-white/[.04] dark:text-jacarta-300">
                  当前是外部钱包，请在钱包应用的账户设置中导出私钥。
                </p>
              )}
              <button type="button" onClick={() => void logout()} className="mt-4 w-full rounded-xl border border-jacarta-100 py-3 text-sm font-semibold text-jacarta-500 transition-colors hover:border-red/30 hover:bg-red/5 hover:text-red dark:border-white/10">退出当前身份</button>
            </section>

            <section className="rounded-[2rem] bg-white p-7 shadow-sm dark:bg-jacarta-800">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[.18em] text-accent">Official community</p>
                  <h2 className="mt-2 font-display text-xl font-semibold text-jacarta-700 dark:text-white">Fanora 官方社区</h2>
                </div>
                <span className="rounded-full bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">已加入 {joinedIds.size}</span>
              </div>
              <div className="mt-5 space-y-3">
                {communities.length === 0 ? (
                  <p className="rounded-xl bg-jacarta-50 p-4 text-sm leading-6 text-jacarta-500 dark:bg-white/[.04] dark:text-jacarta-300">官方社区正在初始化，请稍后刷新。</p>
                ) : communities.map((community) => {
                  const joined = joinedIds.has(community.id);
                  return (
                    <div key={community.id} className="flex items-center gap-3 rounded-2xl border border-jacarta-100 p-3 dark:border-white/10">
                      <div className="h-11 w-11 shrink-0 rounded-xl bg-accent/10 bg-cover bg-center" style={{ backgroundImage: `url(${community.logo_url})` }} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-semibold text-jacarta-700 dark:text-white">{community.name}</p>
                        <p className="truncate text-xs text-jacarta-400">{community.description}</p>
                      </div>
                      <button type="button" disabled={joined || joining === community.id} onClick={() => void join(community)} className="rounded-full bg-accent/10 px-3 py-2 text-xs font-semibold text-accent transition-colors hover:bg-accent hover:text-white disabled:cursor-default disabled:opacity-60">
                        {joined ? "已加入" : joining === community.id ? "加入中…" : "加入"}
                      </button>
                    </div>
                  );
                })}
              </div>
              <Link href="/community" className="mt-4 block rounded-xl border border-jacarta-100 py-3 text-center text-sm font-semibold text-jacarta-500 transition-colors hover:border-accent hover:text-accent dark:border-white/10 dark:text-white">
                进入签到、任务与创作社区
              </Link>
            </section>
          </aside>
        </div>
        <div className="mt-8 text-center">
          <Link href="/" className="text-sm font-semibold text-jacarta-500 transition-colors hover:text-accent">← 返回 Fanora 首页</Link>
        </div>
      </div>
      <PrivateKeyExportModal
        open={showPrivateKeyExport}
        walletAddress={user.primary_wallet.address}
        onClose={() => setShowPrivateKeyExport(false)}
        onExport={exportPrivateKey}
      />
    </main>
  );
}
