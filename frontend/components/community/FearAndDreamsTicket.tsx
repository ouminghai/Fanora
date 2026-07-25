"use client";

import axios from "axios";
import NiceModal from "@ebay/nice-modal-react";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import MarkdownEditor from "@/components/community/MarkdownEditor";
import GlobalInfoModal from "@/components/modals/GlobalInfoModal";
import GlobalProcessModal, { hideGlobalProcessModal } from "@/components/modals/GlobalProcessModal";
import type { TransactionPhase } from "@/components/nft/ChainTransactionProgress";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import type { FanTask, OfficialCommunity } from "@/lib/api/types";

const taskKey = "fear-and-dreams";
const ticketImage = "/img/fanora/eason-concert.webp";
const activeRewardStatuses = new Set(["PENDING", "CREATING_TOKEN_TYPE", "MINTING"]);

function message(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail || "纪念票任务操作没有完成。";
  return error instanceof Error ? error.message : "纪念票任务操作没有完成。";
}

function reviewModalCopy(task: FanTask) {
  const reasons = task.review_reasons.join("；") || "内容需要进一步确认";
  if (task.review_decision === "manual_review") {
    return {
      title: "需要人工确认",
      message: `AI Agent 暂时无法确认这段记忆是否完全回应任务。\n\n${reasons}\n\n你可以补充更具体的现场细节后重新提交。`,
    };
  }
  return {
    title: "审核未通过",
    message: `这次还没有完成任务。\n\n${reasons}\n\n建议加入演唱会现场细节、具体歌曲或情绪记忆，再提交一次。`,
  };
}

function TicketArtwork({
  imageUrl,
  phase,
}: {
  imageUrl: string;
  phase: "sealed" | "revealed";
}) {
  return (
    <div className={`reward-ticket-stage ${phase === "sealed" ? "is-sealed" : "is-revealed"} relative h-64 overflow-hidden`}>
      <Image
        src={imageUrl}
        alt="FEAR and DREAMS 纪念票预览"
        fill
        priority
        sizes="(max-width: 1023px) 100vw, 430px"
        className="reward-ticket-image object-cover"
      />
      <span className="reward-ticket-pixels" aria-hidden="true" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#151941] via-transparent to-black/20" />
      {phase === "sealed" ? (
        <span className="absolute inset-x-8 top-1/2 z-10 -translate-y-1/2 rounded-full border border-white/15 bg-black/45 py-2 text-center text-[10px] font-bold uppercase tracking-[.22em] text-white/75 backdrop-blur">
          Sealed until mint confirmed
        </span>
      ) : null}
      <span className="absolute right-5 top-5 z-10 rounded-full border border-white/20 bg-black/35 px-3 py-1 text-[10px] font-bold tracking-[.2em] backdrop-blur">MEMORIAL PASS</span>
    </div>
  );
}

