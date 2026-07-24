"use client";

import axios from "axios";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import FanNftMarket from "@/components/nft/FanNftMarket";
import FanProfileSummary from "@/components/profile/FanProfileSummary";
import UserAvatar from "@/components/profile/UserAvatar";
import { api } from "@/lib/api/client";
import type { CollectibleNft, FanNftListing, PublicCollection, PublicFanProfileAnalysis } from "@/lib/api/types";

function errorText(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail || "这个用户主页暂时无法打开。";
  return error instanceof Error ? error.message : "这个用户主页暂时无法打开。";
}

function formatDate(value: string | null) {
  if (!value) return "尚未正式入会";
  return new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric" }).format(new Date(value));
}

function Status({ value }: { value: string }) {
  const confirmed = ["CONFIRMED", "MINTED"].includes(value);
  const failed = ["FAILED", "REJECTED"].includes(value);
  return (
    <span className={`inline-flex items-center gap-2 text-xs font-semibold ${confirmed ? "text-green" : failed ? "text-red" : "text-accent"}`}>
      <span className={`h-2 w-2 rounded-full ${confirmed ? "bg-green" : failed ? "bg-red" : "bg-accent"}`} />
      {value}
    </span>
  );
}

function CollectibleCard({ item }: { item: CollectibleNft }) {
  return (
    <article className="overflow-hidden rounded-lg border border-jacarta-100 bg-white dark:border-white/10 dark:bg-jacarta-700">
      <div className="relative aspect-square bg-jacarta-100 dark:bg-white/5">
        {item.image_url ? (
          <Image fill unoptimized src={item.image_url} alt={item.name} sizes="(max-width: 639px) 100vw, 25vw" className="object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-jacarta-400">等待 NFT 图片</div>
        )}
      </div>
      <div className="p-5">
        <div className="flex items-center justify-between gap-3">
          <Status value={item.status} />
          <span className="font-mono text-xs text-jacarta-400">#{item.token_id}</span>
        </div>
        <h3 className="mt-3 font-display text-lg font-semibold text-jacarta-700 dark:text-white">{item.name}</h3>
        <p className="mt-2 line-clamp-2 min-h-10 text-sm text-jacarta-500 dark:text-jacarta-300">{item.description}</p>
      </div>
    </article>
  );
}

function CreationCard({ item, onOpen }: { item: FanNftListing; onOpen: (id: string) => void }) {
  return (
    <button type="button" onClick={() => onOpen(item.id)} className="group flex h-full flex-wrap gap-5 rounded-lg bg-white p-5 text-left transition-transform hover:-translate-y-0.5 dark:bg-jacarta-700 lg:flex-nowrap">
      <span className="relative block h-28 w-28 shrink-0 overflow-hidden rounded-lg bg-jacarta-100 dark:bg-white/5">
        {item.image_url ? <Image fill unoptimized src={item.image_url} alt={item.name} sizes="112px" className="object-cover" /> : null}
      </span>
      <span className="min-w-0 flex-1">
        <span className="mb-2 flex text-orange" aria-hidden="true">★★★★★</span>
        <span className="block font-display text-base font-semibold text-jacarta-700 group-hover:text-accent dark:text-white">{item.name}</span>
        <span className="mt-2 line-clamp-3 block text-sm leading-6 text-jacarta-500 dark:text-jacarta-300">{item.description}</span>
        <FanTokenAmount amount={item.price_fan_tokens} showSymbol className="mt-4 text-sm font-semibold text-accent" />
      </span>
    </button>
  );
}

