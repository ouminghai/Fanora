"use client";

import axios from "axios";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from "react";
import MarkdownEditor from "@/components/community/MarkdownEditor";
import UserAvatar from "@/components/profile/UserAvatar";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import type { CommunityPostDetail, CommunityPostSummary, OfficialCommunity, PostEngagement } from "@/lib/api/types";

const categories = [
  { id: "all", label: "推荐" },
  { id: "creation", label: "共创" },
  { id: "story", label: "故事" },
  { id: "music", label: "音乐" },
  { id: "discussion", label: "讨论" },
  { id: "bookmarked", label: "我的收藏" },
];
const labels: Record<string, string> = { creation: "共创", story: "故事", music: "音乐", discussion: "讨论" };

function message(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail || "操作没有完成。";
  return error instanceof Error ? error.message : "操作没有完成。";
}

export default function CreationWall() {
  const { user, refreshUser } = useAuth();
  const [posts, setPosts] = useState<CommunityPostSummary[]>([]);
  const [community, setCommunity] = useState<OfficialCommunity | null>(null);
  const [category, setCategory] = useState("all");
  const [composer, setComposer] = useState(false);
  const [columnCount, setColumnCount] = useState(1);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [draft, setDraft] = useState({ title: "", body: "", category: "creation", cover_url: null as string | null });

  const load = useCallback(async () => {
    const [postResponse, communityResponse] = await Promise.all([
      api.get<CommunityPostSummary[]>("/community/posts?limit=50"),
      api.get<OfficialCommunity>("/community"),
    ]);
    setPosts(postResponse.data);
    setCommunity(communityResponse.data);
  }, []);

  useEffect(() => { void load().catch((error) => setNotice(message(error))); }, [load, user]);
  useEffect(() => {
    const updateColumns = () => {
      const width = window.innerWidth;
      setColumnCount(width >= 1202 ? 4 : width >= 1025 ? 3 : width >= 575 ? 2 : 1);
    };
    updateColumns();
    window.addEventListener("resize", updateColumns);
    return () => window.removeEventListener("resize", updateColumns);
  }, []);
  const joined = community?.joined || Boolean(user?.communities.some((item) => item.slug === "fanora-official"));
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requestedCategory = params.get("category");
    if (requestedCategory && categories.some((item) => item.id === requestedCategory)) setCategory(requestedCategory);
    if (params.get("composer") === "1" && user?.is_official_member && joined) setComposer(true);
  }, [joined, user]);
  const visiblePosts = useMemo(() => category === "all" ? posts : category === "bookmarked" ? posts.filter((post) => post.bookmarked) : posts.filter((post) => post.category === category), [category, posts]);
  const masonryColumns = useMemo(() => {
    const columns: Array<Array<{ post: CommunityPostSummary; index: number }>> = Array.from({ length: columnCount }, () => []);
    const heights = Array.from({ length: columnCount }, () => 0);
    visiblePosts.forEach((post, index) => {
      const column = heights.indexOf(Math.min(...heights));
      columns[column].push({ post, index });
      heights[column] += post.cover_url ? (index % 3 === 0 ? 520 : index % 3 === 1 ? 440 : 390) : 320;
    });
    return columns;
  }, [columnCount, visiblePosts]);

  const requireInteraction = () => {
    if (!user) { setNotice("请先登录，再点赞或收藏创作。 "); return false; }
    if (!user.is_official_member) { setNotice("正式入会后可以点赞、收藏和评论。 "); return false; }
    if (!joined) { setNotice("请先加入 Fanora 官方社区。 "); return false; }
    return true;
  };

  const updateEngagement = (engagement: PostEngagement) => setPosts((current) => current.map((post) => post.id === engagement.post_id ? { ...post, ...engagement } : post));
  const toggle = async (post: CommunityPostSummary, action: "like" | "bookmark") => {
    if (!requireInteraction()) return;
    setBusy(`${action}:${post.id}`);
    try {
      const response = await api.post<PostEngagement>(`/community/posts/${post.id}/${action}`);
      updateEngagement(response.data);
    } catch (error) { setNotice(message(error)); } finally { setBusy(null); }
  };

  const selectImage = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp", "image/gif"].includes(file.type) || file.size > 1024 * 1024) { setNotice("首图需为 1 MB 以内的 JPEG、PNG、WebP 或 GIF 图片。 "); return; }
    const reader = new FileReader();
    reader.onload = () => setDraft((current) => ({ ...current, cover_url: String(reader.result) }));
    reader.onerror = () => setNotice("首图读取失败，请重新选择图片。 ");
    reader.readAsDataURL(file);
  };

  const publish = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("publish");
    try {
      const response = await api.post<CommunityPostDetail>("/community/posts", draft);
      setDraft({ title: "", body: "", category: "creation", cover_url: null });
      setComposer(false);
      await Promise.all([load(), refreshUser()]);
      setNotice(`《${response.data.title}》已发布。`);
    } catch (error) { setNotice(message(error)); } finally { setBusy(null); }
  };

  return (
    <main className="web3-page-shell min-h-screen pb-24 pt-28 md:pt-32">
      <div className="container">
        <header className="community-reveal flex flex-col gap-8 rounded-[2.25rem] border border-white/10 bg-[#101436]/95 p-7 text-white shadow-[0_30px_100px_rgba(5,6,25,.4)] md:p-10 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <Link href="/community#creation" className="text-sm font-semibold text-accent-lighter hover:text-white">← 返回官方社区</Link>
            <p className="mt-7 text-xs font-bold uppercase tracking-[.28em] text-accent-light">Creation community</p>
            <h1 className="mt-4 font-display text-4xl font-semibold md:text-6xl">发现粉丝创作</h1>
            <p className="mt-5 text-sm leading-7 text-white/60 md:text-base">用瀑布流浏览故事、歌单和作品。每条创作都支持点赞、收藏和两层评论。</p>
          </div>
          {user?.is_official_member && joined ? <button onClick={() => setComposer((value) => !value)} className="web3-action-button shrink-0 rounded-full px-7 py-3.5 font-semibold text-white">{composer ? "收起发布框" : "+ 发布创作"}</button> : <Link href={user ? "/membership/join" : "/login"} className="web3-action-button shrink-0 rounded-full px-7 py-3.5 text-center font-semibold text-white">{user ? "入会后发布" : "登录后发布"}</Link>}
        </header>

        {notice && <div className="community-reveal mt-5 rounded-2xl border border-accent/20 bg-accent/10 px-5 py-4 text-sm font-semibold text-accent-lighter">{notice}</div>}

        {composer && <form onSubmit={publish} className="community-reveal mt-6 grid gap-6 rounded-[2rem] border border-accent/20 bg-[#111538] p-6 text-white md:grid-cols-[280px_1fr] md:p-8">
          <div>
            <div className="mb-3 flex items-center justify-between"><label className="text-sm font-semibold text-white">首图</label><span className="text-[11px] text-white/30">Base64 · 最大 1 MB</span></div>
            <label className="group relative flex min-h-72 cursor-pointer items-center justify-center overflow-hidden rounded-2xl border border-dashed border-accent/35 bg-accent/5 text-center text-sm text-white/55 transition-colors hover:bg-accent/10">
              {draft.cover_url ? <Image src={draft.cover_url} alt="首图预览" fill sizes="280px" className="object-cover transition-transform duration-500 group-hover:scale-105" /> : <span className="px-5"><span className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-accent/15 text-xl text-accent-lighter">＋</span>点击上传文章首图<br /><small className="mt-2 block text-white/35">JPEG / PNG / WebP / GIF</small></span>}
              <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={selectImage} className="hidden" />
            </label>
            <p className="mt-3 text-xs leading-5 text-white/35">图片会在浏览器中转换为 Base64，作为独立首图字段随文章保存，并展示在详情页正文顶部。</p>
            {draft.cover_url && <button type="button" onClick={() => setDraft((current) => ({ ...current, cover_url: null }))} className="mt-3 w-full rounded-full border border-white/10 py-2 text-xs font-semibold text-white/45 transition-colors hover:border-red/30 hover:text-red">移除首图</button>}
          </div>
          <div>
            <div className="grid gap-4 md:grid-cols-[1fr_150px]"><input required minLength={4} maxLength={120} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="创作标题" className="rounded-xl border-white/10 bg-white/[.06] text-white placeholder:text-white/30" /><select value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value })} className="rounded-xl border-white/10 bg-[#181d49] text-white"><option value="creation">共创</option><option value="story">故事</option><option value="music">音乐</option><option value="discussion">讨论</option></select></div>
            <MarkdownEditor value={draft.body} onChange={(body) => setDraft((current) => ({ ...current, body }))} />
            <button disabled={busy === "publish"} className="web3-action-button mt-4 rounded-full px-7 py-3 font-semibold text-white disabled:opacity-50">{busy === "publish" ? "发布中…" : "发布创作"}</button>
          </div>
        </form>}

        <nav className="community-reveal sticky top-20 z-10 mt-7 flex gap-2 overflow-x-auto rounded-2xl border border-white/10 bg-[#0d102d]/85 p-2 backdrop-blur-xl [animation-delay:100ms]">
          {categories.map((item) => <button key={item.id} onClick={() => setCategory(item.id)} className={`shrink-0 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all ${category === item.id ? "bg-accent text-white" : "text-white/50 hover:bg-white/5 hover:text-white"}`}>{item.label}</button>)}
        </nav>

        <section className="mt-6 grid items-start gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {masonryColumns.map((column, columnIndex) => <div key={columnIndex} className="space-y-5">{column.map(({ post, index }) => (
            <article key={post.id} className="web3-interactive-card community-reveal mb-5 inline-block w-full break-inside-avoid overflow-hidden rounded-[1.5rem] border border-white/10 bg-[#111538] text-white" style={{ animationDelay: `${Math.min(index, 12) * 55}ms` }}>
              <Link href={`/community/posts/${post.id}`} className="group block overflow-hidden">
                {post.cover_url ? <div className={`relative overflow-hidden ${index % 3 === 0 ? "aspect-[4/5]" : index % 3 === 1 ? "aspect-square" : "aspect-[4/3]"}`}><Image src={post.cover_url} alt="" fill sizes="(max-width: 639px) 100vw, (max-width: 1023px) 50vw, (max-width: 1279px) 33vw, 25vw" className="object-cover transition-transform duration-700 group-hover:scale-105" /></div> : <div className={`flex ${index % 2 ? "min-h-72" : "min-h-52"} items-center bg-gradient-to-br from-accent/25 via-[#45BFEF]/10 to-[#111538] p-7`}><p className="font-display text-2xl font-semibold leading-relaxed text-white/90">{post.title}</p></div>}
              </Link>
              <div className="p-4">
                <span className="rounded-full bg-accent/15 px-2.5 py-1 text-[11px] font-semibold text-accent-lighter">{labels[post.category] || post.category}</span>
                <Link href={`/community/posts/${post.id}`}><h2 className="mt-3 font-display text-base font-semibold leading-6 transition-colors hover:text-accent-light">{post.title}</h2></Link>
                <p className="mt-2 line-clamp-2 text-xs leading-5 text-white/45">{post.body_preview}</p>
                <div className="mt-4 flex items-center gap-2"><UserAvatar avatarUrl={post.author.avatar_url} seed={post.author.id} displayName={post.author.display_name} className="h-7 w-7 rounded-full" /><span className="min-w-0 flex-1 truncate text-xs text-white/55">{post.author.display_name}</span></div>
                <div className="mt-4 flex items-center gap-1 border-t border-white/5 pt-3">
                  <button onClick={() => void toggle(post, "like")} disabled={busy === `like:${post.id}`} aria-label="点赞创作" className={`creation-action ${post.liked ? "is-active" : ""}`}><span>{post.liked ? "♥" : "♡"}</span>{post.like_count}</button>
                  <Link href={`/community/posts/${post.id}#comments`} className="creation-action"><span>◯</span>{post.reply_count}</Link>
                  <button onClick={() => void toggle(post, "bookmark")} disabled={busy === `bookmark:${post.id}`} aria-label="收藏创作" className={`creation-action ml-auto ${post.bookmarked ? "is-active" : ""}`}><span>{post.bookmarked ? "★" : "☆"}</span>{post.bookmark_count}</button>
                </div>
              </div>
            </article>
          ))}</div>)}
        </section>
      </div>
    </main>
  );
}
