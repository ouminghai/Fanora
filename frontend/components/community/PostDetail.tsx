"use client";

import NiceModal from "@ebay/nice-modal-react";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import CommentPhotoGallery from "@/components/community/CommentPhotoGallery";
import ImageGallery from "@/components/community/ImageGallery";
import MarkdownContent from "@/components/community/MarkdownContent";
import MarkdownEditor from "@/components/community/MarkdownEditor";
import GlobalInfoModal from "@/components/modals/GlobalInfoModal";
import GlobalProcessModal, { hideGlobalProcessModal } from "@/components/modals/GlobalProcessModal";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import FanNftMarket from "@/components/nft/FanNftMarket";
import UserIdentityLink from "@/components/profile/UserIdentityLink";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import { apiErrorMessage } from "@/lib/api/errors";
import type { CommunityPostDetail, CommunityReply, FanNftListing, FanTask, PostEngagement, ReplyEngagement } from "@/lib/api/types";

const categoryLabels: Record<string, string> = { creation: "社区共创", story: "粉丝故事", music: "音乐分享", discussion: "社区讨论" };
const YOUTUBE_URL_PATTERN = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?[^ \n)]*v=|shorts\/|embed\/)|youtu\.be\/)[A-Za-z0-9_-]{6,}[^ \n)]*/i;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function youtubeEmbedUrl(value: string): string | null {
  const match = value.match(YOUTUBE_URL_PATTERN);
  if (!match) return null;
  const rawUrl = match[0].startsWith("http") ? match[0] : `https://${match[0]}`;
  try {
    const url = new URL(rawUrl);
    const host = url.hostname.replace(/^www\./, "");
    const id = host === "youtu.be"
      ? url.pathname.split("/").filter(Boolean)[0]
      : url.pathname.startsWith("/shorts/")
        ? url.pathname.split("/").filter(Boolean)[1]
        : url.pathname.startsWith("/embed/")
          ? url.pathname.split("/").filter(Boolean)[1]
          : url.searchParams.get("v");
    return id ? `https://www.youtube.com/embed/${encodeURIComponent(id)}` : null;
  } catch {
    return null;
  }
}

function YoutubePlayer({ url, title }: { url: string; title: string }) {
  return (
    <div className="community-reveal mx-auto mb-7 max-w-4xl overflow-hidden rounded-2xl border border-white/10 bg-[#090c24] shadow-[0_25px_80px_rgba(5,6,25,.35)]">
      <iframe
        src={url}
        title={title}
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowFullScreen
        className="aspect-video w-full"
      />
    </div>
  );
}

function updateReplyTree(replies: CommunityReply[], engagement: ReplyEngagement): CommunityReply[] {
  return replies.map((reply) => ({ ...reply, ...(reply.id === engagement.reply_id ? engagement : {}), children: updateReplyTree(reply.children, engagement) }));
}

type ReplyDraft = { body: string; image_urls: string[] };

function CommentComposer({ targetName, onCancel, onSubmit, busy, actionLabel }: { targetName?: string; onCancel?: () => void; onSubmit: (draft: ReplyDraft) => Promise<void>; busy: boolean; actionLabel: string }) {
  const [body, setBody] = useState("");
  const [imageUrls, setImageUrls] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (body.trim().length < 2) return;
    await onSubmit({ body: body.trim(), image_urls: imageUrls });
    setBody("");
    setImageUrls([]);
  };
  return <form onSubmit={submit} className="mt-5 rounded-2xl border border-white/10 bg-white/[.025] p-4">
    {targetName && <div className="mb-3 flex items-center justify-between text-xs text-accent-lighter"><span>回复 {targetName}</span><button type="button" onClick={onCancel} className="text-white/45 hover:text-white">取消</button></div>}
    {error && <p className="mb-3 text-xs text-red">{error}</p>}
    <MarkdownEditor value={body} onChange={setBody} maxLength={2000} imageUrls={imageUrls} onImageUrlsChange={setImageUrls} onImageError={setError} />
    <div className="mt-3 flex justify-end"><button disabled={busy || body.trim().length < 2} className="web3-action-button rounded-full px-5 py-2.5 text-sm font-semibold disabled:opacity-40">{busy ? "审核中…" : actionLabel}</button></div>
  </form>;
}

