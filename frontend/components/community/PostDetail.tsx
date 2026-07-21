"use client";

import axios from "axios";
import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import CommentPhotoGallery from "@/components/community/CommentPhotoGallery";
import ImageGallery from "@/components/community/ImageGallery";
import MarkdownContent from "@/components/community/MarkdownContent";
import MarkdownEditor from "@/components/community/MarkdownEditor";
import UserAvatar from "@/components/profile/UserAvatar";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import type { CommunityPostDetail, CommunityReply, FanTask, PostEngagement, ReplyEngagement } from "@/lib/api/types";

const categoryLabels: Record<string, string> = { creation: "社区共创", story: "粉丝故事", music: "音乐分享", discussion: "社区讨论" };

function errorMessage(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail || "操作没有完成。";
  return error instanceof Error ? error.message : "操作没有完成。";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
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
    if (body.trim().length < 10) return;
    await onSubmit({ body: body.trim(), image_urls: imageUrls });
    setBody("");
    setImageUrls([]);
  };
  return <form onSubmit={submit} className="mt-5 rounded-2xl border border-white/10 bg-white/[.025] p-4">
    {targetName && <div className="mb-3 flex items-center justify-between text-xs text-accent-lighter"><span>回复 {targetName}</span><button type="button" onClick={onCancel} className="text-white/45 hover:text-white">取消</button></div>}
    {error && <p className="mb-3 text-xs text-red">{error}</p>}
    <MarkdownEditor value={body} onChange={setBody} maxLength={2000} imageUrls={imageUrls} onImageUrlsChange={setImageUrls} onImageError={setError} />
    <div className="mt-3 flex justify-end"><button disabled={busy || body.trim().length < 10} className="web3-action-button rounded-full px-5 py-2.5 text-sm font-semibold disabled:opacity-40">{busy ? "发布中…" : actionLabel}</button></div>
  </form>;
}

function CommentImageAttachments({ images, authorName }: { images: string[]; authorName: string }) {
  return <CommentPhotoGallery images={images} authorName={authorName} />;
}

function ReplyItem({ reply, onLike, onReply, busy }: { reply: CommunityReply; onLike: (id: string) => void; onReply: (draft: ReplyDraft, parentReplyId: string) => Promise<void>; busy: string | null }) {
  const [replying, setReplying] = useState(false);
  const submitChild = async (draft: ReplyDraft) => { await onReply(draft, reply.parent_reply_id || reply.id); setReplying(false); };
  return <div className="comment-thread">
    <div className="flex gap-3"><UserAvatar avatarUrl={reply.author.avatar_url} seed={reply.author.id} displayName={reply.author.display_name} className="h-10 w-10 shrink-0 rounded-full" /><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><p className="text-sm font-semibold">{reply.author.display_name}</p><span className="text-[11px] text-white/30">{reply.author.level}</span></div><MarkdownContent content={reply.body} className="!text-sm [&_p]:my-2 [&_p]:leading-7" /><CommentImageAttachments images={reply.image_urls} authorName={reply.author.display_name} /><div className="mt-3 flex items-center gap-4 text-xs"><span className="text-white/30">{formatDate(reply.created_at)}</span><button onClick={() => onLike(reply.id)} disabled={busy === `reply-like:${reply.id}`} className={`comment-action ${reply.liked ? "is-active" : ""}`}>{reply.liked ? "♥" : "♡"} {reply.like_count || "赞"}</button><button onClick={() => setReplying((value) => !value)} className="comment-action">◯ 回复</button></div>{replying && <CommentComposer targetName={reply.author.display_name} onCancel={() => setReplying(false)} busy={busy === `reply:${reply.id}`} actionLabel="发送回复" onSubmit={submitChild} />}</div></div>
    {reply.children.length > 0 && <div className="ml-7 mt-5 space-y-5 border-l border-white/10 pl-5 md:ml-12">{reply.children.map((child) => <ReplyItem key={child.id} reply={child} onLike={onLike} onReply={onReply} busy={busy} />)}</div>}
  </div>;
}

