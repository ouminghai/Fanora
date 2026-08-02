"use client";

import axios from "axios";
import { Check, LogOut, RadioTower, RefreshCw, Save, ShieldCheck, UserRound, Wallet } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import UserAvatar from "@/components/profile/UserAvatar";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import type { Community, FanoraUser } from "@/lib/api/types";
import styles from "./CollectionProfilePanel.module.css";

function errorMessage(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail || "保存失败，请稍后再试。";
  return "保存失败，请稍后再试。";
}

export default function CollectionProfilePanel({ onSaved }: { onSaved?: () => Promise<void> | void }) {
  const { user, refreshUser, logout } = useAuth();
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
    void api.get<Community[]>("/communities")
      .then((response) => setCommunities(response.data))
      .catch(() => setCommunities([]));
  }, [user]);

  const joinedIds = useMemo(() => new Set(user?.communities.map((community) => community.id) || []), [user]);

  const updateField = (field: keyof typeof form, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setNotice(null);
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
      await onSaved?.();
      setNotice({ kind: "success", text: "身份资料已保存；如会员卡文字变化，系统会自动更新链上卡面。" });
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

  if (!user) return null;

  return (
    <section className={styles.profileShell}>
      <header className={styles.profileHud}>
        <div className={styles.profileAvatar}>
          <UserAvatar avatarUrl={user.avatar_url} seed={user.id} displayName={user.display_name} className={styles.avatarImage} />
          <span className={styles.avatarStatusBadge}><Check /></span>
        </div>
        <div>
          <p>IDENTITY PROFILE // PERSONAL DATA NODE</p>
          <h2>维护你的链上身份资料</h2>
          <span>资料会同步到 Fanora 身份系统；昵称或用户名变化会触发会员卡更新。</span>
        </div>
        <div className={styles.profileStatus}><i /> PROFILE NODE ONLINE</div>
      </header>

      {notice ? <div className={`${styles.notice} ${notice.kind === "error" ? styles.noticeError : ""}`}>{notice.text}</div> : null}

      <div className={styles.profileGrid}>
        <form onSubmit={save} className={styles.dataPanel}>
          <div className={styles.panelTitle}><span><UserRound /> IDENTITY DATA</span><small>EDITABLE</small></div>
          <div className={styles.fieldGrid}>
            <label>昵称<input required minLength={2} maxLength={80} value={form.display_name} onChange={(event) => updateField("display_name", event.target.value)} placeholder="你希望大家如何称呼你" /></label>
            <label>用户名<input minLength={3} maxLength={40} pattern="[a-z0-9_]+" value={form.username} onChange={(event) => updateField("username", event.target.value.toLowerCase())} placeholder="fanora_name" /></label>
          </div>
          <label className={styles.fullField}>个人简介<textarea rows={5} maxLength={280} value={form.bio} onChange={(event) => updateField("bio", event.target.value)} placeholder="分享你支持的创作者和加入社区的故事…" /><small>{form.bio.length}/280</small></label>
          <div className={styles.fieldGrid}>
            <label>公开范围<select value={form.profile_visibility} onChange={(event) => updateField("profile_visibility", event.target.value)}><option value="public">公开粉丝资料</option><option value="private">仅自己可见</option></select></label>
            <label>界面语言<select value={form.locale} onChange={(event) => updateField("locale", event.target.value)}><option value="zh-CN">简体中文</option><option value="en-US">English</option></select></label>
          </div>
          <button type="submit" disabled={saving} className={styles.saveButton}>{saving ? <RefreshCw className="animate-spin" /> : <Save />}{saving ? "正在同步身份…" : "保存个人资料"}</button>
        </form>

        <aside className={styles.sideColumn}>
          <section className={styles.walletPanel}>
            <div className={styles.panelTitle}><span><Wallet /> WALLET IDENTITY</span><ShieldCheck /></div>
            <p>主钱包</p>
            <strong title={user.primary_wallet.address}>{user.primary_wallet.address}</strong>
            <div><span>NETWORK</span><b>MONAD</b><span>ACCESS</span><b>SELF-CUSTODY</b></div>
            <button type="button" onClick={() => void logout()}><LogOut />退出当前身份</button>
          </section>

          <section className={styles.communityPanel}>
            <div className={styles.panelTitle}><span><RadioTower /> COMMUNITY NODES</span><small>{joinedIds.size} JOINED</small></div>
            <div className={styles.communityList}>
              {communities.length ? communities.map((community) => {
                const joined = joinedIds.has(community.id);
                return <div key={community.id}><span style={{ backgroundImage: `url(${community.logo_url})` }} /><p><strong>{community.name}</strong><small>{community.description}</small></p><button type="button" disabled={joined || joining === community.id} onClick={() => void join(community)}>{joined ? "已连接" : joining === community.id ? "连接中" : "连接"}</button></div>;
              }) : <p className={styles.emptyState}>社区节点正在初始化。</p>}
            </div>
            <Link href="/community">进入社区网络 ↗</Link>
          </section>
        </aside>
      </div>
    </section>
  );
}