function CommentImageAttachments({ images, authorName }: { images: string[]; authorName: string }) {
  return <CommentPhotoGallery images={images} authorName={authorName} />;
}

function LinkedNftCard({ item, onOpen }: { item: FanNftListing; onOpen: () => void }) {
  return (
    <button type="button" onClick={onOpen} className="community-reveal mx-auto mb-7 flex w-full max-w-4xl flex-wrap gap-5 rounded-lg bg-white p-5 text-left shadow-sm transition-transform hover:-translate-y-0.5 dark:bg-jacarta-700 lg:flex-nowrap">
      <span className="relative block h-28 w-28 shrink-0 overflow-hidden rounded-lg bg-jacarta-100 dark:bg-white/5">
        {item.image_url ? <Image src={item.image_url} alt="" fill sizes="112px" className="object-cover" /> : null}
      </span>
      <span className="min-w-0 flex-1">
        <span className="mb-2 flex text-orange" aria-hidden="true">★★★★★</span>
        <span className="block text-xs font-bold uppercase text-accent">关联 NFT 产品</span>
        <span className="mt-2 block font-display text-lg font-semibold text-jacarta-700 dark:text-white">{item.name}</span>
        <span className="mt-2 line-clamp-2 block text-sm leading-6 text-jacarta-500 dark:text-jacarta-300">{item.description}</span>
      </span>
      <span className="flex shrink-0 flex-col justify-center">
        <FanTokenAmount amount={item.price_fan_tokens} showSymbol className="font-display text-xl font-semibold text-green" />
        <span className="mt-2 rounded-full bg-accent px-5 py-2 text-center text-sm font-semibold text-white">购买作品</span>
      </span>
    </button>
  );
}

function ReplyItem({ reply, onLike, onReply, busy }: { reply: CommunityReply; onLike: (id: string) => void; onReply: (draft: ReplyDraft, parentReplyId: string) => Promise<void>; busy: string | null }) {
  const [replying, setReplying] = useState(false);
  const submitChild = async (draft: ReplyDraft) => { await onReply(draft, reply.parent_reply_id || reply.id); setReplying(false); };
  return <div className="comment-thread">
    <div className="flex gap-3"><UserIdentityLink author={reply.author} avatarClassName="h-10 w-10 shrink-0 rounded-full" showName={false} compact /><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><UserIdentityLink author={reply.author} avatarClassName="hidden" nameClassName="text-sm font-semibold" /><span className="text-[11px] text-white/30">{reply.author.level}</span></div><MarkdownContent content={reply.body} className="!text-sm [&_p]:my-2 [&_p]:leading-7" /><CommentImageAttachments images={reply.image_urls} authorName={reply.author.display_name} /><div className="mt-3 flex items-center gap-4 text-xs"><span className="text-white/30">{formatDate(reply.created_at)}</span><button onClick={() => onLike(reply.id)} disabled={busy === `reply-like:${reply.id}`} className={`comment-action ${reply.liked ? "is-active" : ""}`}>{reply.liked ? "♥" : "♡"} {reply.like_count || "赞"}</button><button onClick={() => setReplying((value) => !value)} className="comment-action">◯ 回复</button></div>{replying && <CommentComposer targetName={reply.author.display_name} onCancel={() => setReplying(false)} busy={busy === `reply:${reply.id}`} actionLabel="发送回复" onSubmit={submitChild} />}</div></div>
    {reply.children.length > 0 && <div className="ml-7 mt-5 space-y-5 border-l border-white/10 pl-5 md:ml-12">{reply.children.map((child) => <ReplyItem key={child.id} reply={child} onLike={onLike} onReply={onReply} busy={busy} />)}</div>}
  </div>;
}

type PostDetailProps = {
  postId: string;
  variant?: "page" | "drawer";
  onClose?: () => void;
};

