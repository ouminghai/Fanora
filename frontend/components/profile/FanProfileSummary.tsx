"use client";

import type { PublicFanProfileAnalysis } from "@/lib/api/types";

const fanTypeLabels: Record<string, string> = {
  emerging_fan: "成长型粉丝",
  loyal_fan: "忠诚粉丝",
  advocate: "传播倡导者",
  active_fan: "活跃粉丝",
  early_supporter: "早期支持者",
  high_value_contributor: "高价值贡献者",
};

const scoreLabels: Array<[keyof PublicFanProfileAnalysis["scores"], string]> = [
  ["activity", "活跃"],
  ["loyalty", "忠诚"],
  ["influence", "影响"],
  ["contribution", "贡献"],
];

export default function FanProfileSummary({
  profile,
  ownerLabel = "个人画像",
}: {
  profile: PublicFanProfileAnalysis;
  ownerLabel?: string;
}) {
  return (
    <section className="relative overflow-hidden rounded-[2rem] border border-accent/15 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#111538] md:p-8">
      <span className="pointer-events-none absolute -right-24 -top-24 h-52 w-52 rounded-full bg-accent/10 blur-3xl" />
      <div className="relative">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[.2em] text-accent">Proof of Fandom</p>
            <h2 className="mt-2 font-display text-2xl font-semibold text-jacarta-700 dark:text-white">{ownerLabel}</h2>
          </div>
          <span className="rounded-full border border-accent/20 bg-accent/10 px-4 py-2 text-xs font-semibold text-accent dark:text-accent-lighter">
            {fanTypeLabels[profile.fan_type] || profile.fan_type} · {profile.analysis_source === "llm" ? "AI 增强" : "规则画像"}
          </span>
        </div>

        <p className="mt-5 max-w-3xl text-sm leading-7 text-jacarta-500 dark:text-jacarta-300">{profile.summary}</p>

        <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-5">
          <div className="rounded-2xl bg-accent px-4 py-4 text-center text-white shadow-accent-volume md:row-span-1">
            <p className="text-xs text-white/65">综合</p>
            <p className="mt-1 font-display text-3xl font-semibold">{profile.scores.total}</p>
          </div>
          {scoreLabels.map(([key, label]) => (
            <div key={key} className="rounded-2xl bg-jacarta-50 px-4 py-4 text-center dark:bg-white/[.045]">
              <p className="text-xs text-jacarta-400">{label}</p>
              <p className="mt-1 font-display text-2xl font-semibold text-jacarta-700 dark:text-white">{profile.scores[key]}</p>
            </div>
          ))}
        </div>

        {profile.labels.length ? (
          <div className="mt-5 flex flex-wrap gap-2">
            {profile.labels.slice(0, 8).map((label) => <span key={label} className="rounded-full bg-jacarta-50 px-3 py-1.5 text-xs font-medium text-jacarta-500 dark:bg-white/[.05] dark:text-white/55">{label}</span>)}
          </div>
        ) : null}
      </div>
    </section>
  );
}
