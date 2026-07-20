"use client";

import axios from "axios";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import UserAvatar from "@/components/profile/UserAvatar";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import type {
  CommunityPostDetail,
  CommunityPostSummary,
  DailyCheckInStatus,
  FanTask,
  FanTokenLedgerEntry,
  OfficialCommunity,
} from "@/lib/api/types";

const categoryLabels: Record<string, string> = {
  discussion: "讨论",
  music: "音乐",
  story: "故事",
  creation: "共创",
};

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || "请求没有完成，请稍后再试。";
  }
  return error instanceof Error ? error.message : "请求没有完成，请稍后再试。";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric" }).format(
    new Date(value),
  );
}

export default function CommunityHub() {
  const { user, status, refreshUser } = useAuth();
  const [community, setCommunity] = useState<OfficialCommunity | null>(null);
  const [posts, setPosts] = useState<CommunityPostSummary[]>([]);
  const [tasks, setTasks] = useState<FanTask[]>([]);
  const [checkIn, setCheckIn] = useState<DailyCheckInStatus | null>(null);
  const [ledger, setLedger] = useState<FanTokenLedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [showComposer, setShowComposer] = useState(false);
  const [draft, setDraft] = useState({ title: "", body: "", category: "creation" });

  const loadPublic = useCallback(async () => {
    const [communityResponse, postsResponse, tasksResponse] = await Promise.all([
      api.get<OfficialCommunity>("/community"),
      api.get<CommunityPostSummary[]>("/community/posts"),
      api.get<FanTask[]>("/tasks"),
    ]);
    setCommunity(communityResponse.data);
    setPosts(postsResponse.data);
    setTasks(tasksResponse.data);
  }, []);

  const loadPrivate = useCallback(async () => {
    if (!user) {
      setCheckIn(null);
      setLedger([]);
      return;
    }
    const requests: Promise<unknown>[] = [
      api.get<FanTask[]>("/tasks").then((response) => setTasks(response.data)),
      api
        .get<FanTokenLedgerEntry[]>("/fan-tokens/me/ledger?limit=6")
        .then((response) => setLedger(response.data)),
    ];
    if (user.is_official_member) {
      requests.push(
        api
          .get<DailyCheckInStatus>("/check-ins/me")
          .then((response) => setCheckIn(response.data)),
      );
    }
    await Promise.all(requests);
  }, [user]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        await loadPublic();
        if (!cancelled) setLoading(false);
      } catch (error) {
        if (!cancelled) {
          setNotice({ kind: "error", text: getErrorMessage(error) });
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [loadPublic]);

  useEffect(() => {
    if (status === "authenticated") void loadPrivate();
  }, [loadPrivate, status]);

  const joined = community?.joined || Boolean(user?.communities.some((item) => item.slug === "fanora-official"));
  const completedCount = useMemo(
    () => tasks.filter((task) => task.participation_status === "rewarded").length,
    [tasks],
  );

  const join = async () => {
    if (!user) return;
    setAction("join");
    setNotice(null);
    try {
      const response = await api.post<OfficialCommunity>("/community/join");
      setCommunity(response.data);
      await refreshUser();
      await loadPrivate();
      setNotice({ kind: "success", text: "已加入 Fanora 官方社区，并记录到你的粉丝身份。" });
    } catch (error) {
      setNotice({ kind: "error", text: getErrorMessage(error) });
    } finally {
      setAction(null);
    }
  };

  const performCheckIn = async () => {
    setAction("check-in");
    setNotice(null);
    try {
      const response = await api.post<DailyCheckInStatus>("/check-ins");
      setCheckIn(response.data);
      await Promise.all([refreshUser(), loadPrivate()]);
      setNotice({
        kind: "success",
        text: response.data.already_checked_in
          ? "今天已经签到，明天再来延续记录。"
          : `签到成功，获得 ${response.data.reward_fan_tokens} FAN。`,
      });
    } catch (error) {
      setNotice({ kind: "error", text: getErrorMessage(error) });
    } finally {
      setAction(null);
    }
  };

  const claimTask = async (task: FanTask) => {
    setAction(`task:${task.id}`);
    setNotice(null);
    try {
      const response = await api.post<FanTask>(`/tasks/${task.id}/claim`);
      setTasks((current) => current.map((item) => (item.id === task.id ? response.data : item)));
      setNotice({ kind: "success", text: "任务已领取。进入指定帖子回复，发布后会立即完成。" });
    } catch (error) {
      setNotice({ kind: "error", text: getErrorMessage(error) });
    } finally {
      setAction(null);
    }
  };

  const createPost = async (event: FormEvent) => {
    event.preventDefault();
    setAction("create-post");
    setNotice(null);
    try {
      const response = await api.post<CommunityPostDetail>("/community/posts", draft);
      setDraft({ title: "", body: "", category: "creation" });
      setShowComposer(false);
      await loadPublic();
      setNotice({ kind: "success", text: `《${response.data.title}》已发布到创作社区。` });
    } catch (error) {
      setNotice({ kind: "error", text: getErrorMessage(error) });
    } finally {
      setAction(null);
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-light-base pt-36 dark:bg-jacarta-900">
        <div className="container flex min-h-[50vh] items-center justify-center">
          <span className="h-10 w-10 animate-spin rounded-full border-4 border-accent/20 border-t-accent" />
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#F7F7FB] pb-24 pt-28 dark:bg-jacarta-900 md:pt-32">
      <section className="container">
        <div className="relative overflow-hidden rounded-[2rem] bg-[#171A43] px-6 py-8 text-white shadow-2xl md:px-10 md:py-12">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_78%_18%,rgba(131,88,255,.55),transparent_34%),radial-gradient(circle_at_20%_90%,rgba(69,191,239,.22),transparent_28%)]" />
          <div className="relative flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-5 flex items-center gap-3">
                <div className="flex h-14 w-14 items-center justify-center overflow-hidden rounded-2xl bg-white p-2 shadow-lg">
                  <Image src={community?.logo_url || "/img/logo.png"} alt="" width={120} height={40} className="h-auto w-full" />
                </div>
                <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold text-white/80">
                  唯一官方社区
                </span>
              </div>
              <h1 className="font-display text-3xl font-semibold md:text-5xl">{community?.name}</h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-white/70 md:text-base">{community?.description}</p>
              <div className="mt-6 flex flex-wrap gap-5 text-sm text-white/65">
                <span><strong className="text-lg text-white">{community?.member_count || 0}</strong> 位成员</span>
                <span><strong className="text-lg text-white">{community?.post_count || 0}</strong> 篇内容</span>
                <span><strong className="text-lg text-white">{completedCount}</strong> 个任务已完成</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              {!user ? (
                <Link href="/login" className="rounded-full bg-accent px-7 py-3.5 font-semibold text-white shadow-accent-volume transition-transform hover:-translate-y-0.5">
                  登录并加入
                </Link>
              ) : !joined ? (
                <button onClick={() => void join()} disabled={action === "join"} className="rounded-full bg-accent px-7 py-3.5 font-semibold text-white shadow-accent-volume disabled:opacity-60">
                  {action === "join" ? "加入中…" : "加入官方社区"}
                </button>
              ) : (
                <span className="rounded-full border border-green/35 bg-green/15 px-6 py-3 font-semibold text-green">✓ 已加入社区</span>
              )}
              <Link href="#creation" className="rounded-full border border-white/20 bg-white/10 px-6 py-3 font-semibold text-white transition-colors hover:bg-white/20">浏览创作</Link>
            </div>
          </div>
        </div>

        {notice && (
          <div className={`mt-6 rounded-2xl border px-5 py-4 text-sm font-semibold ${notice.kind === "success" ? "border-green/20 bg-green/10 text-green" : "border-red/20 bg-red/10 text-red"}`}>
            {notice.text}
          </div>
        )}

        <div className="mt-8 grid gap-8 xl:grid-cols-[1fr_340px]">
          <div className="space-y-8">
            <section id="check-in" className="scroll-mt-32 overflow-hidden rounded-[2rem] bg-white shadow-sm dark:bg-jacarta-800">
              <div className="grid md:grid-cols-[1.1fr_.9fr]">
                <div className="p-7 md:p-9">
                  <p className="text-xs font-bold uppercase tracking-[.2em] text-accent">Daily check-in</p>
                  <h2 className="mt-3 font-display text-2xl font-semibold text-jacarta-700 dark:text-white">每日签到</h2>
                  <p className="mt-3 max-w-xl text-sm leading-7 text-jacarta-500 dark:text-jacarta-300">每天一次，由服务端按北京时间记录。重复点击不会重复获得 FAN，连续七天还有额外奖励。</p>
                  <div className="mt-6 flex flex-wrap gap-3">
                    <div className="rounded-2xl bg-jacarta-50 px-5 py-4 dark:bg-white/[.05]">
                      <p className="text-xs text-jacarta-400">连续签到</p>
                      <p className="mt-1 font-display text-2xl font-semibold text-jacarta-700 dark:text-white">{checkIn?.streak_days || 0} 天</p>
                    </div>
                    <div className="rounded-2xl bg-accent/10 px-5 py-4">
                      <p className="text-xs text-accent">今日奖励</p>
                      <FanTokenAmount amount={checkIn?.reward_fan_tokens || 20} className="mt-1 font-display text-2xl font-semibold text-accent" />
                    </div>
                  </div>
                </div>
                <div className="flex min-h-64 items-center justify-center bg-[url('/img/fanora/activity-checkin.jpg')] bg-cover bg-center p-8">
                  <div className="w-full max-w-xs rounded-3xl border border-white/20 bg-[#101436]/80 p-6 text-center text-white backdrop-blur-lg">
                    {!user ? (
                      <Link href="/login" className="block rounded-full bg-accent py-3.5 font-semibold">登录后签到</Link>
                    ) : !user.is_official_member ? (
                      <Link href="/membership/join" className="block rounded-full bg-accent py-3.5 font-semibold">缴纳 1 MON 解锁签到</Link>
                    ) : !joined ? (
                      <button onClick={() => void join()} className="w-full rounded-full bg-accent py-3.5 font-semibold">先加入社区</button>
                    ) : (
                      <button
                        onClick={() => void performCheckIn()}
                        disabled={checkIn?.checked_in || action === "check-in"}
                        className="w-full rounded-full bg-accent py-3.5 font-semibold shadow-accent-volume disabled:bg-green disabled:shadow-none"
                      >
                        {action === "check-in" ? "签到中…" : checkIn?.checked_in ? "✓ 今日已签到" : "立即签到"}
                      </button>
                    )}
                    <p className="mt-4 text-xs leading-5 text-white/60">签到事实与奖励流水都保存在 Fanora 服务端。</p>
                  </div>
                </div>
              </div>
            </section>

            <section id="tasks" className="scroll-mt-32 rounded-[2rem] bg-white p-7 shadow-sm dark:bg-jacarta-800 md:p-9">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[.2em] text-accent">Fan missions</p>
                  <h2 className="mt-3 font-display text-2xl font-semibold text-jacarta-700 dark:text-white">任务模块</h2>
                  <p className="mt-2 text-sm text-jacarta-500 dark:text-jacarta-300">领取后回复指定帖子，发布成功即由系统验证并发放 FAN，无需人工审核。</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="rounded-full bg-green/10 px-4 py-2 text-xs font-semibold text-green">自动验证 · 幂等奖励</span>
                  <Link href="/community/tasks" className="group inline-flex items-center gap-2 rounded-full border border-accent/20 px-4 py-2 text-xs font-semibold text-accent transition-all hover:bg-accent hover:text-white">
                    更多 <span className="transition-transform group-hover:translate-x-1">→</span>
                  </Link>
                </div>
              </div>
              <div className="mt-7 grid gap-5 md:grid-cols-2">
                {tasks.map((task) => {
                  const rewarded = task.participation_status === "rewarded";
                  const claimed = task.participation_status === "claimed";
                  return (
                    <article key={task.id} className="flex flex-col rounded-3xl border border-jacarta-100 p-6 dark:border-white/10">
                      <div className="flex items-start justify-between gap-4">
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${rewarded ? "bg-green/10 text-green" : claimed ? "bg-orange/10 text-orange" : "bg-accent/10 text-accent"}`}>
                          {rewarded ? "已完成" : claimed ? "进行中" : "可领取"}
                        </span>
                        <FanTokenAmount amount={task.reward_fan_tokens} className="font-display text-lg font-semibold text-accent" />
                      </div>
                      <h3 className="mt-5 font-display text-xl font-semibold text-jacarta-700 dark:text-white">{task.title}</h3>
                      <p className="mt-3 flex-1 text-sm leading-6 text-jacarta-500 dark:text-jacarta-300">{task.description}</p>
                      <p className="mt-4 truncate rounded-xl bg-jacarta-50 px-3 py-2 text-xs text-jacarta-500 dark:bg-white/[.04] dark:text-jacarta-300">指定帖子：{task.target_post_title}</p>
                      <div className="mt-5 flex gap-3">
                        {claimed || rewarded ? (
                          <Link href={`/community/posts/${task.target_post_id}`} className="flex-1 rounded-full bg-accent px-5 py-3 text-center text-sm font-semibold text-white">
                            {rewarded ? "查看回复" : "去回复完成"}
                          </Link>
                        ) : user && task.eligible ? (
                          <button onClick={() => void claimTask(task)} disabled={action === `task:${task.id}`} className="flex-1 rounded-full bg-accent px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">
                            {action === `task:${task.id}` ? "领取中…" : "领取任务"}
                          </button>
                        ) : !user ? (
                          <Link href="/login" className="flex-1 rounded-full bg-accent px-5 py-3 text-center text-sm font-semibold text-white">登录后领取</Link>
                        ) : !user.is_official_member ? (
                          <Link href="/membership/join" className="flex-1 rounded-full bg-accent px-5 py-3 text-center text-sm font-semibold text-white">正式入会后领取</Link>
                        ) : !joined ? (
                          <button onClick={() => void join()} className="flex-1 rounded-full bg-accent px-5 py-3 text-sm font-semibold text-white">先加入社区</button>
                        ) : (
                          <span className="flex-1 rounded-full bg-jacarta-50 px-5 py-3 text-center text-sm font-semibold text-jacarta-400 dark:bg-white/[.05]">{task.unavailable_reason}</span>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>

            <section id="creation" className="scroll-mt-32 rounded-[2rem] bg-white p-7 shadow-sm dark:bg-jacarta-800 md:p-9">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[.2em] text-accent">Creation community</p>
                  <h2 className="mt-3 font-display text-2xl font-semibold text-jacarta-700 dark:text-white">创作社区模块</h2>
                  <p className="mt-2 text-sm text-jacarta-500 dark:text-jacarta-300">分享故事、歌单与作品，也可以进入主题帖参与任务。</p>
                </div>
                <div className="flex items-center gap-3">
                  <Link href="/community/creations" className="group inline-flex items-center gap-2 rounded-full border border-accent/20 px-4 py-2 text-sm font-semibold text-accent transition-all hover:bg-accent hover:text-white">
                    更多 <span className="transition-transform group-hover:translate-x-1">→</span>
                  </Link>
                  {user?.is_official_member && joined && (
                    <button onClick={() => setShowComposer((current) => !current)} className="rounded-full bg-accent px-5 py-3 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5">
                      {showComposer ? "收起发布框" : "+ 发布创作"}
                    </button>
                  )}
                </div>
              </div>

              {showComposer && (
                <form onSubmit={createPost} className="mt-6 rounded-3xl border border-accent/20 bg-accent/[.035] p-5 md:p-6">
                  <div className="grid gap-4 md:grid-cols-[1fr_160px]">
                    <input required minLength={4} maxLength={120} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="给创作起一个标题" className="rounded-xl border-jacarta-100 bg-white dark:border-white/10 dark:bg-jacarta-700 dark:text-white" />
                    <select value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value })} className="rounded-xl border-jacarta-100 bg-white dark:border-white/10 dark:bg-jacarta-700 dark:text-white">
                      <option value="creation">共创</option>
                      <option value="story">故事</option>
                      <option value="music">音乐</option>
                      <option value="discussion">讨论</option>
                    </select>
                  </div>
                  <textarea required minLength={10} maxLength={10000} rows={5} value={draft.body} onChange={(event) => setDraft({ ...draft, body: event.target.value })} placeholder="写下你的内容…" className="mt-4 w-full resize-none rounded-xl border-jacarta-100 bg-white dark:border-white/10 dark:bg-jacarta-700 dark:text-white" />
                  <button disabled={action === "create-post"} className="mt-4 rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white disabled:opacity-60">{action === "create-post" ? "发布中…" : "发布到社区"}</button>
                </form>
              )}

              <div className="mt-7 grid gap-5 md:grid-cols-2">
                {posts.map((post) => (
                  <Link key={post.id} href={`/community/posts/${post.id}`} className="group overflow-hidden rounded-3xl border border-jacarta-100 transition-all hover:-translate-y-1 hover:shadow-xl dark:border-white/10">
                    <div className="h-44 overflow-hidden bg-jacarta-100 dark:bg-jacarta-700">
                      {post.cover_url ? <Image src={post.cover_url} alt="" width={720} height={360} className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" /> : <div className="h-full bg-gradient-to-br from-accent/60 to-[#45BFEF]/40" />}
                    </div>
                    <div className="p-5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="rounded-full bg-accent/10 px-3 py-1 font-semibold text-accent">{categoryLabels[post.category] || post.category}</span>
                        <span className="text-jacarta-400">{post.reply_count} 条回复</span>
                      </div>
                      <h3 className="mt-4 font-display text-lg font-semibold text-jacarta-700 transition-colors group-hover:text-accent dark:text-white">{post.title}</h3>
                      <p className="mt-3 line-clamp-2 text-sm leading-6 text-jacarta-500 dark:text-jacarta-300">{post.body_preview}</p>
                      <div className="mt-5 flex items-center gap-2">
                        <UserAvatar avatarUrl={post.author.avatar_url} seed={post.author.id} displayName={post.author.display_name} className="h-7 w-7 rounded-full" />
                        <span className="text-xs font-semibold text-jacarta-500 dark:text-jacarta-300">{post.author.display_name}</span>
                        <span className="ml-auto text-xs text-jacarta-400">{formatDate(post.updated_at)}</span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          </div>

          <aside className="space-y-6">
            <section className="rounded-[2rem] bg-white p-6 shadow-sm dark:bg-jacarta-800">
              <p className="text-xs font-bold uppercase tracking-[.18em] text-accent">Your progress</p>
              <h2 className="mt-2 font-display text-xl font-semibold text-jacarta-700 dark:text-white">我的社区成长</h2>
              {user ? (
                <>
                  <div className="mt-5 flex items-center gap-3 rounded-2xl bg-jacarta-50 p-4 dark:bg-white/[.04]">
                    <UserAvatar avatarUrl={user.avatar_url} seed={user.id} displayName={user.display_name} className="h-11 w-11 rounded-full" />
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-jacarta-700 dark:text-white">{user.display_name || "Fanora 用户"}</p>
                      <p className="mt-1 text-xs text-jacarta-400">{user.level}</p>
                    </div>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <div className="rounded-2xl bg-accent/10 p-4"><p className="text-xs text-accent">Fan Token</p><FanTokenAmount amount={user.fan_token_balance} className="mt-1 font-display text-xl font-semibold text-accent" /></div>
                    <div className="rounded-2xl bg-green/10 p-4"><p className="text-xs text-green">完成任务</p><p className="mt-1 font-display text-xl font-semibold text-green">{completedCount}</p></div>
                  </div>
                  <Link href="/profile" className="mt-4 block rounded-full border border-jacarta-100 py-3 text-center text-sm font-semibold text-jacarta-600 transition-colors hover:border-accent hover:text-accent dark:border-white/10 dark:text-white">查看完整身份</Link>
                </>
              ) : (
                <p className="mt-4 rounded-2xl bg-jacarta-50 p-4 text-sm leading-6 text-jacarta-500 dark:bg-white/[.04] dark:text-jacarta-300">登录后查看签到、任务进度和 FAN 流水。</p>
              )}
            </section>

            {user && (
              <section className="rounded-[2rem] bg-white p-6 shadow-sm dark:bg-jacarta-800">
                <div className="flex items-center justify-between">
                  <h2 className="font-display text-lg font-semibold text-jacarta-700 dark:text-white">最近 FAN 明细</h2>
                  <span className="text-xs text-jacarta-400">不可直接修改</span>
                </div>
                <div className="mt-4 space-y-3">
                  {ledger.length ? ledger.map((entry) => (
                    <div key={entry.id} className="flex items-center gap-3 rounded-2xl border border-jacarta-100 p-3 dark:border-white/10">
                      <span className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold ${entry.delta > 0 ? "bg-green/10 text-green" : "bg-red/10 text-red"}`}>{entry.delta > 0 ? "+" : "−"}</span>
                      <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-jacarta-700 dark:text-white">{entry.description}</p><p className="mt-1 text-xs text-jacarta-400">{formatDate(entry.created_at)}</p></div>
                      <FanTokenAmount amount={entry.delta} className={`text-sm font-semibold ${entry.delta > 0 ? "text-green" : "text-red"}`} />
                    </div>
                  )) : <p className="rounded-2xl bg-jacarta-50 p-4 text-sm text-jacarta-400 dark:bg-white/[.04]">完成签到或任务后，流水会显示在这里。</p>}
                </div>
              </section>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}
