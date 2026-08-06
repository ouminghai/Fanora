"use client";

import { useEffect } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import PrivyLoginButton from "@/components/auth/PrivyLoginButton";
import RainbowWalletLoginButton from "@/components/web3/RainbowWalletLoginButton";
import { useAuth } from "@/components/providers/AuthProvider";
import { isPrivyConfigured } from "@/components/providers/PrivyAuthProvider";
import styles from "./LoginExperience.module.css";

const steps = [
  ["01", "快速登录", "使用邮箱、Google 或钱包进入 Fanora。"],
  ["02", "生成身份钱包", "Privy 自动连接或创建可签名的钱包身份。"],
  ["03", "进入 Fanora", "完成一次无 Gas 确认后开始积累粉丝身份。"],
];

export default function LoginExperience() {
  const router = useRouter();
  const { user, status, error, clearError } = useAuth();

  useEffect(() => {
    if (user && status === "authenticated") {
      router.replace("/collection");
    }
  }, [router, status, user]);

  return (
    <main className={`${styles.stage} flex min-h-screen items-center px-6 pb-16 pt-32`}>
      <Image
        fill
        priority
        src="/img/fanora/login/login-bg.jpg"
        alt=""
        aria-hidden="true"
        sizes="100vw"
        className={`${styles.backdrop} pointer-events-none object-cover object-center`}
      />
      <div className={styles.backdropVeil} aria-hidden="true" />
      <div className="mx-auto grid w-full max-w-6xl items-center gap-12 lg:grid-cols-[1.05fr_.95fr]">
        <section className={styles.card}>
          <span className={styles.protocolLabel}>
            One identity · one wallet
          </span>
          <h1 className={`${styles.heroTitle} mt-6 max-w-2xl font-display text-5xl font-semibold leading-[1.05] md:text-7xl`}>
            <span className={`${styles.typewriterLine} ${styles.typewriterBrand}`}>Fanora</span>
          </h1>
          <h1 className={`${styles.heroTitle} mt-6 max-w-2xl font-display text-5xl font-semibold leading-[1.05] md:text-7xl`}>
            <span className={`${styles.typewriterLine} ${styles.typewriterFandom}`}>Your fandom.</span>
            <br />
            <span className={`${styles.typewriterLine} ${styles.typewriterForever}`}>On-chain. Forever.</span>
          </h1>
          <p className={`${styles.heroCopy} mt-6 max-w-xl text-lg leading-8`}>
            Fanora 接入 Privy，让新用户可以用邮箱、Google 或钱包快速进入。完成一次无 Gas 的身份确认后，即可获得可验证的粉丝身份。
          </p>
          <div className={`${styles.stepFlow} mt-10 grid gap-4 sm:grid-cols-3`}>
            {steps.map(([number, title, text]) => (
              <div
                key={number}
                className={`${styles.stepCard} p-5`}
              >
                <span className={`${styles.stepNumber} font-display text-sm`}>{number}</span>
                <h2 className="mt-3 font-display text-base font-semibold text-white">{title}</h2>
                <p className={`${styles.stepCopy} mt-2 text-sm leading-6`}>{text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className={`${styles.card} ${styles.loginCard} relative mx-auto w-full max-w-md`}>
          <span className={`${styles.corner} ${styles.cornerTopLeft}`} aria-hidden="true" />
          <span className={`${styles.corner} ${styles.cornerTopRight}`} aria-hidden="true" />
          <span className={`${styles.corner} ${styles.cornerBottomLeft}`} aria-hidden="true" />
          <span className={`${styles.corner} ${styles.cornerBottomRight}`} aria-hidden="true" />
          <span className={styles.photon} aria-hidden="true"><i /></span>
          <span className={`${styles.photon} ${styles.photonSecondary}`} aria-hidden="true"><i /></span>
          <div className={styles.loginSystemBar}>
            <span><i aria-hidden="true" /> PRIVY AUTH NODE</span>
            <span>FANORA // READY</span>
          </div>
          <div className={styles.loginCardBody}>
          <div className="relative mx-auto mb-8 flex h-28 w-28 items-center justify-center">
            <div className={`${styles.orbit} absolute inset-0 rounded-full border border-dashed border-accent/45`} />
            <Image
              src="/img/avatars/login-icon.jpg"
              alt="Fanora 粉丝身份"
              width={80}
              height={80}
              priority
              className={`${styles.pulse} h-20 w-20 rounded-lg object-cover shadow-accent-volume`}
            />
            <span className="absolute -right-1 top-2 h-4 w-4 rounded-full bg-green shadow-[0_0_18px_rgba(16,185,129,.8)]" />
          </div>
          <div className="text-center">
            <h2 className="font-display text-2xl font-semibold text-white">欢迎加入 Fanora！</h2>
            <p className={`${styles.loginCopy} mt-3 text-sm leading-6`}>完成确认后，即可开启签到、粉丝任务和会员专属权益。</p>
          </div>
          <div className="mt-8">
            {isPrivyConfigured ? (
              <PrivyLoginButton />
            ) : (
              <RainbowWalletLoginButton variant="full" />
            )}
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
          <div className={`${styles.securityNotes} mt-6 flex items-center justify-center gap-5 text-xs`}>
            <span>✓ 不保存私钥</span>
            <span>✓ Privy 钱包身份</span>
            <span>✓ 随时退出</span>
          </div>
          </div>
        </section>
      </div>
    </main>
  );
}
