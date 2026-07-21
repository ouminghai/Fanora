"use client";

import axios from "axios";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import { useAuth } from "@/components/providers/AuthProvider";
import { fanTaskCatalogByKey } from "@/data/fanora";
import { api } from "@/lib/api/client";
import type { FanTask, OfficialCommunity } from "@/lib/api/types";

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

function arrangeGalleryGroup(tasks: FanTask[]) {
  const arranged = [...tasks];
  const featuredIndex = arranged.findIndex((task) => presentation(task).special);
  if (featuredIndex < 0) return arranged;

  const [featuredTask] = arranged.splice(featuredIndex, 1);
  arranged.splice(Math.min(4, arranged.length), 0, featuredTask);
  return arranged;
}

export default function TaskGallery() {
  const { user, refreshUser } = useAuth();
  const router = useRouter();
  const [tasks, setTasks] = useState<FanTask[]>([]);
  const [community, setCommunity] = useState<OfficialCommunity | null>(null);
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
  const visibleTasks = useMemo(
    () => [...tasks].sort((left, right) => presentation(left).order - presentation(right).order),
    [tasks],
  );
  const taskGalleryGroups = useMemo(() => {
    const groups: FanTask[][] = [];
    for (let index = 0; index < visibleTasks.length; index += 9) {
      groups.push(arrangeGalleryGroup(visibleTasks.slice(index, index + 9)));
    }
    return groups;
  }, [visibleTasks]);

  const join = async () => {
    setBusy("join");
    try {
      await api.post("/community/join");
      await Promise.all([refreshUser(), load()]);
      setNotice("已加入链上社区，现在可以领取任务。 ");
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

  const renderTaskCard = (task: FanTask, featured = false, animationIndex = 0) => {
    const view = presentation(task);
    const claimed = task.participation_status === "claimed";
    const rewarded = task.participation_status === "rewarded";
    const active = task.status === "published";
    const statusLabel = rewarded ? "已完成" : claimed ? "进行中" : active ? "可领取" : "即将开放";
    const cardClassName = `community-task-card group relative block aspect-square overflow-hidden rounded-2.5xl border bg-[#111538] ${featured ? "border-accent/45 shadow-[0_0_48px_rgba(131,88,255,.2)]" : "border-white/10"}`;
    const cardStyle = { "--community-item-delay": `${Math.min(animationIndex, 12) * 55}ms` } as CSSProperties;
    const content = (
      <>
        <Image
          src={view.imageUrl}
          alt={task.title}
          fill
          sizes={featured ? "(max-width: 1024px) 100vw, 34vw" : "(max-width: 1024px) 50vw, 17vw"}
          className="object-cover transition-transform duration-[1600ms] will-change-transform group-hover:scale-105"
        />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#0d102d]/90 via-[#0d102d]/10 to-transparent" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 p-4 text-white md:p-5">
          <h2 className={`font-display font-semibold leading-tight ${featured ? "text-xl md:text-3xl" : "text-sm xl:text-base"}`}>{task.title}</h2>
          <div className="mt-2 flex items-center gap-2 text-2xs text-white/75">
            <span>{statusLabel}</span>
            <span aria-hidden="true">·</span>
            <FanTokenAmount amount={task.reward_fan_tokens} className="font-semibold text-accent-lighter" />
          </div>
        </div>
      </>
    );

    if (claimed || rewarded) {
      return <Link key={task.id} style={cardStyle} href={view.actionUrl} aria-label={`${statusLabel}：${task.title}`} className={cardClassName}>{content}</Link>;
    }
    if (!active) {
      if (view.special && view.actionUrl !== "/community/tasks") {
        return <Link key={task.id} style={cardStyle} href={view.actionUrl} aria-label={`预览任务：${task.title}`} className={cardClassName}>{content}</Link>;
      }
      return <article key={task.id} style={cardStyle} aria-label={`${statusLabel}：${task.title}`} className={`${cardClassName} cursor-not-allowed opacity-75`}>{content}</article>;
    }
    if (!user) {
      return <Link key={task.id} style={cardStyle} href="/login" aria-label={`登录后领取：${task.title}`} className={cardClassName}>{content}</Link>;
    }
    if (!user.is_official_member) {
      return <Link key={task.id} style={cardStyle} href="/membership/join" aria-label={`入会后领取：${task.title}`} className={cardClassName}>{content}</Link>;
    }
    if (!joined) {
      return <button key={task.id} style={cardStyle} type="button" onClick={() => void join()} disabled={busy === "join"} aria-label="加入链上社区" className={`${cardClassName} w-full text-left disabled:cursor-wait disabled:opacity-60`}>{content}</button>;
    }
    if (task.eligible) {
      return <button key={task.id} style={cardStyle} type="button" onClick={() => void claim(task)} disabled={busy === task.id} aria-label={`领取任务：${task.title}`} className={`${cardClassName} w-full text-left disabled:cursor-wait disabled:opacity-60`}>{content}</button>;
    }
    return <article key={task.id} style={cardStyle} aria-label={task.unavailable_reason || `${statusLabel}：${task.title}`} className={`${cardClassName} cursor-not-allowed opacity-75`}>{content}</article>;
  };

  return (
    <main className="community-page-enter web3-page-shell min-h-screen pb-24 pt-28 md:pt-32">
      <div className="w-full px-5 lg:px-6">
        {notice && <div className="community-notice-enter mb-6 rounded-2xl border border-accent/20 bg-accent/10 px-5 py-4 text-sm font-semibold text-accent-lighter">{notice}</div>}

        <section className="space-y-5">
          {taskGalleryGroups.map((group, groupIndex) => (
            group.length === 9 ? (
              <div key={`gallery-${groupIndex}`} className="community-section-enter grid gap-5 lg:grid-cols-3">
                <div className="grid min-w-0 grid-cols-2 grid-rows-2 gap-5">
                  {group.slice(0, 4).map((task, taskIndex) => renderTaskCard(task, false, groupIndex * 9 + taskIndex))}
                </div>
                <div className="min-w-0 aspect-square">
                  {renderTaskCard(group[4], true, groupIndex * 9 + 4)}
                </div>
                <div className="grid min-w-0 grid-cols-2 grid-rows-2 gap-5">
                  {group.slice(5).map((task, taskIndex) => renderTaskCard(task, false, groupIndex * 9 + taskIndex + 5))}
                </div>
              </div>
            ) : (
              <div key={`gallery-${groupIndex}`} className="community-section-enter grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {group.map((task, taskIndex) => renderTaskCard(task, false, groupIndex * 9 + taskIndex))}
              </div>
            )
          ))}
        </section>
      </div>
    </main>
  );
}
