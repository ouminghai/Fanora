"use client";

import axios from "axios";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import type { MyCollection, NftApplication } from "@/lib/api/types";

const statusLabels: Record<string, string> = {
  NOT_CONFIGURED: "等待测试网配置",
  PENDING: "等待提交",
  SUBMITTED: "已提交链上",
  CONFIRMING: "确认中",
  CONFIRMED: "已确认",
  RETRYABLE: "等待重试",
  FAILED: "同步失败",
  DRAFT: "草稿",
  UNDER_REVIEW: "审核中",
  APPROVED: "已批准",
  REJECTED: "已拒绝",
  PINNING: "固定到 IPFS",
  MINTING: "铸造中",
  MINTED: "已铸造",
};

function errorText(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail || "请求暂时没有完成。";
  if (error instanceof Error) return error.message;
  return "请求暂时没有完成。";
}

function Status({ value }: { value: string }) {
  const active = ["CONFIRMED", "MINTED"].includes(value);
  return (
    <span className={`inline-flex items-center gap-2 text-xs font-semibold ${active ? "text-green" : "text-accent"}`}>
      <span className={`h-2 w-2 rounded-full ${active ? "bg-green" : "bg-accent"}`} />
      {statusLabels[value] || value}
    </span>
  );
}

export default function CollectionDashboard() {
  const router = useRouter();
  const { user, status } = useAuth();
  const [collection, setCollection] = useState<MyCollection | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [imageData, setImageData] = useState("");
  const [form, setForm] = useState({ name: "", description: "", theme: "", copyright: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get<MyCollection>("/nft/me");
      setCollection(response.data);
    } catch (error) {
      setNotice(errorText(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (status === "anonymous" || status === "error") router.replace("/login");
    if (status === "authenticated") void load();
  }, [load, router, status]);

  const syncIdentity = async () => {
    setBusy("identity");
    setNotice(null);
    try {
      const response = await api.post<MyCollection>("/nft/identity/sync");
      setCollection(response.data);
      setNotice(response.data.identity?.status === "CONFIRMED" ? "链上会员身份已同步。" : "同步任务已记录，可稍后重试。");
    } catch (error) {
      setNotice(errorText(error));
    } finally {
      setBusy(null);
    }
  };

  const chooseImage = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 5_000_000) {
      setNotice("图片仅支持 JPEG、PNG、WebP，且不能超过 5 MB。");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setImageData(String(reader.result || ""));
    reader.readAsDataURL(file);
  };

  const createApplication = async (event: FormEvent) => {
    event.preventDefault();
    if (!imageData) {
      setNotice("请先选择徽章图片。");
      return;
    }
    setBusy("application");
    setNotice(null);
    try {
      const created = await api.post<NftApplication>("/nft/applications", {
        name: form.name,
        description: form.description,
        theme: form.theme,
        copyright_declaration: form.copyright,
        public_attributes: [{ trait_type: "Theme", value: form.theme }],
        image_data_url: imageData,
      });
      await api.post(`/nft/applications/${created.data.id}/submit`);
      setForm({ name: "", description: "", theme: "", copyright: "" });
      setImageData("");
      setNotice("纪念徽章申请已提交审核。");
      await load();
    } catch (error) {
      setNotice(errorText(error));
    } finally {
      setBusy(null);
    }
  };

  if (!user || loading) {
    return <main className="flex min-h-screen items-center justify-center bg-[#f7f7fb] pt-24 dark:bg-jacarta-900"><span className="mr-3 h-5 w-5 animate-spin rounded-full border-2 border-accent/25 border-t-accent" />正在读取链上收藏…</main>;
  }

  const identity = collection?.identity;
  return (
    <main className="min-h-screen bg-[#f7f7fb] pb-24 pt-28 dark:bg-jacarta-900">
      <div className="mx-auto max-w-6xl px-5">
        <div className="flex flex-col justify-between gap-4 border-b border-jacarta-100 pb-6 dark:border-white/10 sm:flex-row sm:items-end">
          <div><p className="text-xs font-bold uppercase text-accent">Onchain collection</p><h1 className="mt-2 font-display text-3xl font-semibold text-jacarta-700 dark:text-white">我的 Fanora 收藏</h1><p className="mt-2 text-sm text-jacarta-500 dark:text-jacarta-300">Monad Testnet · 身份、纪念卡与限定徽章</p></div>
          <button type="button" onClick={() => void syncIdentity()} disabled={busy === "identity" || !user.is_official_member} className="rounded-lg bg-accent px-5 py-3 text-sm font-semibold text-white disabled:opacity-45">{busy === "identity" ? "同步中…" : "同步链上身份"}</button>
        </div>

        {notice && <div className="mt-5 rounded-lg border border-accent/20 bg-accent/5 px-4 py-3 text-sm text-jacarta-700 dark:text-white">{notice}</div>}

        {!user.is_official_member ? <div className="mt-8 border-l-4 border-accent bg-white p-6 dark:bg-jacarta-800"><h2 className="font-display text-xl font-semibold dark:text-white">尚未激活会员身份</h2><p className="mt-2 text-sm text-jacarta-500 dark:text-jacarta-300">通过付款合约缴纳当前会费后，系统才能铸造不可转移的会员身份。</p><Link href="/membership/join" className="mt-5 inline-flex rounded-lg bg-accent px-5 py-3 text-sm font-semibold text-white">前往入会</Link></div> : (
          <section className="mt-8 grid gap-6 lg:grid-cols-[360px_1fr]">
            <div className="overflow-hidden rounded-lg bg-[#100b24] text-white shadow-lg">
              <div className="relative aspect-square bg-black/20">{identity?.image_url ? <Image fill unoptimized src={identity.image_url} alt={`${user.level} 会员身份`} className="object-cover" /> : <Image fill src="/img/badges/new.png" alt="会员身份等待同步" className="object-cover opacity-35" />}</div>
              <div className="p-5"><div className="flex items-center justify-between"><Status value={identity?.status || collection?.identity_sync_status || "NOT_CONFIGURED"} /><span className="font-mono text-xs text-white/45">#{identity?.token_id ?? "--"}</span></div><h2 className="mt-4 font-display text-2xl font-semibold">{user.level}</h2><p className="mt-2 text-sm text-white/60">不可转移的 Fanora 会员身份</p><div className="mt-5 grid grid-cols-2 gap-3 border-t border-white/10 pt-4 text-xs"><div><p className="text-white/40">Level ID</p><p className="mt-1 font-semibold">{identity?.level_id ?? "--"}</p></div><div><p className="text-white/40">Metadata</p><p className="mt-1 font-semibold">v{identity?.metadata_version ?? 1}</p></div></div>{identity?.explorer_url && <a href={identity.explorer_url} target="_blank" rel="noreferrer" className="mt-5 block text-sm font-semibold text-accent-lighter">在 Monad 浏览器查看 ↗</a>}</div>
            </div>
            <div className="rounded-lg bg-white p-6 dark:bg-jacarta-800"><h2 className="font-display text-xl font-semibold text-jacarta-700 dark:text-white">身份同步说明</h2><div className="mt-5 grid gap-4 text-sm text-jacarta-500 dark:text-jacarta-300 sm:grid-cols-2"><div className="border-l-2 border-accent pl-4"><p className="font-semibold text-jacarta-700 dark:text-white">等级图片</p><p className="mt-1">直接读取 membership_levels 对应图片并固定到 Pinata。</p></div><div className="border-l-2 border-green pl-4"><p className="font-semibold text-jacarta-700 dark:text-white">等级升级</p><p className="mt-1">积分规则决定等级，同一 tokenId 更新 metadata，不重新铸造。</p></div></div>{identity?.metadata_uri && <p className="mt-6 break-all rounded-lg bg-jacarta-50 p-4 font-mono text-xs dark:bg-white/5">{identity.metadata_uri}</p>}</div>
          </section>
        )}

        <section className="mt-12"><div className="flex items-end justify-between"><div><p className="text-xs font-bold uppercase text-accent">Collectibles</p><h2 className="mt-2 font-display text-2xl font-semibold text-jacarta-700 dark:text-white">纪念资产</h2></div><span className="text-sm text-jacarta-400">{collection?.collectibles.length || 0} 项</span></div>{collection?.collectibles.length ? <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{collection.collectibles.map((item) => <article key={item.token_type_id} className="overflow-hidden rounded-lg bg-white shadow-sm dark:bg-jacarta-800"><div className="relative aspect-square bg-jacarta-100 dark:bg-white/5">{item.image_url && <Image fill unoptimized src={item.image_url} alt={item.name} className="object-cover" />}</div><div className="p-5"><Status value={item.status} /><h3 className="mt-3 font-display text-lg font-semibold dark:text-white">{item.name}</h3><p className="mt-2 line-clamp-2 text-sm text-jacarta-500 dark:text-jacarta-300">{item.description}</p></div></article>)}</div> : <p className="mt-6 border-y border-jacarta-100 py-10 text-center text-sm text-jacarta-400 dark:border-white/10">还没有获得纪念卡或限定 Badge。</p>}</section>

        {user.is_official_member && <section className="mt-12 grid gap-8 lg:grid-cols-[1fr_.8fr]"><form onSubmit={createApplication} className="rounded-lg bg-white p-6 dark:bg-jacarta-800"><p className="text-xs font-bold uppercase text-accent">Custom badge</p><h2 className="mt-2 font-display text-2xl font-semibold dark:text-white">申请自定义纪念徽章</h2><div className="mt-6 grid gap-4 sm:grid-cols-2"><input required minLength={2} maxLength={100} value={form.name} onChange={(event) => setForm({...form, name: event.target.value})} placeholder="徽章名称" className="rounded-lg border-jacarta-100 dark:border-white/10 dark:bg-white/5" /><input required minLength={2} maxLength={120} value={form.theme} onChange={(event) => setForm({...form, theme: event.target.value})} placeholder="纪念主题" className="rounded-lg border-jacarta-100 dark:border-white/10 dark:bg-white/5" /></div><textarea required minLength={10} maxLength={1000} rows={4} value={form.description} onChange={(event) => setForm({...form, description: event.target.value})} placeholder="描述这枚徽章纪念的故事" className="mt-4 w-full rounded-lg border-jacarta-100 dark:border-white/10 dark:bg-white/5" /><textarea required minLength={10} maxLength={500} rows={2} value={form.copyright} onChange={(event) => setForm({...form, copyright: event.target.value})} placeholder="版权声明：确认你拥有或获准使用该图片" className="mt-4 w-full rounded-lg border-jacarta-100 dark:border-white/10 dark:bg-white/5" /><label className="mt-4 flex cursor-pointer items-center justify-center rounded-lg border border-dashed border-accent/40 px-4 py-4 text-sm font-semibold text-accent">{imageData ? "已选择图片，点击可更换" : "选择徽章图片"}<input type="file" accept="image/jpeg,image/png,image/webp" onChange={chooseImage} className="hidden" /></label><button disabled={busy === "application"} className="mt-5 rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy === "application" ? "提交中…" : "提交审核"}</button></form><div><p className="text-xs font-bold uppercase text-accent">Applications</p><h2 className="mt-2 font-display text-2xl font-semibold dark:text-white">申请记录</h2><div className="mt-5 space-y-3">{collection?.applications.length ? collection.applications.map((item) => <div key={item.id} className="rounded-lg bg-white p-4 dark:bg-jacarta-800"><div className="flex items-center justify-between gap-3"><p className="font-semibold dark:text-white">{item.name}</p><Status value={item.status} /></div>{item.rejection_reason && <p className="mt-2 text-sm text-red">{item.rejection_reason}</p>}</div>) : <p className="text-sm text-jacarta-400">暂无申请。</p>}</div></div></section>}
      </div>
    </main>
  );
}
