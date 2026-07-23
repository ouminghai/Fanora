"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";

export type TransactionPhase = "idle" | "processing" | "complete";
type TransactionKind = "publish" | "mint" | "identity" | "member-card";

const stepLabels: Record<TransactionKind, string[]> = {
  publish: ["提交发布", "写入 IPFS", "合约铸造", "链上确认"],
  mint: ["提交购买", "扣除 FAN", "铸造 NFT", "钱包确认"],
  identity: ["读取身份", "同步等级", "验证 Owner", "区块确认"],
  "member-card": ["验证会员身份", "合成会员证", "写入 IPFS", "链上确认"],
};

export default function ChainTransactionProgress({
  phase,
  kind,
  title,
  detail,
  artifactName,
  imageUrl,
  compact = false,
}: {
  phase: Exclude<TransactionPhase, "idle">;
  kind: TransactionKind;
  title: string;
  detail: string;
  artifactName: string;
  imageUrl?: string | null;
  compact?: boolean;
}) {
  const steps = useMemo(() => stepLabels[kind], [kind]);
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    if (phase === "complete") {
      setActiveStep(steps.length);
      return;
    }
    setActiveStep(0);
    const timer = window.setInterval(() => {
      setActiveStep((current) => Math.min(steps.length - 1, current + 1));
    }, 720);
    return () => window.clearInterval(timer);
  }, [phase, steps.length]);

  return (
    <div className={`chain-transaction-progress ${compact ? "is-compact" : ""}`} aria-live="polite">
      <div className="text-center">
        <p className="text-[10px] font-bold uppercase tracking-[.18em] text-[#45bfef]">Monad Transaction</p>
        <h3 className={`${compact ? "mt-2 text-lg" : "mt-3 text-2xl"} font-display font-semibold text-jacarta-700 dark:text-white`}>{title}</h3>
        <p className={`mx-auto mt-2 max-w-lg leading-6 text-jacarta-500 dark:text-jacarta-300 ${compact ? "text-xs" : "text-sm"}`}>{detail}</p>
      </div>

      <div className="chain-transaction-nodes" aria-label="交易确认进度">
        {steps.map((label, index) => {
          const completed = activeStep > index;
          const current = activeStep === index && phase !== "complete";
          return (
            <div key={label} className="chain-transaction-step">
              {index > 0 ? <span className={`chain-transaction-link ${activeStep >= index ? "is-connected" : ""}`} /> : null}
              <span className={`chain-transaction-node ${completed ? "is-complete" : ""} ${current ? "is-current" : ""}`}>
                {completed ? "✓" : index + 1}
              </span>
              <span className="chain-transaction-label">{label}</span>
            </div>
          );
        })}
      </div>

      {phase === "complete" ? (
        <div className={`chain-transaction-artifact ${kind === "identity" ? "is-block" : "is-nft"}`}>
          {kind !== "identity" && imageUrl ? (
            <span className="relative block h-14 w-14 shrink-0 overflow-hidden rounded-md bg-black/10">
              <Image src={imageUrl} alt="" fill unoptimized className="object-cover" sizes="56px" />
            </span>
          ) : (
            <span className="chain-transaction-cube" aria-hidden="true"><i /><i /><i /></span>
          )}
          <span className="min-w-0 text-left">
            <span className="block text-[10px] font-bold uppercase tracking-[.16em] text-green">Confirmed on Monad</span>
            <strong className="mt-1 block truncate text-sm text-jacarta-700 dark:text-white">{artifactName}</strong>
          </span>
          <span className="ml-auto text-lg text-green" aria-hidden="true">✓</span>
        </div>
      ) : (
        <p className="mt-5 text-center font-mono text-[10px] uppercase tracking-[.14em] text-jacarta-400">Waiting for validator confirmation</p>
      )}
    </div>
  );
}