export default function FearAndDreamsTicket() {
  const { user, refreshUser } = useAuth();
  const [task, setTask] = useState<FanTask | null>(null);
  const [community, setCommunity] = useState<OfficialCommunity | null>(null);
  const [memory, setMemory] = useState("");
  const [imageUrls, setImageUrls] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [rewardPhase, setRewardPhase] = useState<Exclude<TransactionPhase, "idle"> | "idle">("idle");

  const load = useCallback(async () => {
    const [tasksResponse, communityResponse] = await Promise.all([
      api.get<FanTask[]>("/tasks"),
      api.get<OfficialCommunity>("/community"),
    ]);
    setTask(tasksResponse.data.find((item) => item.presentation.catalog_key === taskKey) || null);
    setCommunity(communityResponse.data);
  }, []);

  useEffect(() => { void load().catch((error) => setNotice(message(error))); }, [load, user]);

  useEffect(() => {
    const status = task?.nft_reward_status;
    if (status === "CONFIRMED") {
      setRewardPhase("complete");
    } else if (status && activeRewardStatuses.has(status)) {
      setRewardPhase("processing");
    } else if (busy !== "complete") {
      setRewardPhase("idle");
    }
  }, [busy, task?.nft_reward_status]);

  const joined = community?.joined || Boolean(user?.communities.some((item) => item.slug === "fanora-official"));
  const artUrl = task?.presentation.image_url || ticketImage;
  const ticketRevealed = task?.nft_reward_status === "CONFIRMED" || rewardPhase === "complete";
  const ticketSealed = rewardPhase === "processing" || Boolean(task?.participation_status === "rewarded" && !ticketRevealed);

  const claim = async () => {
    if (!task) return;
    setBusy("claim");
    try {
      const response = await api.post<FanTask>(`/tasks/${task.id}/claim`);
      setTask(response.data);
      setNotice("纪念票任务已领取。写下现场记忆后即可完成本阶段任务。 ");
    } catch (error) { setNotice(message(error)); } finally { setBusy(null); }
  };

  const join = async () => {
    setBusy("join");
    try {
      await api.post("/community/join");
      await Promise.all([load(), refreshUser()]);
      setNotice("已加入链上社区，现在可以领取纪念票任务。 ");
    } catch (error) { setNotice(message(error)); } finally { setBusy(null); }
  };

  const complete = async () => {
    if (!task || memory.trim().length < 2) {
      void NiceModal.show(GlobalInfoModal, {
        title: "再写一点现场记忆",
        message: "写下与 FEAR and DREAMS 相关的真实感受或现场瞬间即可，简短表达也可以。",
        tone: "warning",
        eyebrow: "MEMORY REQUIRED",
        confirmLabel: "继续填写",
      });
      return;
    }
    setBusy("complete");
    setRewardPhase("processing");
    setNotice(null);
    void NiceModal.show(GlobalProcessModal, {
      title: "审核与铸造进行中",
      message: "AI 会先判断内容是否真实参与任务，通过后依次写入 IPFS 并提交 Monad 铸造。确认前页面暂时锁定。",
      eyebrow: "MONAD TRANSACTION",
      gifUrl: null,
      phase: "processing",
      progressKind: "quest-reward",
      artifactName: "FEAR and DREAMS 纪念票",
      imageUrl: artUrl,
    });
    try {
      const response = await api.post<FanTask>(`/tasks/${task.id}/complete`, { interaction_note: memory.trim(), image_urls: imageUrls });
      setTask(response.data);
      await refreshUser();
      await hideGlobalProcessModal();
      if (response.data.participation_status === "rewarded") {
        setImageUrls([]);
        if (response.data.nft_reward_status === "CONFIRMED") {
          setRewardPhase("complete");
          void NiceModal.show(GlobalInfoModal, {
            title: "获得 FEAR and DREAMS 纪念票",
            message: "AI 审核已通过，500 FAN 已发放。纪念票 NFT 已在 Monad 上完成铸造，卡面已经揭晓。",
            tone: "success",
            imageUrl: artUrl,
            imageAlt: "FEAR and DREAMS 纪念票",
            celebrate: true,
            actionLabel: "查看链上 NFT",
            actionUrl: response.data.nft_explorer_url,
          });
        } else if (response.data.nft_reward_status === "WAITING_CONFIGURATION") {
          setRewardPhase("idle");
          setNotice("AI 审核已通过，500 FAN 已发放；纪念票铸造已登记，等待部署环境完成 Pinata 与 Monad 配置。");
        } else if (response.data.nft_reward_status === "RETRYABLE") {
          setRewardPhase("idle");
          void NiceModal.show(GlobalInfoModal, {
            title: "纪念票铸造可重试",
            message: "AI 审核已通过，500 FAN 已发放；但 NFT 铸造或上传暂时失败，系统已保存可重试状态。",
            tone: "warning",
          });
        } else {
          setRewardPhase("processing");
          setNotice("AI 审核已通过，500 FAN 已发放，纪念票正在进入链上铸造流程。");
        }
      } else {
        setRewardPhase("idle");
        const copy = reviewModalCopy(response.data);
        void NiceModal.show(GlobalInfoModal, { ...copy, tone: "warning" });
      }
    } catch (error) {
      setRewardPhase("idle");
      await hideGlobalProcessModal();
      void NiceModal.show(GlobalInfoModal, {
        title: "任务暂时没有完成",
        message: message(error),
        tone: "error",
        eyebrow: "TASK ERROR",
        confirmLabel: "返回重试",
      });
    } finally {
      setBusy(null);
    }
  };

  return (
    <main className="web3-page-shell min-h-screen overflow-hidden pb-24 pt-28 text-white md:pt-32">
      <div className="container">
        <Link href="/community/tasks" className="community-reveal text-sm font-semibold text-accent-lighter transition-colors hover:text-white">← 返回粉丝任务中心</Link>

        <section className="community-reveal relative mt-6 overflow-hidden rounded-[2.5rem] border border-accent/25 bg-[#0d102d] p-6 shadow-[0_35px_120px_rgba(5,6,25,.65)] md:p-10 lg:p-14">
          <div className="web3-orb -right-28 -top-28 h-96 w-96 bg-accent/30" />
          <div className="web3-orb -bottom-36 left-1/3 h-80 w-80 bg-[#45BFEF]/15 [animation-delay:-4s]" />
          <div className="relative grid items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(360px,.72fr)]">
            <div>
              <span className="inline-flex rounded-full border border-accent/30 bg-accent/10 px-4 py-2 text-xs font-bold uppercase tracking-[.24em] text-accent-lighter">Special mission · Ticket preview</span>
              <h1 className="mt-7 max-w-4xl font-display text-5xl font-semibold leading-[.95] md:text-7xl">FEAR<br /><span className="text-accent-light">and DREAMS</span></h1>
              <p className="mt-7 max-w-2xl text-base leading-8 text-white/60">把一次现场相遇保存成长期粉丝记忆。提交内容由 AI Agent 检查相关性与灌水，通过后发放 FAN，并使用演唱会纪念图铸造一张限量 ERC-1155 纪念票。</p>
              <div className="mt-8 flex flex-wrap gap-3 text-sm">
                <span className="rounded-full bg-white/5 px-4 py-2 text-white/65">演唱会纪念</span>
                <span className="rounded-full bg-white/5 px-4 py-2 text-white/65">限时活动</span>
                <span className="rounded-full bg-white/5 px-4 py-2 text-white/65">AI 内容审核</span>
                <span className="rounded-full bg-white/5 px-4 py-2 text-white/65">ERC-1155 纪念票</span>
              </div>
            </div>

            <div className={`web3-interactive-card relative mx-auto w-full max-w-md overflow-hidden rounded-[2rem] border border-white/20 bg-[#151941] shadow-[0_30px_80px_rgba(0,0,0,.45)] ${ticketRevealed ? "nft-flow-border" : ""}`}>
              <TicketArtwork imageUrl={artUrl} phase={ticketSealed ? "sealed" : "revealed"} />
              <div className="relative p-7">
                <div className="absolute -top-3 left-0 h-6 w-6 -translate-x-1/2 rounded-full bg-[#0d102d]" />
                <div className="absolute -top-3 right-0 h-6 w-6 translate-x-1/2 rounded-full bg-[#0d102d]" />
                <div className="border-t border-dashed border-white/20 pt-6">
                  <div className="flex items-end justify-between gap-5">
                    <div><p className="text-[10px] uppercase tracking-[.24em] text-white/35">Fanora Archive</p><h2 className="mt-2 font-display text-2xl font-semibold">FEAR and DREAMS</h2></div>
                    <div className="text-right"><p className="text-[10px] uppercase tracking-[.2em] text-white/35">Reward</p>{task ? <FanTokenAmount amount={task.reward_fan_tokens} className="mt-2 font-display text-xl font-semibold text-accent-light" /> : <span className="mt-2 block text-accent-light">500 FAN</span>}</div>
                  </div>
                  <div className="mt-6 flex justify-between font-mono text-[10px] tracking-[.16em] text-white/35"><span>FANORA / 2026</span><span>NO. FAD-0001</span></div>
                  {ticketRevealed ? <p className="mt-4 text-xs font-semibold text-green">Mint confirmed · NFT revealed</p> : null}
                </div>
              </div>
            </div>
          </div>
        </section>

        {notice && <div className="community-reveal mt-6 rounded-2xl border border-accent/20 bg-accent/10 px-5 py-4 text-sm font-semibold text-accent-lighter">{notice}</div>}

        <section className="community-reveal mt-8 grid gap-6 lg:grid-cols-[1fr_360px] [animation-delay:120ms]">
          <div className="rounded-[2rem] border border-white/10 bg-[#111538] p-6 md:p-8">
            <p className="text-xs font-bold uppercase tracking-[.24em] text-accent-light">Your live memory</p>
            <h2 className="mt-4 font-display text-3xl font-semibold">你最想留住哪一个现场瞬间？</h2>
            <p className="mt-4 text-sm leading-7 text-white/50">用 Markdown 写下现场记忆，也可以上传多张图片。Agent 会判断内容是否回应演唱会主题、是否有真实信息量以及是否存在明显灌水。</p>
            <MarkdownEditor value={memory} onChange={setMemory} maxLength={300} imageUrls={imageUrls} onImageUrlsChange={setImageUrls} onImageError={setNotice} />
          </div>

          <aside className="rounded-[2rem] border border-white/10 bg-[#111538] p-6 md:p-8">
            <h2 className="font-display text-2xl font-semibold">领取流程</h2>
            <ol className="mt-6 space-y-5 text-sm text-white/55">
              <li className="flex gap-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-bold text-white">1</span><span>加入 Fanora 链上社区并领取任务</span></li>
              <li className="flex gap-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-bold text-white">2</span><span>写下与主题相关的真实现场记忆</span></li>
              <li className="flex gap-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-bold text-white">3</span><span>通过 AI 审核，领取 500 FAN 与纪念票 NFT</span></li>
            </ol>
            <div className="mt-7">
              {!user ? <Link href="/login" className="web3-action-button block rounded-full py-3.5 text-center font-semibold">登录后领取</Link>
                : !user.is_official_member ? <Link href="/membership/join" className="web3-action-button block rounded-full py-3.5 text-center font-semibold">正式入会后领取</Link>
                  : !joined ? <button onClick={() => void join()} disabled={busy === "join"} className="web3-action-button w-full rounded-full py-3.5 font-semibold">{busy === "join" ? "加入中…" : "先加入链上社区"}</button>
                    : !task ? <div className="rounded-full bg-white/5 py-3.5 text-center text-sm text-white/35">任务加载中…</div>
                      : !task.participation_status ? <button onClick={() => void claim()} disabled={busy === "claim" || !task.eligible} className="web3-action-button w-full rounded-full py-3.5 font-semibold disabled:opacity-45">{busy === "claim" ? "领取中…" : "领取纪念票任务"}</button>
                        : task.participation_status === "claimed" ? <button onClick={() => void complete()} disabled={busy === "complete" || memory.trim().length < 2} className="web3-action-button w-full rounded-full py-3.5 font-semibold disabled:opacity-45">{busy === "complete" ? "AI 审核中…" : "提交审核并领取纪念票"}</button>
                          : task.nft_reward_status === "CONFIRMED" && task.nft_explorer_url ? <a href={task.nft_explorer_url} target="_blank" rel="noreferrer" className="block rounded-full border border-green/20 bg-green/10 py-3.5 text-center text-sm font-semibold text-green">✓ 查看链上纪念票 ↗</a>
                            : <div className="rounded-full border border-green/20 bg-green/10 py-3.5 text-center text-sm font-semibold text-green">✓ 任务完成 · NFT {task.nft_reward_status || "处理中"}</div>}
            </div>
            <div className="mt-5 rounded-xl border border-white/10 bg-white/[.035] p-4 text-xs leading-6 text-white/42">
              提交后会在页面中央显示审核与铸造进度，并锁定背景操作；确认后卡面逐渐清晰，再弹出获得 NFT 提示。
            </div>
            {task?.review_decision && <p className="mt-5 text-xs leading-5 text-white/45">最近审核：{task.review_decision} · {task.review_quality_score ?? 0}/100{task.review_reasons.length ? ` · ${task.review_reasons.join("；")}` : ""}</p>}
            <p className="mt-3 text-xs leading-5 text-white/30">Agent 只输出结构化审核结论；FAN 发放和 ERC-1155 铸造由后端业务服务执行。未配置链上环境时会明确保留待铸造状态，不伪造交易。</p>
          </aside>
        </section>
      </div>
    </main>
  );
}