export default function PostDetail({ postId, variant = "page", onClose }: PostDetailProps) {
  const { user, refreshUser } = useAuth();
  const [post, setPost] = useState<CommunityPostDetail | null>(null);
  const [tasks, setTasks] = useState<FanTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [postResponse, taskResponse] = await Promise.all([api.get<CommunityPostDetail>(`/community/posts/${postId}?reply_limit=10&reply_offset=0`), api.get<FanTask[]>("/tasks")]);
    setPost(postResponse.data);
    setTasks(taskResponse.data.filter((task) => task.target_post_id === postId));
  }, [postId]);

  useEffect(() => { let cancelled = false; setLoading(true); load().catch((error) => !cancelled && setNotice({ kind: "error", text: apiErrorMessage(error) })).finally(() => !cancelled && setLoading(false)); return () => { cancelled = true; }; }, [load, user?.id]);
  useEffect(() => {
    if (variant !== "drawer" || loading || !post || window.location.hash !== "#comments") return;
    const frame = window.requestAnimationFrame(() => document.getElementById("comments")?.scrollIntoView({ block: "start" }));
    return () => window.cancelAnimationFrame(frame);
  }, [loading, post, variant]);

  const requireInteraction = () => {
    if (!user) { setNotice({ kind: "error", text: "请先登录后参与互动。" }); return false; }
    if (!user.is_official_member) { setNotice({ kind: "error", text: "正式入会后可以点赞、收藏和评论。" }); return false; }
    return true;
  };
  const togglePost = async (action: "like" | "bookmark") => { if (!post || !requireInteraction()) return; setBusy(action); try { const response = await api.post<PostEngagement>(`/community/posts/${post.id}/${action}`); setPost((current) => current ? { ...current, ...response.data } : current); if (action === "like") await refreshUser(); } catch (error) { setNotice({ kind: "error", text: apiErrorMessage(error) }); } finally { setBusy(null); } };
  const toggleReplyLike = async (replyId: string) => { if (!post || !requireInteraction()) return; setBusy(`reply-like:${replyId}`); try { const response = await api.post<ReplyEngagement>(`/community/replies/${replyId}/like`); setPost((current) => current ? { ...current, replies: updateReplyTree(current.replies, response.data) } : current); } catch (error) { setNotice({ kind: "error", text: apiErrorMessage(error) }); } finally { setBusy(null); } };
  const loadMoreReplies = async () => { if (!post?.has_more_replies || post.next_replies_offset === null) return; setBusy("load-more"); try { const response = await api.get<CommunityPostDetail>(`/community/posts/${postId}?reply_limit=10&reply_offset=${post.next_replies_offset}`); setPost((current) => current ? { ...response.data, replies: [...current.replies, ...response.data.replies] } : response.data); } catch (error) { setNotice({ kind: "error", text: apiErrorMessage(error) }); } finally { setBusy(null); } };
  const sendReply = async (draft: ReplyDraft, parentReplyId: string | null = null) => {
    if (!requireInteraction()) return;
    setBusy(`reply:${parentReplyId || "root"}`);
    setNotice(null);
    void NiceModal.show(GlobalProcessModal, {
      title: "AI 正在审核回复",
      message: "正在确认回复与当前讨论相关，并排除广告、垃圾信息和明显刷任务内容。普通、简短的真实表达会被保留。",
      eyebrow: "REPLY REVIEW",
      gifUrl: "/img/process/cyancat.gif",
    });
    try {
      await api.post<CommunityReply>(`/community/posts/${postId}/replies`, { ...draft, parent_reply_id: parentReplyId });
      await Promise.all([load(), refreshUser()]);
      await hideGlobalProcessModal();
      const completed = tasks.some((task) => task.participation_status === "claimed");
      setNotice({ kind: "success", text: completed ? "评论已发布，关联任务已自动验证并发放 FAN。" : "评论已发布。" });
    } catch (error) {
      await hideGlobalProcessModal();
      void NiceModal.show(GlobalInfoModal, {
        title: "这次回复没有发布",
        message: apiErrorMessage(error, "这次回复没有发布，请检查内容后重试。"),
        tone: "error",
        eyebrow: "REPLY ERROR",
        confirmLabel: "返回修改",
      });
    } finally {
      setBusy(null);
    }
  };

  if (loading) return variant === "drawer"
    ? <div className="flex min-h-[55vh] items-center justify-center"><span className="h-8 w-8 animate-spin rounded-full border-2 border-accent/20 border-t-accent" /></div>
    : <main className="web3-page-shell flex min-h-screen items-center justify-center"><span className="h-10 w-10 animate-spin rounded-full border-4 border-accent/20 border-t-accent" /></main>;
  if (!post) return variant === "drawer"
    ? <div className="flex min-h-[55vh] flex-col items-center justify-center px-6 text-center text-white"><h1 className="font-display text-2xl">帖子暂时无法打开</h1><button type="button" onClick={onClose} className="web3-action-button mt-6 rounded-full px-6 py-3">返回创作社区</button></div>
    : <main className="web3-page-shell min-h-screen pt-40 text-center text-white"><h1 className="font-display text-3xl">帖子暂时无法打开</h1><Link href="/community/creations" className="web3-action-button mt-8 inline-block rounded-full px-6 py-3">返回创作社区</Link></main>;
  const activeTask = tasks.find((task) => task.participation_status === "claimed");
  const postImages = post.image_urls.length ? post.image_urls : post.cover_url ? [post.cover_url] : [];
  const videoUrl = youtubeEmbedUrl(post.body);
  const content = <div className={variant === "drawer" ? "mx-auto w-full max-w-5xl px-5 pt-10 md:px-10 md:pt-12" : "container max-w-6xl"}>
    {variant === "page" ? <div className="community-reveal mb-6 flex items-center justify-between gap-4"><Link href="/community/creations" className="text-sm font-semibold text-white/50 hover:text-accent-light">← 返回创作社区</Link>{activeTask && <span className="rounded-full bg-orange/15 px-4 py-2 text-xs font-semibold text-orange">进行中的任务：{activeTask.title}</span>}</div> : activeTask ? <div className="community-reveal mb-4 flex justify-end pr-12"><span className="rounded-full bg-orange/15 px-4 py-2 text-xs font-semibold text-orange">进行中的任务：{activeTask.title}</span></div> : null}
    {notice && <div className={`community-reveal mb-6 rounded-2xl border px-5 py-4 text-sm font-semibold ${notice.kind === "success" ? "border-green/20 bg-green/10 text-green" : "border-red/20 bg-red/10 text-red"}`}>{notice.text}</div>}
    <header className={`community-reveal mx-auto max-w-4xl text-center text-white ${variant === "drawer" ? "py-5 md:py-7" : "py-10 md:py-16"}`}><span className={`inline-flex rounded-full border border-accent/25 bg-accent/10 font-bold uppercase tracking-[.2em] text-accent-lighter ${variant === "drawer" ? "px-3 py-1.5 text-[10px]" : "px-4 py-2 text-xs"}`}>{categoryLabels[post.category] || post.category}</span><h1 className={`font-display font-semibold leading-[1.12] ${variant === "drawer" ? "mt-5 text-2xl md:text-4xl" : "mt-7 text-4xl md:text-6xl"}`}>{post.title}</h1><div className={`${variant === "drawer" ? "mt-5" : "mt-7"} flex items-center justify-center gap-3`}><UserIdentityLink author={post.author} avatarClassName={`${variant === "drawer" ? "h-9 w-9" : "h-10 w-10"} rounded-full`} nameClassName={`${variant === "drawer" ? "text-xs" : "text-sm"} font-semibold`} /><span className="text-left text-[11px] text-white/35">{post.author.level} · {formatDate(post.created_at)}</span></div></header>
    <ImageGallery images={postImages} alt={post.title} mode="natural" className={`community-reveal bg-[#090c24] ${variant === "drawer" ? "mb-7 rounded-2xl" : "mb-10 rounded-[2rem] border border-white/10 shadow-[0_30px_100px_rgba(5,6,25,.5)]"}`} />
    {videoUrl ? <YoutubePlayer url={videoUrl} title={`${post.title} YouTube 视频`} /> : null}
    {post.linked_nft ? <LinkedNftCard item={post.linked_nft} onOpen={() => setSelectedItemId(post.linked_nft?.id || null)} /> : null}
    <article className={`community-reveal mx-auto max-w-4xl overflow-hidden text-white ${variant === "drawer" ? "rounded-2xl bg-white/[.025]" : "rounded-[2rem] border border-white/10 bg-[#111538] shadow-[0_25px_80px_rgba(5,6,25,.35)]"}`}><div className={variant === "drawer" ? "p-5 md:p-7" : "p-7 md:p-10"}><MarkdownContent content={post.body} className={variant === "drawer" ? "[&_h1]:text-2xl [&_h2]:text-xl [&_h3]:text-lg [&_li]:text-sm [&_p]:text-sm [&_p]:leading-7" : undefined} /><div className={`${variant === "drawer" ? "mt-6" : "mt-8"} flex flex-wrap items-center gap-3 border-t border-white/5 pt-5`}><button onClick={() => void togglePost("like")} disabled={busy === "like"} className={`post-action ${post.liked ? "is-active" : ""}`}>{post.liked ? "♥" : "♡"} {post.like_count} </button><a href="#comments" className="post-action">◯ {post.reply_count} </a><button onClick={() => void togglePost("bookmark")} disabled={busy === "bookmark"} className={`post-action ml-auto ${post.bookmarked ? "is-active" : ""}`}>{post.bookmarked ? "★" : "☆"} {post.bookmark_count} </button></div></div></article>
    <section id="comments" className={`community-reveal mx-auto mt-7 max-w-4xl scroll-mt-20 text-white ${variant === "drawer" ? "rounded-t-2xl bg-white/[.025] p-5 md:p-7" : "rounded-[2rem] border border-white/10 bg-[#111538] p-6 md:p-9"}`}><div className="flex items-center justify-between"><h2 className={`font-display font-semibold ${variant === "drawer" ? "text-xl" : "text-2xl"}`}>社区评论</h2><span className="rounded-full bg-white/5 px-3 py-1 text-xs text-white/45">{post.reply_count} 条</span></div>
      <div className="mt-8 space-y-7">{post.replies.length ? post.replies.map((reply) => <ReplyItem key={reply.id} reply={reply} onLike={(id) => void toggleReplyLike(id)} onReply={sendReply} busy={busy} />) : <p className="rounded-2xl bg-white/[.035] p-5 text-sm text-white/35">还没有评论，来留下第一条认真分享吧。</p>}</div>
      {post.has_more_replies && <button type="button" onClick={() => void loadMoreReplies()} disabled={busy === "load-more"} className="mt-7 w-full border-y border-white/10 py-3 text-sm font-semibold text-accent-lighter transition-colors hover:text-white disabled:opacity-50">{busy === "load-more" ? "加载中…" : "加载更多评论"}</button>}
      {!user ? <Link href="/login" className="web3-action-button mt-7 block rounded-full py-3 text-center font-semibold">登录后评论</Link> : !user.is_official_member ? <Link href="/membership/join" className="web3-action-button mt-7 block rounded-full py-3 text-center font-semibold">正式入会后评论</Link> : <CommentComposer busy={busy === "reply:root"} actionLabel={activeTask ? "发布并完成任务" : "发布评论"} onSubmit={(draft) => sendReply(draft)} />}
    </section>
  </div>;
  return variant === "drawer"
    ? <div className="community-letter-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain">{content}{selectedItemId ? <NftDrawer itemId={selectedItemId} onClose={() => setSelectedItemId(null)} /> : null}</div>
    : <main className="web3-page-shell min-h-screen pb-24 pt-28 md:pt-32">{content}{selectedItemId ? <NftDrawer itemId={selectedItemId} onClose={() => setSelectedItemId(null)} /> : null}</main>;
}