export default function PostDetail({ postId }: { postId: string }) {
  const { user, refreshUser } = useAuth();
  const [post, setPost] = useState<CommunityPostDetail | null>(null);
  const [tasks, setTasks] = useState<FanTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    const [postResponse, taskResponse] = await Promise.all([api.get<CommunityPostDetail>(`/community/posts/${postId}?reply_limit=10&reply_offset=0`), api.get<FanTask[]>("/tasks")]);
    setPost(postResponse.data);
    setTasks(taskResponse.data.filter((task) => task.target_post_id === postId));
  }, [postId]);

  useEffect(() => { let cancelled = false; setLoading(true); load().catch((error) => !cancelled && setNotice({ kind: "error", text: errorMessage(error) })).finally(() => !cancelled && setLoading(false)); return () => { cancelled = true; }; }, [load, user]);

  const requireInteraction = () => {
    if (!user) { setNotice({ kind: "error", text: "请先登录后参与互动。" }); return false; }
    if (!user.is_official_member) { setNotice({ kind: "error", text: "正式入会后可以点赞、收藏和评论。" }); return false; }
    return true;
  };
  const togglePost = async (action: "like" | "bookmark") => { if (!post || !requireInteraction()) return; setBusy(action); try { const response = await api.post<PostEngagement>(`/community/posts/${post.id}/${action}`); setPost((current) => current ? { ...current, ...response.data } : current); if (action === "like") await refreshUser(); } catch (error) { setNotice({ kind: "error", text: errorMessage(error) }); } finally { setBusy(null); } };
  const toggleReplyLike = async (replyId: string) => { if (!post || !requireInteraction()) return; setBusy(`reply-like:${replyId}`); try { const response = await api.post<ReplyEngagement>(`/community/replies/${replyId}/like`); setPost((current) => current ? { ...current, replies: updateReplyTree(current.replies, response.data) } : current); } catch (error) { setNotice({ kind: "error", text: errorMessage(error) }); } finally { setBusy(null); } };
  const loadMoreReplies = async () => { if (!post?.has_more_replies || post.next_replies_offset === null) return; setBusy("load-more"); try { const response = await api.get<CommunityPostDetail>(`/community/posts/${postId}?reply_limit=10&reply_offset=${post.next_replies_offset}`); setPost((current) => current ? { ...response.data, replies: [...current.replies, ...response.data.replies] } : response.data); } catch (error) { setNotice({ kind: "error", text: errorMessage(error) }); } finally { setBusy(null); } };
  const sendReply = async (draft: ReplyDraft, parentReplyId: string | null = null) => { if (!requireInteraction()) return; setBusy(`reply:${parentReplyId || "root"}`); setNotice(null); try { await api.post<CommunityReply>(`/community/posts/${postId}/replies`, { ...draft, parent_reply_id: parentReplyId }); await Promise.all([load(), refreshUser()]); const completed = tasks.some((task) => task.participation_status === "claimed"); setNotice({ kind: "success", text: completed ? "评论已发布，关联任务已自动验证并发放 FAN。" : "评论已发布。" }); } catch (error) { setNotice({ kind: "error", text: errorMessage(error) }); } finally { setBusy(null); } };

  if (loading) return <main className="web3-page-shell flex min-h-screen items-center justify-center"><span className="h-10 w-10 animate-spin rounded-full border-4 border-accent/20 border-t-accent" /></main>;
  if (!post) return <main className="web3-page-shell min-h-screen pt-40 text-center text-white"><h1 className="font-display text-3xl">帖子暂时无法打开</h1><Link href="/community/creations" className="web3-action-button mt-8 inline-block rounded-full px-6 py-3">返回创作社区</Link></main>;
  const activeTask = tasks.find((task) => task.participation_status === "claimed");
  const postImages = post.image_urls.length ? post.image_urls : post.cover_url ? [post.cover_url] : [];
  return <main className="web3-page-shell min-h-screen pb-24 pt-28 md:pt-32"><div className="container max-w-6xl">
    <div className="community-reveal mb-6 flex items-center justify-between gap-4"><Link href="/community/creations" className="text-sm font-semibold text-white/50 hover:text-accent-light">← 返回创作社区</Link>{activeTask && <span className="rounded-full bg-orange/15 px-4 py-2 text-xs font-semibold text-orange">进行中的任务：{activeTask.title}</span>}</div>
    {notice && <div className={`community-reveal mb-6 rounded-2xl border px-5 py-4 text-sm font-semibold ${notice.kind === "success" ? "border-green/20 bg-green/10 text-green" : "border-red/20 bg-red/10 text-red"}`}>{notice.text}</div>}
    <header className="community-reveal mx-auto max-w-4xl py-10 text-center text-white md:py-16"><span className="inline-flex rounded-full border border-accent/25 bg-accent/10 px-4 py-2 text-xs font-bold uppercase tracking-[.2em] text-accent-lighter">{categoryLabels[post.category] || post.category}</span><h1 className="mt-7 font-display text-4xl font-semibold leading-[1.08] md:text-6xl">{post.title}</h1><div className="mt-7 flex items-center justify-center gap-3"><UserAvatar avatarUrl={post.author.avatar_url} seed={post.author.id} displayName={post.author.display_name} className="h-10 w-10 rounded-full" /><div className="text-left"><p className="text-sm font-semibold">{post.author.display_name}</p><p className="mt-1 text-xs text-white/35">{post.author.level} · {formatDate(post.created_at)}</p></div></div></header>
    <ImageGallery images={postImages} alt={post.title} className="community-reveal mb-10 aspect-[16/9] rounded-[2rem] border border-white/10 bg-[#111538] shadow-[0_30px_100px_rgba(5,6,25,.5)]" />
    <article className="community-reveal mx-auto max-w-4xl overflow-hidden rounded-[2rem] border border-white/10 bg-[#111538] text-white shadow-[0_25px_80px_rgba(5,6,25,.35)]"><div className="p-7 md:p-10"><MarkdownContent content={post.body} /><div className="mt-8 flex flex-wrap items-center gap-3 border-t border-white/5 pt-5"><button onClick={() => void togglePost("like")} disabled={busy === "like"} className={`post-action ${post.liked ? "is-active" : ""}`}>{post.liked ? "♥" : "♡"} {post.like_count} </button><a href="#comments" className="post-action">◯ {post.reply_count} </a><button onClick={() => void togglePost("bookmark")} disabled={busy === "bookmark"} className={`post-action ml-auto ${post.bookmarked ? "is-active" : ""}`}>{post.bookmarked ? "★" : "☆"} {post.bookmark_count} </button></div></div></article>
    <section id="comments" className="community-reveal mx-auto mt-8 max-w-4xl scroll-mt-28 rounded-[2rem] border border-white/10 bg-[#111538] p-6 text-white md:p-9"><div className="flex items-center justify-between"><h2 className="font-display text-2xl font-semibold">社区评论</h2><span className="rounded-full bg-white/5 px-3 py-1 text-xs text-white/45">{post.reply_count} 条</span></div>
      <div className="mt-8 space-y-7">{post.replies.length ? post.replies.map((reply) => <ReplyItem key={reply.id} reply={reply} onLike={(id) => void toggleReplyLike(id)} onReply={sendReply} busy={busy} />) : <p className="rounded-2xl bg-white/[.035] p-5 text-sm text-white/35">还没有评论，来留下第一条认真分享吧。</p>}</div>
      {post.has_more_replies && <button type="button" onClick={() => void loadMoreReplies()} disabled={busy === "load-more"} className="mt-7 w-full border-y border-white/10 py-3 text-sm font-semibold text-accent-lighter transition-colors hover:text-white disabled:opacity-50">{busy === "load-more" ? "加载中…" : "加载更多评论"}</button>}
      {!user ? <Link href="/login" className="web3-action-button mt-7 block rounded-full py-3 text-center font-semibold">登录后评论</Link> : !user.is_official_member ? <Link href="/membership/join" className="web3-action-button mt-7 block rounded-full py-3 text-center font-semibold">正式入会后评论</Link> : <CommentComposer busy={busy === "reply:root"} actionLabel={activeTask ? "发布并完成任务" : "发布评论"} onSubmit={(draft) => sendReply(draft)} />}
    </section>
  </div></main>;
}
