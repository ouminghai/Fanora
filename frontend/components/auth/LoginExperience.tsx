"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import WalletButton from "@/components/web3/WalletButton";
import { useAuth } from "@/components/providers/AuthProvider";
import styles from "./LoginExperience.module.css";

const steps = [
  ["01", "选择熟悉的方式", "使用邮箱或社交账号，不需要安装钱包。"],
  ["02", "自动获得钱包身份", "Web3Auth 安全创建或恢复 Monad 兼容钱包。"],
  ["03", "进入 Fanora", "一次确认后完成注册或登录，开始积累粉丝身份。"],
];

export default function LoginExperience() {
  const router = useRouter();
  const { user, status, error, clearError } = useAuth();

  useEffect(() => {
    if (user && status === "authenticated") {
      const timer = window.setTimeout(() => router.replace("/profile"), 450);
      return () => window.clearTimeout(timer);
    }
  }, [router, status, user]);

  return (
    <main className={`${styles.stage} flex min-h-screen items-center bg-[#F8F7FF] px-6 pb-16 pt-32 dark:bg-jacarta-900`}>
      <div className="mx-auto grid w-full max-w-6xl items-center gap-12 lg:grid-cols-[1.05fr_.95fr]">
        <section className={styles.card}>
          <span className="inline-flex rounded-full border border-accent/20 bg-accent/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] text-accent">
            One identity · one wallet
          </span>
          <h1 className="mt-6 max-w-2xl font-display text-5xl font-semibold leading-[1.05] text-jacarta-700 dark:text-white md:text-7xl">
           Fanora — Every Interaction Builds Your Identity.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-jacarta-500 dark:text-jacarta-200">
            Fanora 使用 Web3Auth 把邮箱与社交登录转换成安全的嵌入式钱包。你无需理解助记词、Gas 或切链，也能拥有可验证的粉丝身份。
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {steps.map(([number, title, text], index) => (
              <div
                key={number}
                className="rounded-2xl border border-white/70 bg-white/70 p-5 shadow-sm backdrop-blur dark:border-white/10 dark:bg-white/[.05]"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <span className="font-display text-sm text-accent">{number}</span>
                <h2 className="mt-3 font-display text-base font-semibold text-jacarta-700 dark:text-white">{title}</h2>
                <p className="mt-2 text-sm leading-6 text-jacarta-500 dark:text-jacarta-300">{text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className={`${styles.card} relative mx-auto w-full max-w-md rounded-[2rem] border border-white/60 bg-white/85 p-8 shadow-[0_30px_90px_rgba(62,38,140,.22)] backdrop-blur-xl dark:border-white/10 dark:bg-jacarta-800/90 md:p-10`}>
          <div className="relative mx-auto mb-8 flex h-28 w-28 items-center justify-center">
            <div className={`${styles.orbit} absolute inset-0 rounded-full border border-dashed border-accent/45`} />
            <div className={`${styles.pulse} flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-accent to-[#46C7FF] text-3xl text-white shadow-accent-volume`}>
              ✦
            </div>
            <span className="absolute -right-1 top-2 h-4 w-4 rounded-full bg-green shadow-[0_0_18px_rgba(16,185,129,.8)]" />
          </div>
          <div className="text-center">
            <h2 className="font-display text-2xl font-semibold text-jacarta-700 dark:text-white">开始建立粉丝身份</h2>
            <p className="mt-3 text-sm leading-6 text-jacarta-500 dark:text-jacarta-300">首次登录会自动注册 Fanora 账户并绑定唯一主钱包。</p>
          </div>
          <div className="mt-8">
            <WalletButton variant="login" />
          </div>
          {error && (
            <button
              type="button"
              onClick={clearError}
              className="mt-2 w-full rounded-xl border border-red/20 bg-red/5 px-4 py-3 text-left text-sm text-red transition-colors hover:bg-red/10"
            >
              {error}
            </button>
          )}
          <div className="mt-6 flex items-center justify-center gap-5 text-xs text-jacarta-400">
            <span>✓ 不保存私钥</span>
            <span>✓ 钱包强绑定</span>
            <span>✓ 随时退出</span>
          </div>
        </section>
      </div>
    </main>
  );
}
