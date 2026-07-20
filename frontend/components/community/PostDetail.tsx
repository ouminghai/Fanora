"use client";

import axios from "axios";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import MarkdownContent from "@/components/community/MarkdownContent";
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
  return replies.map((reply) => ({
    ...reply,
    ...(reply.id === engagement.reply_id ? engagement : {}),
    children: updateReplyTree(reply.children, engagement),
  }));
}

export default function PostDetail({ postId }: { postId: string }) {
  const { user, refreshUser } = useAuth();
  const [post, setPost] = useState<CommunityPostDetail | null>(null);
  const [tasks, setTasks] = useState<FanTask[]>([]);
  const [body, setBody] = useState("");
  const [replyTarget, setReplyTarget] = useState<{ rootId: string; name: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    const [postResponse, taskResponse] = await Promise.all([
      api.get<CommunityPostDetail>(`/community/posts/${postId}`),
      api.get<FanTask[]>("/tasks"),
    ]);
    setPost(postResponse.data);
    setTasks(taskResponse.data.filter((task) => task.target_post_id === postId));
  }, [postId]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    load().catch((error) => !cancelled && setNotice({ kind: "error", text: errorMessage(error) })).finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [load, user]);

  const requireInteraction = () => {
    if (!user) { setNotice({ kind: "error", text: "请先登录后参与互动。" }); return false; }
    if (!user.is_official_member) { setNotice({ kind: "error", text: "正式入会后可以点赞、收藏和评论。" }); return false; }
    return true;
  };

  const togglePost = async (action: "like" | "bookmark") => {
    if (!post || !requireInteraction()) return;
    setBusy(action);
    try {
      const response = await api.post<PostEngagement>(`/community/posts/${post.id}/${action}`);
      setPost((current) => current ? { ...current, ...response.data } : current);
    } catch (error) { setNotice({ kind: "error", text: errorMessage(error) }); } finally { setBusy(null); }
  };

  const toggleReplyLike = async (replyId: string) => {
    if (!post || !requireInteraction()) return;
    setBusy(`reply-like:${replyId}`);
    try {
      const response = await api.post<ReplyEngagement>(`/community/replies/${replyId}/like`);
      setPost((current) => current ? { ...current, replies: updateReplyTree(current.replies, response.data) } : current);
    } catch (error) { setNotice({ kind: "error", text: errorMessage(error) }); } finally { setBusy(null); }
  };

  const startReply = (rootId: string, name: string) => {
    if (!requireInteraction()) return;
    setReplyTarget({ rootId, name });
    document.getElementById("reply-composer")?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const submitReply = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("reply");
    setNotice(null);
    try {
      await api.post<CommunityReply>(`/community/posts/${postId}/replies`, {
        body: replyTarget ? `回复 ${replyTarget.name}：${body}` : body,
        parent_reply_id: replyTarget?.rootId || null,
      });
      await Promise.all([load(), refreshUser()]);
      setBody("");
      setReplyTarget(null);
      const completed = tasks.some((task) => task.participation_status === "claimed");
      setNotice({ kind: "success", text: completed ? "评论已发布，关联任务已自动验证并发放 FAN。" : "评论已发布。" });
    } catch (error) { setNotice({ kind: "error", text: errorMessage(error) }); } finally { setBusy(null); }
  };

  if (loading) return <main className="web3-page-shell flex min-h-screen items-center justify-center"><span className="h-10 w-10 animate-spin rounded-full border-4 border-accent/20 border-t-accent" /></main>;
  if (!post) return <main className="web3-page-shell min-h-screen pt-40 text-center text-white"><h1 className="font-display text-3xl">帖子暂时无法打开</h1><Link href="/community/creations" className="web3-action-button mt-8 inline-block rounded-full px-6 py-3">返回创作社区</Link></main>;

  const activeTask = tasks.find((task) => task.participation_status === "claimed");
  return (
    <main className="web3-page-shell min-h-screen pb-24 pt-28 md:pt-32">
      <div className="container max-w-6xl">
        <div className="community-reveal mb-6 flex items-center justify-between gap-4"><Link href="/community/creations" className="text-sm font-semibold text-white/50 hover:text-accent-light">← 返回创作社区</Link>{activeTask && <span className="rounded-full bg-orange/15 px-4 py-2 text-xs font-semibold text-orange">进行中的任务：{activeTask.title}</span>}</div>
        {notice && <div className={`community-reveal mb-6 rounded-2xl border px-5 py-4 text-sm font-semibold ${notice.kind === "success" ? "border-green/20 bg-green/10 text-green" : "border-red/20 bg-red/10 text-red"}`}>{notice.text}</div>}

        <header className="community-reveal mx-auto max-w-4xl py-10 text-center text-white md:py-16">
          <span className="inline-flex rounded-full border border-accent/25 bg-accent/10 px-4 py-2 text-xs font-bold uppercase tracking-[.2em] text-accent-lighter">{categoryLabels[post.category] || post.category}</span>
          <h1 className="mt-7 font-display text-4xl font-semibold leading-[1.08] md:text-6xl">{post.title}</h1>
          <div className="mt-7 flex items-center justify-center gap-3"><UserAvatar avatarUrl={post.author.avatar_url} seed={post.author.id} displayName={post.author.display_name} className="h-10 w-10 rounded-full" /><div className="text-left"><p className="text-sm font-semibold">{post.author.display_name}</p><p className="mt-1 text-xs text-white/35">{post.author.level} · {formatDate(post.created_at)}</p></div></div>
        </header>

        {post.cover_url && <figure className="community-reveal relative mb-10 h-80 overflow-hidden rounded-[2rem] border border-white/10 bg-[#111538] shadow-[0_30px_100px_rgba(5,6,25,.5)] [animation-delay:80ms] md:h-[36rem]"><Image src={post.cover_url} alt={`${post.title}首图`} fill priority sizes="(max-width: 1200px) 100vw, 1152px" className="object-cover transition-transform duration-1000 hover:scale-[1.015]" /></figure>}

        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-8">
            <article className="community-reveal overflow-hidden rounded-[2rem] border border-white/10 bg-[#111538] text-white shadow-[0_25px_80px_rgba(5,6,25,.35)] [animation-delay:120ms]">
              <div className="p-7 md:p-10">
                <MarkdownContent content={post.body} />
                <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-white/5 pt-5">
                  <button onClick={() => void togglePost("like")} disabled={busy === "like"} className={`post-action ${post.liked ? "is-active" : ""}`}><span>{post.liked ? "♥" : "♡"}</span> {post.like_count} 点赞</button>
                  <a href="#comments" className="post-action"><span>◯</span> {post.reply_count} 评论</a>
                  <button onClick={() => void togglePost("bookmark")} disabled={busy === "bookmark"} className={`post-action ml-auto ${post.bookmarked ? "is-active" : ""}`}><span>{post.bookmarked ? "★" : "☆"}</span> {post.bookmark_count} 收藏</button>
                </div>
              </div>
            </article>

            <section id="comments" className="community-reveal scroll-mt-28 rounded-[2rem] border border-white/10 bg-[#111538] p-6 text-white [animation-delay:100ms] md:p-9">
              <div className="flex items-center justify-between"><h2 className="font-display text-2xl font-semibold">社区评论</h2><span className="rounded-full bg-white/5 px-3 py-1 text-xs text-white/45">{post.reply_count} 条</span></div>
              <div className="mt-7 space-y-7">
                {post.replies.length ? post.replies.map((reply, index) => (
                  <div key={reply.id} className="comment-thread community-reveal" style={{ animationDelay: `${index * 55}ms` }}>
                    <div className="flex gap-3"><UserAvatar avatarUrl={reply.author.avatar_url} seed={reply.author.id} displayName={reply.author.display_name} className="h-10 w-10 shrink-0 rounded-full" /><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><p className="text-sm font-semibold">{reply.author.display_name}</p><span className="text-[11px] text-white/30">{reply.author.level}</span></div><p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-white/70">{reply.body}</p><div className="mt-3 flex items-center gap-4 text-xs"><span className="text-white/30">{formatDate(reply.created_at)}</span><button onClick={() => void toggleReplyLike(reply.id)} className={`comment-action ${reply.liked ? "is-active" : ""}`}>{reply.liked ? "♥" : "♡"} {reply.like_count || "赞"}</button><button onClick={() => startReply(reply.id, reply.author.display_name)} className="comment-action">◯ 回复</button></div></div></div>
                    {reply.children.length > 0 && <div className="ml-7 mt-5 space-y-5 border-l border-white/10 pl-5 md:ml-12">{reply.children.map((child) => <div key={child.id} className="flex gap-3"><UserAvatar avatarUrl={child.author.avatar_url} seed={child.author.id} displayName={child.author.display_name} className="h-8 w-8 shrink-0 rounded-full" /><div className="min-w-0 flex-1"><p className="text-sm font-semibold">{child.author.display_name}</p><p className="mt-2 text-sm leading-7 text-white/65">{child.body}</p><div className="mt-2 flex gap-4 text-xs"><span className="text-white/30">{formatDate(child.created_at)}</span><button onClick={() => void toggleReplyLike(child.id)} className={`comment-action ${child.liked ? "is-active" : ""}`}>{child.liked ? "♥" : "♡"} {child.like_count || "赞"}</button><button onClick={() => startReply(reply.id, child.author.display_name)} className="comment-action">◯ 回复</button></div></div></div>)}</div>}
                  </div>
                )) : <p className="rounded-2xl bg-white/[.035] p-5 text-sm text-white/35">还没有评论，来留下第一条认真分享吧。</p>}
              </div>
            </section>
          </div>

          <aside><section id="reply-composer" className="community-reveal sticky top-28 rounded-[2rem] border border-white/10 bg-[#111538] p-6 text-white [animation-delay:160ms]"><p className="text-xs font-bold uppercase tracking-[.18em] text-accent-light">Join the conversation</p><h2 className="mt-2 font-display text-xl font-semibold">参与讨论</h2>{activeTask && <div className="mt-4 rounded-2xl border border-orange/20 bg-orange/10 p-4 text-xs leading-5 text-orange">回复后自动完成任务：{activeTask.title}</div>}
            {!user ? <Link href="/login" className="web3-action-button mt-5 block rounded-full py-3.5 text-center font-semibold">登录后评论</Link> : !user.is_official_member ? <Link href="/membership/join" className="web3-action-button mt-5 block rounded-full py-3.5 text-center font-semibold">正式入会后评论</Link> : <form onSubmit={submitReply} className="mt-5">{replyTarget && <div className="mb-3 flex items-center justify-between rounded-xl bg-accent/10 px-3 py-2 text-xs text-accent-lighter"><span>回复 {replyTarget.name}</span><button type="button" onClick={() => setReplyTarget(null)}>取消</button></div>}<textarea required minLength={10} maxLength={2000} rows={7} value={body} onChange={(event) => setBody(event.target.value)} placeholder={replyTarget ? `回复 ${replyTarget.name}…` : "至少 10 个字，认真说说你的想法…"} className="w-full resize-none rounded-2xl border-white/10 bg-white/[.05] text-sm leading-6 text-white placeholder:text-white/25" /><div className="mt-2 text-right text-xs text-white/25">{body.length}/2000</div><button disabled={busy === "reply" || body.trim().length < 10} className="web3-action-button mt-3 w-full rounded-full py-3.5 font-semibold disabled:opacity-40">{busy === "reply" ? "发布中…" : replyTarget ? "发布子评论" : activeTask ? "发布并完成任务" : "发布评论"}</button></form>}
          </section></aside>
        </div>
      </div>
    </main>
  );
}
