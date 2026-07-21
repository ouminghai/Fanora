"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import type { FanTask } from "@/lib/api/types";

const labels = ["进行中", "即将开始", "已完成"];

export default function Collections() {
  const { user } = useAuth();
  const [activeLabel, setActiveLabel] = useState(labels[0]);
  const [tasks, setTasks] = useState<FanTask[]>([]);
  useEffect(() => { void api.get<FanTask[]>("/tasks").then((response) => setTasks(response.data)).catch(() => setTasks([])); }, []);
  const missions = useMemo(() => tasks.filter((task) => activeLabel === "已完成" ? task.participation_status === "rewarded" : activeLabel === "进行中" ? task.status === "published" : task.status !== "published").sort((left, right) => right.participant_count - left.participant_count || right.reward_fan_tokens - left.reward_fan_tokens).slice(0, 8), [activeLabel, tasks]);

  return <section id="missions" className="relative isolate overflow-hidden py-24 dark:bg-jacarta-800"><picture className="pointer-events-none absolute inset-0 -z-10 dark:hidden"><Image width={1920} height={789} src="/img/gradient_light.jpg" priority alt="gradient" className="h-full w-full" /></picture><div className="pointer-events-none absolute inset-0 z-0 mx-auto max-w-[90rem]" aria-hidden="true"><Image width={1413} height={760} src="/img/nft-game/crypto_icons.png" className="pointer-events-none absolute -top-1/4 animate-fly" alt="image" /></div><div className="container relative z-10"><div className="mb-12 text-center font-display text-3xl text-jacarta-700 dark:text-white"><h2 className="inline">热门粉丝任务</h2>{" "}<div className="dropdown inline cursor-pointer"><button className="dropdown-toggle inline-flex items-center text-accent" type="button" id="missionSort" data-bs-toggle="dropdown" aria-expanded="false">· {activeLabel}<span aria-hidden="true" className="ml-1 text-xl">⌄</span></button><div className="dropdown-menu z-10 hidden min-w-[200px] whitespace-nowrap rounded-xl bg-white px-2 py-4 text-left shadow-xl dark:bg-jacarta-800" aria-labelledby="missionSort">{labels.map((label) => <button type="button" onClick={() => setActiveLabel(label)} key={label} className="dropdown-item block w-full cursor-pointer rounded-xl px-5 py-2 text-left text-sm transition-colors hover:bg-jacarta-50 dark:hover:bg-jacarta-600">{label}</button>)}</div></div></div>
    {user && !user.is_official_member && <div className="mx-auto mb-8 flex max-w-2xl flex-col items-center gap-3 rounded-2xl border border-accent/25 bg-accent/10 px-5 py-4 text-center text-sm text-jacarta-700 backdrop-blur dark:text-white sm:flex-row sm:justify-between"><span>你目前是待入会用户，缴纳会费后才能参与签到和粉丝任务。</span><Link href="/membership/join" className="shrink-0 rounded-full bg-accent px-5 py-2.5 font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-accent-dark">缴纳会费正式加入</Link></div>}
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-[1.875rem] lg:grid-cols-4">{missions.map((task, index) => { const actionUrl = task.presentation.action_url || "/community/tasks"; const imageUrl = task.presentation.image_url || "/img/fanora/activity-community.jpg"; return <div key={task.id} className="flex rounded-2.5xl border border-jacarta-100 bg-white px-7 py-4 transition-shadow hover:shadow-lg dark:border-transparent dark:bg-jacarta-700"><figure className="mr-4 shrink-0 rtl:mr-0 rtl:ml-4"><Link href={actionUrl} className="relative block"><Image width={48} height={48} src={imageUrl} alt={task.title} className="h-12 w-12 rounded-2lg object-cover" loading="lazy" /><div className="absolute -left-3 top-1/2 flex h-6 w-6 -translate-y-2/4 items-center justify-center rounded-full border-2 border-white bg-jacarta-700 text-xs text-white dark:border-jacarta-600">{index + 1}</div></Link></figure><div><Link href={actionUrl} className="block"><span className="font-display font-semibold text-jacarta-700 hover:text-accent dark:text-white">{task.title}</span></Link><span className="flex flex-wrap items-center gap-1 text-sm dark:text-jacarta-300"><FanTokenAmount amount={task.reward_fan_tokens} prefix="+" /><span>· {task.participant_count} 人参与</span></span></div></div>; })}</div>
    <div className="mt-10 text-center"><Link href="/community/tasks" className="inline-block rounded-full bg-accent px-8 py-3 text-center font-semibold text-white shadow-accent-volume transition-all hover:bg-accent-dark">查看全部任务</Link></div>
  </div></section>;
}
