"use client";

import { Bot, Cpu, Fingerprint, ScanLine, Sparkles } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import type { FanTask } from "@/lib/api/types";
import styles from "./Collections.module.css";

const labels = ["进行中", "即将开始", "已完成"];

function shortAddress(address: string | undefined) {
  if (!address) return "0xFANORA...AGENT";
  return `${address.slice(0, 10)}...${address.slice(-8)}`;
}

export default function Collections() {
  const { user } = useAuth();
  const [activeLabel, setActiveLabel] = useState(labels[0]);
  const [tasks, setTasks] = useState<FanTask[]>([]);
  useEffect(() => { void api.get<FanTask[]>("/tasks").then((response) => setTasks(response.data)).catch(() => setTasks([])); }, []);
  const missions = useMemo(() => tasks.filter((task) => activeLabel === "已完成" ? task.participation_status === "rewarded" : activeLabel === "进行中" ? task.status === "published" : task.status !== "published").sort((left, right) => right.participant_count - left.participant_count || right.reward_fan_tokens - left.reward_fan_tokens).slice(0, 8), [activeLabel, tasks]);
  const identityProgress = Math.min(100, Math.max(12, Math.round((user?.fan_token_lifetime_earned ?? 120) / 10)));

  return (
    <section id="missions" className={styles.missionSection}>
      <div className={styles.cryptoBackdrop} aria-hidden="true"><Image width={1413} height={760} src="/img/nft-game/crypto_icons.png" className="animate-fly" alt="" /></div>
      <div className="container relative z-10">
        <section className={styles.agentAwakening} aria-label="Fanora AI Agent NFT 创作">
          <div className={styles.agentCopy}>
            <span><Bot /> FANORA NFT CREATION AGENT</span>
            <h2>把真实故事，唤醒为你的链上数字身份。</h2>
            <p>通过多轮对话持续整理故事、名称、作品描述与视觉提示词。Agent 会在画面方向真正变化时询问你，再调用生图工具生成 NFT 或粉丝周边。</p>
            <div className={styles.agentCapabilities}>
              <span><Cpu /> LangGraph State</span>
              <span><Fingerprint /> Visual Identity</span>
              <span><ScanLine /> BeeImg Reference</span>
            </div>
            <Link href="/collections/create" className={styles.agentAction}><Sparkles /> 进入 AI NFT 创作台</Link>
          </div>

          <div className={styles.identityStage}>
            <div className={styles.dataHelix} aria-hidden="true">{Array.from({ length: 10 }, (_, index) => <i key={index} />)}</div>
            <div className={styles.identityCard}>
              <span className={styles.cardScan} aria-hidden="true" />
              <header><span>CYBER IDENTITY</span><strong>ON-CHAIN PASSPORT</strong></header>
              <div className={styles.identityBody}>
                <div className={styles.avatarOrbit}>
                  <span className={styles.avatarPhoton} />
                  <Image
                    src={user?.avatar_url || "/img/agent/bot.webp"}
                    alt={user?.display_name || "Fanora Agent 身份"}
                    width={104}
                    height={104}
                    unoptimized
                  />
                  <i className={styles.hologramBadge}><Fingerprint /></i>
                </div>
                <div className={styles.identityData}>
                  <small>IDENTITY HOLDER</small>
                  <h3>{user?.display_name || "FANORA CREATOR"}</h3>
                  <span className={styles.walletAddress}>{shortAddress(user?.primary_wallet.address)}</span>
                  <p>{user?.level || "数字灵魂待激活"} · {user?.fan_type || "AI 共创者"}</p>
                </div>
              </div>
              <footer>
                <div className={styles.progressRing} style={{ background: `conic-gradient(#d8b4fe ${identityProgress * 3.6}deg, rgba(255,255,255,.08) 0deg)` }}><span>{identityProgress}%</span></div>
                <p>IDENTITY GROWTH<strong>{user?.fan_token_lifetime_earned ?? 0} LIFETIME FAN</strong></p>
                <span className={styles.nftBadge}>NFT BADGE<i /></span>
              </footer>
            </div>
          </div>
        </section>

        <div className={styles.missionHeading}>
          <h2>热门粉丝任务</h2>
          <div className="dropdown inline cursor-pointer">
            <button className="dropdown-toggle inline-flex items-center text-accent-light" type="button" id="missionSort" data-bs-toggle="dropdown" aria-expanded="false">· {activeLabel}<span aria-hidden="true" className="ml-1 text-xl">⌄</span></button>
            <div className="dropdown-menu z-10 hidden min-w-[200px] whitespace-nowrap rounded-xl border border-white/10 bg-[#111538] px-2 py-4 text-left text-white shadow-xl" aria-labelledby="missionSort">{labels.map((label) => <button type="button" onClick={() => setActiveLabel(label)} key={label} className="dropdown-item block w-full cursor-pointer rounded-xl px-5 py-2 text-left text-sm transition-colors hover:bg-white/10">{label}</button>)}</div>
          </div>
        </div>

        {user && !user.is_official_member ? <div className={styles.memberNotice}><span>你目前是待入会用户，激活会员身份后才能参与签到和粉丝任务。</span><Link href="/membership/join">正式加入 Fans Club</Link></div> : null}

        <div className={styles.missionGrid}>{missions.map((task, index) => {
          const actionUrl = task.presentation.action_url || "/community/tasks";
          const imageUrl = task.presentation.image_url || "/img/fanora/activity-community.jpg";
          return (
            <article key={task.id} className={styles.missionCard}>
              <figure><Link href={actionUrl}><Image width={52} height={52} src={imageUrl} alt={task.title} loading="lazy" /><span>{index + 1}</span></Link></figure>
              <div><Link href={actionUrl}><strong>{task.title}</strong></Link><span><FanTokenAmount amount={task.reward_fan_tokens} prefix="+" /> · {task.participant_count} 人参与</span></div>
            </article>
          );
        })}</div>
        <div className={styles.allTasks}><Link href="/community/tasks">查看全部任务</Link></div>
      </div>
    </section>
  );
}
