"use client";

import axios from "axios";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import { useAuth } from "@/components/providers/AuthProvider";
import { fanTaskCatalogByKey } from "@/data/fanora";
import { api } from "@/lib/api/client";
import type { FanTask, OfficialCommunity } from "@/lib/api/types";

const statusFilters = [
  { id: "all", label: "全部任务" },
  { id: "available", label: "可领取" },
  { id: "claimed", label: "进行中" },
  { id: "rewarded", label: "已完成" },
];

const modeFilters = [
  { id: "all", label: "全部模式" },
  { id: "daily", label: "每日互动" },
  { id: "discussion", label: "社区回复" },
  { id: "creation", label: "内容共创" },
  { id: "event", label: "活动任务" },
  { id: "special", label: "特别收藏" },
];

const modeLabels: Record<string, string> = {
  daily_check_in: "每日签到",
  post_reply: "回复互动",
  content_publish: "发布创作",
  page_action: "专属页面",
  streak: "连续挑战",
  event_check_in: "活动打卡",
  future: "未来任务",
};

function message(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail || "任务操作没有完成。";
  return error instanceof Error ? error.message : "任务操作没有完成。";
}

function presentation(task: FanTask) {
  const catalog = task.presentation.catalog_key
    ? fanTaskCatalogByKey.get(task.presentation.catalog_key)
    : undefined;
  return {
    imageUrl: task.presentation.image_url || catalog?.imageSrc || "/img/fanora/activity-community.jpg",
    category: task.presentation.category || catalog?.category || "discussion",
    interactionPrompt: task.presentation.interaction_prompt || catalog?.interactionPrompt || "参与一次真实粉丝互动",
    actionUrl: task.presentation.action_url || catalog?.actionHref || (task.target_post_id ? `/community/posts/${task.target_post_id}` : "/community/tasks"),
    actionLabel: task.presentation.action_label || catalog?.actionLabel || "开始任务",
    badgeLabel: task.presentation.badge_label || catalog?.missionDetail || modeLabels[task.task_type],
    special: task.presentation.special || catalog?.special || false,
    order: catalog?.order ?? 999,
  };
}