function NftDrawer({ itemId, onClose }: { itemId: string; onClose: () => void }) {
  return (
    <div role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }} className="community-drawer-backdrop fixed inset-0 z-[1100] flex items-end justify-center bg-[#050619]/75 px-0 pt-5 backdrop-blur-md md:px-8 md:pt-10">
      <section role="dialog" aria-modal="true" aria-label="NFT 详情" className="community-letter-drawer relative flex min-h-[95dvh] max-h-[calc(100dvh-1.25rem)] w-full max-w-7xl flex-col overflow-hidden rounded-t-lg bg-[#f7f7fb] shadow-[0_45px_140px_rgba(0,0,0,.72)] dark:bg-jacarta-900 md:max-h-[calc(100dvh-2.5rem)]" onMouseDown={(event) => event.stopPropagation()}>
        <button type="button" onClick={onClose} aria-label="关闭 NFT 详情" className="absolute right-4 top-4 z-20 flex h-10 w-10 items-center justify-center rounded-full border border-jacarta-100 bg-white/90 text-2xl leading-none text-jacarta-600 shadow-lg transition-colors hover:border-accent hover:text-accent dark:border-white/15 dark:bg-[#090b23]/85 dark:text-white/75">
          <span aria-hidden="true" className="-translate-y-px">×</span>
        </button>
        <FanNftMarket mode="item" itemId={itemId} variant="drawer" onClose={onClose} />
      </section>
    </div>
  );
}