export default function PublicCollectionDashboard({ userId }: { userId: string }) {
  const [collection, setCollection] = useState<PublicCollection | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [fanProfile, setFanProfile] = useState<PublicFanProfileAnalysis | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [response, profileResponse] = await Promise.all([
        api.get<PublicCollection>(`/nft/users/${userId}`),
        api.get<PublicFanProfileAnalysis>(`/profile/users/${userId}`).catch(() => null),
      ]);
      setCollection(response.data);
      setFanProfile(profileResponse?.data || null);
      setNotice(null);
    } catch (error) {
      setNotice(errorText(error));
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { void load(); }, [load]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f7f7fb] pt-24 dark:bg-jacarta-900 dark:text-white">
        <span className="mr-3 h-5 w-5 animate-spin rounded-full border-2 border-accent/25 border-t-accent" />
        正在读取用户主页...
      </main>
    );
  }

  if (!collection) {
    return (
      <main className="min-h-screen bg-[#f7f7fb] px-5 pb-24 pt-40 text-center dark:bg-jacarta-900 dark:text-white">
        <h1 className="font-display text-3xl font-semibold">主页暂时无法打开</h1>
        <p className="mt-4 text-sm text-jacarta-500 dark:text-jacarta-300">{notice}</p>
        <Link href="/community/creations" className="mt-8 inline-flex rounded-lg bg-accent px-6 py-3 text-sm font-semibold text-white">返回社区</Link>
      </main>
    );
  }

  const { user, identity, collectibles, creations } = collection;
  const identityImage = identity?.is_member_card && identity.image_url ? identity.image_url : "/img/membercard/membercard.jpg";

  return (
    <main className="min-h-screen bg-[#f7f7fb] pb-24 pt-[88px] dark:bg-jacarta-900">
      <div className="community-reveal relative h-[220px] overflow-hidden sm:h-[300px]">
        <Image fill priority src="/img/fanora/eason-concert.webp" alt="Fanora 用户主页封面" sizes="100vw" className="object-cover object-center" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#140d2d]/65 via-transparent to-black/10" />
      </div>

      <section className="community-reveal relative bg-white pb-10 pt-24 [animation-delay:80ms] dark:bg-jacarta-800 sm:pt-28">
        <div className="absolute left-1/2 top-0 z-10 -translate-x-1/2 -translate-y-1/2">
          <div className="relative">
            <UserAvatar avatarUrl={user.avatar_url} seed={user.id} displayName={user.display_name} className="h-32 w-32 rounded-lg border-[5px] border-white shadow-xl dark:border-jacarta-700 sm:h-36 sm:w-36" />
            {user.is_official_member ? <span title="Fanora 正式会员" className="absolute -bottom-1 -right-2 flex h-8 w-8 items-center justify-center rounded-full border-[3px] border-white bg-green text-sm font-bold text-white dark:border-jacarta-700">✓</span> : null}
          </div>
        </div>
        <div className="mx-auto max-w-4xl px-5 text-center">
          <h1 className="font-display text-3xl font-semibold text-jacarta-700 dark:text-white sm:text-4xl">{user.display_name}</h1>
          <p className="mt-3 text-sm text-jacarta-400">{formatDate(user.official_member_since)}加入 Fanora</p>
          <p className="mx-auto mt-5 max-w-xl text-base leading-7 text-jacarta-500 dark:text-jacarta-300">{user.bio || "用每一次参与，留下属于自己的 Proof of Fandom。"}</p>
          <div className="mx-auto mt-7 grid max-w-3xl grid-cols-2 divide-x divide-y divide-jacarta-100 border-y border-jacarta-100 py-5 dark:divide-white/10 dark:border-white/10 sm:grid-cols-4 sm:divide-y-0">
            <div><p className="text-xs text-jacarta-400">会员等级</p><p className="mt-2 font-display font-semibold text-jacarta-700 dark:text-white">{user.level}</p></div>
            <div><p className="text-xs text-jacarta-400">累计 FAN</p><FanTokenAmount amount={user.fan_token_lifetime_earned} showSymbol className="mt-2 justify-center font-display font-semibold text-accent" /></div>
            <div><p className="text-xs text-jacarta-400">链上收藏</p><p className="mt-2 font-display font-semibold text-jacarta-700 dark:text-white">{collectibles.length}</p></div>
            <div><p className="text-xs text-jacarta-400">发布 NFT</p><p className="mt-2 font-display font-semibold text-jacarta-700 dark:text-white">{creations.length}</p></div>
          </div>
        </div>
      </section>

      <div className="community-reveal mx-auto max-w-6xl px-5 pt-10 [animation-delay:160ms]">
        {fanProfile ? <FanProfileSummary profile={fanProfile} ownerLabel="TA 的个人画像" /> : null}
        <div className="mt-8 grid gap-8 lg:grid-cols-[360px_1fr]">
          <aside className="lg:sticky lg:top-28 lg:self-start">
          <article className="overflow-hidden rounded-lg border border-jacarta-100 bg-white shadow-sm dark:border-white/10 dark:bg-jacarta-700">
            <div className="relative aspect-[421/734] bg-[#100b24]">
              <Image fill unoptimized src={identityImage} alt={`${user.display_name} Fanora 会员证`} sizes="360px" className="object-cover" />
            </div>
            <div className="flex items-center justify-between gap-3 px-5 py-4">
              <Status value={identity?.status || (user.is_official_member ? "READY" : "WAITING")} />
              {identity?.explorer_url ? <a href={identity.explorer_url} target="_blank" rel="noreferrer" className="text-xs font-semibold text-accent">链上查看 ↗</a> : null}
            </div>
          </article>
          </aside>

          <div className="space-y-12">
          <section>
            <div className="flex items-end justify-between gap-4">
              <div><p className="text-xs font-bold uppercase text-accent">Published NFT</p><h2 className="mt-2 font-display text-2xl font-semibold text-jacarta-700 dark:text-white">TA 发布的 NFT</h2></div>
            </div>
            {creations.length ? <div className="mt-7 grid gap-6 md:grid-cols-2">{creations.map((item) => <CreationCard key={item.id} item={item} onOpen={setSelectedItemId} />)}</div> : <p className="mt-7 border-y border-jacarta-100 py-12 text-center text-sm text-jacarta-400 dark:border-white/10">暂时还没有公开发布的 NFT。</p>}
          </section>
          <section>
            <div><p className="text-xs font-bold uppercase text-accent">Collected on Monad</p><h2 className="mt-2 font-display text-2xl font-semibold text-jacarta-700 dark:text-white">TA 的链上收藏</h2></div>
            {collectibles.length ? <div className="mt-7 grid gap-6 sm:grid-cols-2 xl:grid-cols-3">{collectibles.map((item) => <CollectibleCard key={item.token_type_id} item={item} />)}</div> : <p className="mt-7 border-y border-jacarta-100 py-12 text-center text-sm text-jacarta-400 dark:border-white/10">收藏仍在等待故事发生。</p>}
          </section>
          </div>
        </div>
      </div>

      {selectedItemId ? (
        <div role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedItemId(null); }} className="community-drawer-backdrop fixed inset-0 z-[1000] flex items-end justify-center bg-[#050619]/75 px-0 pt-5 backdrop-blur-md md:px-8 md:pt-10">
          <section role="dialog" aria-modal="true" aria-label="NFT 详情" className="community-letter-drawer relative flex min-h-[95dvh] max-h-[calc(100dvh-1.25rem)] w-full max-w-7xl flex-col overflow-hidden rounded-t-lg bg-[#f7f7fb] shadow-[0_45px_140px_rgba(0,0,0,.72)] dark:bg-jacarta-900 md:max-h-[calc(100dvh-2.5rem)]" onMouseDown={(event) => event.stopPropagation()}>
            <button type="button" onClick={() => setSelectedItemId(null)} aria-label="关闭 NFT 详情" className="absolute right-4 top-4 z-20 flex h-10 w-10 items-center justify-center rounded-full border border-jacarta-100 bg-white/90 text-2xl leading-none text-jacarta-600 shadow-lg transition-colors hover:border-accent hover:text-accent dark:border-white/15 dark:bg-[#090b23]/85 dark:text-white/75">
              <span aria-hidden="true" className="-translate-y-px">×</span>
            </button>
            <FanNftMarket mode="item" itemId={selectedItemId} variant="drawer" onClose={() => setSelectedItemId(null)} />
          </section>
        </div>
      ) : null}
    </main>
  );
}