export default function TaskGallery() {
  const { user, refreshUser } = useAuth();
  const router = useRouter();
  const [tasks, setTasks] = useState<FanTask[]>([]);
  const [community, setCommunity] = useState<OfficialCommunity | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [modeFilter, setModeFilter] = useState("all");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [taskResponse, communityResponse] = await Promise.all([
      api.get<FanTask[]>("/tasks"),
      api.get<OfficialCommunity>("/community"),
    ]);
    setTasks(taskResponse.data);
    setCommunity(communityResponse.data);
  }, []);

  useEffect(() => {
    void load().catch((error) => setNotice(message(error)));
  }, [load, user]);

  const joined = community?.joined || Boolean(user?.communities.some((item) => item.slug === "fanora-official"));
  const visibleTasks = useMemo(() => tasks
    .filter((task) => {
      if (statusFilter === "available" && !task.eligible) return false;
      if (["claimed", "rewarded"].includes(statusFilter) && task.participation_status !== statusFilter) return false;
      const view = presentation(task);
      if (modeFilter === "special" && !view.special) return false;
      if (modeFilter !== "all" && modeFilter !== "special" && view.category !== modeFilter) return false;
      return true;
    })
    .sort((left, right) => presentation(left).order - presentation(right).order), [modeFilter, statusFilter, tasks]);

  const join = async () => {
    setBusy("join");
    try {
      await api.post("/community/join");
      await Promise.all([refreshUser(), load()]);
      setNotice("已加入官方社区，现在可以领取任务。 ");
    } catch (error) {
      setNotice(message(error));
    } finally {
      setBusy(null);
    }
  };

  const claim = async (task: FanTask) => {
    setBusy(task.id);
    try {
      const response = await api.post<FanTask>(`/tasks/${task.id}/claim`);
      setTasks((current) => current.map((item) => (item.id === task.id ? response.data : item)));
      await refreshUser();
      if (response.data.participation_status === "rewarded") {
        setNotice("任务已完成，积分已经发放。 ");
      } else {
        setNotice("任务已领取，正在带你进入指定互动页面。 ");
        router.push(presentation(response.data).actionUrl);
      }
    } catch (error) {
      setNotice(message(error));
    } finally {
      setBusy(null);
    }
  };

  return (
    <main className="web3-page-shell min-h-screen pb-24 pt-28 md:pt-32">
      <div className="container">
        <section className="community-reveal relative overflow-hidden rounded-[2.25rem] border border-white/10 bg-[#101436] px-6 py-10 text-white shadow-[0_30px_100px_rgba(5,6,25,.45)] md:px-10 md:py-14">
          <div className="web3-orb -right-20 -top-24 h-72 w-72 bg-accent/35" />
          <div className="web3-orb -bottom-32 left-1/4 h-64 w-64 bg-[#45BFEF]/20 [animation-delay:-3s]" />
          <div className="relative max-w-3xl">
            <Link href="/community#tasks" className="text-sm font-semibold text-accent-lighter transition-colors hover:text-white">← 返回官方社区</Link>
            <p className="mt-8 text-xs font-bold uppercase tracking-[.28em] text-accent-light">Fan missions</p>
            <h1 className="mt-4 font-display text-4xl font-semibold md:text-6xl">粉丝任务中心</h1>
            <p className="mt-5 max-w-2xl text-sm leading-7 text-white/65 md:text-base">任务覆盖签到、回复、创作、连续挑战和专属活动。领取后完成真实互动，系统自动验证并发放 FAN，不需要人工审核。</p>
          </div>
        </section>

        {notice && <div className="community-reveal mt-6 rounded-2xl border border-accent/20 bg-accent/10 px-5 py-4 text-sm font-semibold text-accent-lighter">{notice}</div>}

        <section className="community-reveal mt-8 rounded-[1.75rem] border border-white/10 bg-[#101436]/75 p-4 [animation-delay:100ms] md:p-5">
          <div className="flex flex-wrap gap-2">
            {statusFilters.map((item) => (
              <button key={item.id} onClick={() => setStatusFilter(item.id)} className={`rounded-full px-5 py-2.5 text-sm font-semibold transition-all duration-300 ${statusFilter === item.id ? "bg-accent text-white shadow-accent-volume" : "border border-white/10 bg-white/5 text-jacarta-300 hover:border-accent/40 hover:text-white"}`}>{item.label}</button>
            ))}
          </div>
          <div className="mt-3 flex gap-2 overflow-x-auto border-t border-white/5 pt-3">
            {modeFilters.map((item) => (
              <button key={item.id} onClick={() => setModeFilter(item.id)} className={`shrink-0 rounded-xl px-4 py-2 text-xs font-semibold transition-all ${modeFilter === item.id ? "bg-white/10 text-accent-lighter" : "text-white/40 hover:text-white"}`}>{item.label}</button>
            ))}
          </div>
        </section>

        <section className="mt-7 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {visibleTasks.map((task, index) => {
            const view = presentation(task);
            const claimed = task.participation_status === "claimed";
            const rewarded = task.participation_status === "rewarded";
            const active = task.status === "published";
            return (
              <article key={task.id} className={`web3-interactive-card community-reveal flex min-h-[32rem] flex-col overflow-hidden rounded-[2rem] border bg-[#111538]/95 text-white ${view.special ? "border-accent/35 shadow-[0_0_55px_rgba(131,88,255,.14)]" : "border-white/10"}`} style={{ animationDelay: `${Math.min(index, 10) * 65}ms` }}>
                <div className="group relative h-48 overflow-hidden">
                  <Image src={view.imageUrl} alt={task.title} fill sizes="(max-width: 767px) 100vw, (max-width: 1279px) 50vw, 33vw" className="object-cover transition-transform duration-700 group-hover:scale-105" />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#111538] via-transparent to-black/15" />
                  <div className="absolute left-5 top-5 flex flex-wrap gap-2">
                    <span className="rounded-full border border-white/15 bg-[#0c102d]/75 px-3 py-1.5 text-[11px] font-bold text-white backdrop-blur">{view.badgeLabel}</span>
                    <span className="rounded-full bg-accent/80 px-3 py-1.5 text-[11px] font-bold text-white backdrop-blur">{modeLabels[task.task_type] || task.task_type}</span>
                  </div>
                </div>
                <div className="flex flex-1 flex-col p-6">
                  <div className="flex items-start justify-between gap-4">
                    <span className={`rounded-full px-3 py-1.5 text-xs font-bold ${rewarded ? "bg-green/15 text-green" : claimed ? "bg-orange/15 text-orange" : active ? "bg-accent/15 text-accent-lighter" : "bg-white/5 text-white/40"}`}>{rewarded ? "已完成" : claimed ? "进行中" : active ? "可领取" : "即将开放"}</span>
                    <FanTokenAmount amount={task.reward_fan_tokens} className="font-display text-xl font-semibold text-accent-light" />
                  </div>
                  <h2 className="mt-5 font-display text-2xl font-semibold leading-tight">{task.title}</h2>
                  <p className="mt-4 text-sm leading-7 text-white/55">{task.description}</p>
                  <div className="mt-5 rounded-2xl border border-accent/15 bg-accent/[.07] px-4 py-3 text-xs leading-5 text-accent-lighter">
                    <span className="font-bold text-white/70">互动目标</span><br />{view.interactionPrompt}
                  </div>
                  <div className="mt-4 flex items-center justify-between text-xs text-white/35">
                    <span>{task.participant_count.toLocaleString()} 人已领取</span>
                    {task.participation_limit && <span>限量 {task.participation_limit.toLocaleString()}</span>}
                  </div>
                  <div className="mt-auto pt-6">
                    {claimed || rewarded ? (
                      <Link href={view.actionUrl} className="web3-action-button block rounded-full py-3.5 text-center font-semibold text-white">{rewarded ? "查看互动成果" : view.actionLabel}</Link>
                    ) : !active ? (
                      <div className="rounded-full bg-white/5 py-3.5 text-center text-sm font-semibold text-white/35">{task.unavailable_reason || "任务即将开放"}</div>
                    ) : !user ? (
                      <Link href="/login" className="web3-action-button block rounded-full py-3.5 text-center font-semibold text-white">登录后领取</Link>
                    ) : !user.is_official_member ? (
                      <Link href="/membership/join" className="web3-action-button block rounded-full py-3.5 text-center font-semibold text-white">正式入会后领取</Link>
                    ) : !joined ? (
                      <button onClick={() => void join()} disabled={busy === "join"} className="web3-action-button w-full rounded-full py-3.5 font-semibold text-white">{busy === "join" ? "加入中…" : "先加入社区"}</button>
                    ) : task.eligible ? (
                      <button onClick={() => void claim(task)} disabled={busy === task.id} className="web3-action-button w-full rounded-full py-3.5 font-semibold text-white">{busy === task.id ? "领取中…" : "领取任务"}</button>
                    ) : (
                      <div className="rounded-full bg-white/5 py-3.5 text-center text-sm font-semibold text-white/35">{task.unavailable_reason || "当前不可领取"}</div>
                    )}
                    {view.special && view.actionUrl !== "/community/tasks" && !claimed && !rewarded && <Link href={view.actionUrl} className="mt-3 block text-center text-xs font-semibold text-accent-lighter transition-colors hover:text-white">预览专属任务页面 →</Link>}
                  </div>
                </div>
              </article>
            );
          })}
        </section>
      </div>
    </main>
  );
}
