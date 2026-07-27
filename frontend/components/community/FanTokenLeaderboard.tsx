"use client";

import axios from "axios";
import Link from "next/link";
import { JSX, useEffect, useState } from "react";
import { Medal, Trophy } from "lucide-react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import UserAvatar from "@/components/profile/UserAvatar";
import { api } from "@/lib/api/client";
import type { FanTokenLeaderboardUser } from "@/lib/api/types";

function message(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail || "排行榜暂时没有载入。";
  return error instanceof Error ? error.message : "排行榜暂时没有载入。";
}

export default function FanTokenLeaderboard() {
  const [leaders, setLeaders] = useState<FanTokenLeaderboardUser[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get<FanTokenLeaderboardUser[]>("/fan-tokens/leaderboard?limit=10")
      .then((response) => {
        if (!cancelled) setLeaders(response.data);
      })
      .catch((error) => {
        if (!cancelled) setNotice(message(error));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);
  
  const topThree = leaders.slice(0, 3);
  const rest = leaders.slice(3);

  function reutrn(arg0: JSX.Element) {
    throw new Error("Function not implemented.");
  }

  return (
    <main className="community-page-enter web3-page-shell min-h-screen pb-24 pt-28 md:pt-32">
      <div className="w-full px-5 lg:px-6">
        {notice ? <div className="community-notice-enter mb-6 rounded-2xl border border-red/20 bg-red/10 px-5 py-4 text-sm font-semibold text-red">{notice}</div> : null}

        <section className="community-section-enter overflow-hidden rounded-[2rem] bg-[#101436] p-6 text-white shadow-[0_24px_60px_rgba(13,16,45,.2)] md:p-9">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[.2em] text-accent-light">Fan leaderboard</p>
              <h1 className="mt-3 font-display text-2xl font-semibold md:text-4xl">Fan Token 排行榜</h1>
              <p className="mt-2 text-sm text-white/55">按当前 FAN 余额展示前 10 位公开用户。</p>
            </div>
            <Link href="/community/tasks" className="group inline-flex items-center gap-2 rounded-full border border-white/15 px-4 py-2 text-xs font-semibold text-white transition-colors hover:border-accent hover:bg-accent">
              返回任务 <span className="transition-transform group-hover:translate-x-1">→</span>
            </Link>
          </div>

          {loading ? (
            <div className="flex min-h-[360px] items-center justify-center">
              <span className="h-10 w-10 animate-spin rounded-full border-4 border-accent/20 border-t-accent" />
            </div>
          ) : leaders.length ? (
            <>
              <div className="mt-8 grid gap-5 lg:grid-cols-3">
                {topThree.map((leader) => (
                  <Link
                    key={leader.user_id}
                    href={`/users/${leader.user_id}`}
                    className="community-task-card group relative flex min-h-72 flex-col justify-between overflow-hidden rounded-2.5xl border border-white/10 bg-[#171B49] p-6 transition-all hover:-translate-y-0.5 hover:border-accent/45"
                  >
                    <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_80%_12%,rgba(131,88,255,.45),transparent_34%),radial-gradient(circle_at_10%_95%,rgba(69,191,239,.2),transparent_32%)]" />
                    <div className="relative flex items-start justify-between gap-4">
                      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-accent text-lg font-bold text-white">#{leader.rank}</span>
                      <Trophy className="h-8 w-8 text-accent-light" aria-hidden="true" />
                    </div>
                    <div className="relative mt-10">
                      <UserAvatar avatarUrl={leader.avatar_url} seed={leader.user_id} displayName={leader.display_name} className="h-16 w-16 rounded-full border-2 border-white/20" />
                      <h2 className="mt-4 truncate font-display text-xl font-semibold">{leader.display_name}</h2>
                      <p className="mt-1 truncate text-xs text-white/45">{leader.username ? `@${leader.username}` : leader.level}</p>
                      <div className="mt-5 flex items-end justify-between gap-4">
                        <FanTokenAmount amount={leader.fan_token_balance} showSymbol className="font-display text-2xl font-semibold text-accent-light" />
                        <span className="rounded-full border border-white/15 px-3 py-1 text-xs text-white/65">{leader.level}</span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>

              <div className="mt-6 overflow-hidden rounded-[1.25rem] border border-white/10 bg-[#171B49]">
                {rest.map((leader) => (
                  <Link key={leader.user_id} href={`/users/${leader.user_id}`} className="community-list-item grid min-h-24 grid-cols-[3rem_minmax(0,1fr)_auto] items-center gap-4 border-b border-white/10 px-4 py-4 last:border-b-0 hover:bg-white/[.04] md:grid-cols-[4rem_minmax(0,1fr)_auto] md:px-6">
                    <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-sm font-bold text-white/75">{leader.rank}</span>
                    <div className="flex min-w-0 items-center gap-3">
                      <UserAvatar avatarUrl={leader.avatar_url} seed={leader.user_id} displayName={leader.display_name} className="h-11 w-11 rounded-full" />
                      <div className="min-w-0">
                        <p className="truncate font-semibold">{leader.display_name}</p>
                        <p className="mt-1 truncate text-xs text-white/45">{leader.username ? `@${leader.username}` : leader.level}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <FanTokenAmount amount={leader.fan_token_balance} showSymbol className="justify-end text-sm font-semibold text-accent-light md:text-base" />
                      <p className="mt-1 hidden text-xs text-white/35 sm:block">累计 {leader.fan_token_lifetime_earned} FAN</p>
                    </div>
                  </Link>
                ))}
              </div>
            </>
          ) : (
            <div className="mt-8 flex min-h-[320px] flex-col items-center justify-center rounded-[1.25rem] border border-white/10 bg-[#171B49] text-center">
              <Medal className="h-10 w-10 text-white/35" aria-hidden="true" />
              <p className="mt-4 text-sm text-white/55">暂时还没有公开用户进入排行榜。</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
