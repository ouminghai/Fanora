"use client";

import axios from "axios";
import NiceModal from "@ebay/nice-modal-react";
import { Activity, RadioTower, ShieldCheck, Zap } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import GlobalInfoModal from "@/components/modals/GlobalInfoModal";
import GlobalProcessModal, { hideGlobalProcessModal } from "@/components/modals/GlobalProcessModal";
import { api } from "@/lib/api/client";
import type { OfficialMembershipStatus } from "@/lib/api/types";
import { startRealisticConfetti } from "@/lib/ui/confetti";
import styles from "./OfficialMembershipCheckout.module.css";

type PaymentPhase = "idle" | "wallet" | "verifying" | "free" | "success";

const VERIFY_ATTEMPTS = 20;
const VERIFY_INTERVAL_MS = 3_000;
const FREE_SUCCESS_CELEBRATION_MS = 4_000;

function pendingPaymentKey(userId: string) {
  return `fanora.membership.pending.${userId}`;
}

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function isRetryableVerificationError(error: unknown) {
  if (!axios.isAxiosError(error)) return false;
  if (!error.response) return true;
  if ([404, 502, 503, 504].includes(error.response.status)) return true;
  if (error.response.status !== 409) return false;
  const detail = String(error.response.data?.detail || "").toLowerCase();
  return ["waiting for confirmation", "enough confirmations", "activated by another request"].some(
    (message) => detail.includes(message),
  );
}

function paymentErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || "入会交易暂时无法验证，请稍后重试。";
  }
  if (error instanceof Error) return error.message;
  return "入会交易没有完成，请重试。";
}

export default function OfficialMembershipCheckout() {
  const router = useRouter();
  const {
    user,
    status: authStatus,
    sendMembershipPayment,
    refreshUser,
  } = useAuth();
  const [membership, setMembership] = useState<OfficialMembershipStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [phase, setPhase] = useState<PaymentPhase>("idle");
  const [transactionHash, setTransactionHash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const celebratedMembershipRef = useRef(false);

  const verifyTransaction = useCallback(
    async (hash: string) => {
      if (!user) return;
      setError(null);
      setPhase("verifying");
      for (let attempt = 0; attempt < VERIFY_ATTEMPTS; attempt += 1) {
        try {
          const response = await api.post<OfficialMembershipStatus>("/membership/verify", {
            transaction_hash: hash,
          });
          setMembership(response.data);
          window.localStorage.removeItem(pendingPaymentKey(user.id));
          await refreshUser();
          setPhase("success");
          return;
        } catch (verificationError) {
          if (!isRetryableVerificationError(verificationError)) {
            window.localStorage.removeItem(pendingPaymentKey(user.id));
            setTransactionHash(null);
            setPhase("idle");
            throw verificationError;
          }
          if (attempt < VERIFY_ATTEMPTS - 1) await wait(VERIFY_INTERVAL_MS);
        }
      }
      setPhase("idle");
      throw new Error("交易已经提交，Monad 暂时还未确认。页面会保留交易记录，请稍后点击继续确认，无需再次支付。");
    },
    [refreshUser, user],
  );

  const loadMembership = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<OfficialMembershipStatus>("/membership/me");
      setMembership(response.data);
    } catch (requestError) {
      setError(paymentErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authStatus === "anonymous" || authStatus === "error") {
      router.replace("/login");
      return;
    }
    if (authStatus === "authenticated") void loadMembership();
  }, [authStatus, loadMembership, router]);

  useEffect(() => {
    if (!user || loading || !membership || membership.is_official_member || transactionHash) return;
    const pendingHash = window.localStorage.getItem(pendingPaymentKey(user.id));
    if (!pendingHash) return;
    setTransactionHash(pendingHash);
    void verifyTransaction(pendingHash).catch((verificationError) => {
      setError(paymentErrorMessage(verificationError));
    });
  }, [loading, membership, transactionHash, user, verifyTransaction]);

  useEffect(() => {
    const canCelebrate = phase === "idle" || phase === "success";
    if (loading || !canCelebrate || !membership?.is_official_member || celebratedMembershipRef.current) return;
    celebratedMembershipRef.current = true;
    let disposed = false;
    let stopConfetti: (() => void) | undefined;
    let redirectTimer: number | undefined;
    const shouldRedirect = phase === "success" && membership.fee_wei === "0";

    void startRealisticConfetti(FREE_SUCCESS_CELEBRATION_MS).then((cleanup) => {
      if (disposed) {
        cleanup();
        return;
      }
      stopConfetti = cleanup;
      if (shouldRedirect) {
        redirectTimer = window.setTimeout(() => {
          router.push("/collection?welcome=member-card");
        }, FREE_SUCCESS_CELEBRATION_MS);
      }
    });

    return () => {
      disposed = true;
      if (redirectTimer !== undefined) window.clearTimeout(redirectTimer);
      stopConfetti?.();
    };
  }, [loading, membership?.fee_wei, membership?.is_official_member, phase, router]);

  const pay = async () => {
    if (!membership?.payment_contract_address || !membership.payment_id || !user) return;
    setError(null);
    setPhase("wallet");
    try {
      const hash = await sendMembershipPayment({
        paymentContractAddress: membership.payment_contract_address,
        paymentId: membership.payment_id,
        feeWei: membership.fee_wei,
        chainId: membership.chain_id,
      });
      setTransactionHash(hash);
      window.localStorage.setItem(pendingPaymentKey(user.id), hash);
      await verifyTransaction(hash);
    } catch (paymentError) {
      setError(paymentErrorMessage(paymentError));
      setPhase("idle");
    }
  };

  const activateFree = async () => {
    if (!user) return;
    setError(null);
    setPhase("free");
    void NiceModal.show(GlobalProcessModal, {
      title: "正在激活正式会员",
      message: "正在确认免费入会资格并等待 Monad 完成会员关系确认。",
      eyebrow: "MEMBERSHIP ACTIVATION",
      gifUrl: null,
      phase: "processing",
      progressKind: "identity",
      artifactName: `${user.level || "Fanora"} Membership`,
    });
    try {
      const response = await api.post<OfficialMembershipStatus>("/membership/activate-free");
      setMembership(response.data);
      window.localStorage.removeItem(pendingPaymentKey(user.id));
      window.sessionStorage.setItem("fanora.membership.card.onboarding", user.id);
      await hideGlobalProcessModal();
      setPhase("success");
      void refreshUser().catch(() => undefined);
    } catch (freeError) {
      await hideGlobalProcessModal();
      setError(paymentErrorMessage(freeError));
      setPhase("idle");
      void NiceModal.show(GlobalInfoModal, {
        title: "免费入会没有完成",
        message: paymentErrorMessage(freeError),
        tone: "error",
        eyebrow: "MEMBERSHIP ERROR",
        confirmLabel: "返回重试",
      });
    }
  };

  if (!user || loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#09051c] pt-24 text-white">
        <span className="mr-3 h-6 w-6 animate-spin rounded-full border-2 border-white/25 border-t-accent" />
        正在读取正式会员状态…
      </main>
    );
  }

  const isActive = membership?.is_official_member || phase === "success";
  const isPaying = phase === "wallet" || phase === "verifying";
  const isFree = membership?.fee_wei === "0";
  const feeLabel = isFree ? "限时免费" : membership?.fee_mon ? `${membership.fee_mon} MON` : "当前会费";
  const resultFeeLabel = isActive
    ? isFree
      ? "免费激活完成"
      : `${feeLabel} 已确认`
    : feeLabel;
  const walletLabel = "RainbowKit 直连钱包";

  return (
    <main className={`${styles.stage} relative isolate min-h-screen overflow-hidden pb-24 pt-32 text-white`}>
      <Image
        fill
        priority
        src="/img/fanora/membership-join-bg.jpg"
        alt=""
        aria-hidden="true"
        sizes="100vw"
        className={`${styles.backdrop} pointer-events-none -z-30 object-cover object-center`}
      />
      <div className={styles.backdropVeil} aria-hidden="true" />
      <div className={styles.cyberGrid} aria-hidden="true" />
      <div className={styles.scanlines} aria-hidden="true" />

      <div className="relative mx-auto max-w-3xl px-5 sm:px-6">
        <section className={styles.panel}>
          <span className={`${styles.corner} ${styles.cornerTopLeft}`} aria-hidden="true" />
          <span className={`${styles.corner} ${styles.cornerTopRight}`} aria-hidden="true" />
          <span className={`${styles.corner} ${styles.cornerBottomLeft}`} aria-hidden="true" />
          <span className={`${styles.corner} ${styles.cornerBottomRight}`} aria-hidden="true" />

          <div className={styles.systemBar}>
            <span className={styles.systemIdentity}>
              <i className={styles.statusDot} aria-hidden="true" />
              FANORA IDENTITY PROTOCOL
            </span>
            <span>MONAD // CHAIN 10143</span>
          </div>

          <div className={styles.heroBlock}>
            <p className={styles.eyebrow}>EASON FANS CLUB · MEMBERSHIP ACCESS</p>
            <h1 className={styles.title}>
              {isActive ? "你的 Fanora Identity 已正式激活" : "Your fandom. On-chain. Forever."}
            </h1>
            <p className={styles.subtitle}>
              {isActive
                ? "会员身份已完成 Monad 链上确认，签到、粉丝任务与会员专属权益现已开放。"
                : isFree
                  ? "Activate your on-chain identity and become part of Fanora."
                  : `使用${walletLabel}确认 ${feeLabel} 入会交易。交易由你的钱包直接签名，Fanora 不会读取、保存或上传你的钱包私钥。`}
            </p>
          </div>

          <div className={styles.contentBlock}>
            <div className={styles.metrics}>
              <div className={styles.metric}>
                <span className={styles.metricNode} aria-hidden="true">
                  <ShieldCheck className={styles.metricIcon} />
                </span>
                <div>
                  <p>{isActive ? "MEMBERSHIP STATUS" : "IDENTITY STATUS"}</p>
                  <strong>{isActive ? "正式会员 · 已激活" : "待入会"}</strong>
                </div>
              </div>
              <div className={styles.metric}>
                <span className={styles.metricNode} aria-hidden="true">
                  <Activity className={styles.metricIcon} />
                </span>
                <div>
                  <p>{isActive ? "ACTIVATION RESULT" : "MEMBERSHIP FEE"}</p>
                  <strong>{resultFeeLabel}</strong>
                </div>
              </div>
              <div className={styles.metric}>
                <span className={styles.metricNode} aria-hidden="true">
                  <RadioTower className={styles.metricIcon} />
                </span>
                <div>
                  <p>NETWORK</p>
                  <strong>Monad Testnet</strong>
                </div>
              </div>
            </div>

            {!isFree && !membership?.payment_contract_address && !isActive ? (
              <div className={`${styles.notice} ${styles.noticeWarning}`}>
                后端尚未配置入会付款合约。部署后设置 `MEMBERSHIP_PAYMENT_CONTRACT_ADDRESS`，系统不会把普通地址转账当作入会凭证。
              </div>
            ) : null}

            {error ? <div className={`${styles.notice} ${styles.noticeError}`}>{error}</div> : null}

            {transactionHash ? (
              <a
                href={`https://testnet.monadexplorer.com/tx/${transactionHash}`}
                target="_blank"
                rel="noreferrer"
                className={styles.transactionLink}
              >
                TX HASH // {transactionHash}
              </a>
            ) : null}

            {isActive ? (
              <div className={styles.successBlock}>
                <div className={styles.successMark}>✓</div>
                <p>链上会员关系已确认，签到、粉丝任务和会员专属权益均已解锁。</p>
                <Link href="/collection" className={styles.secondaryAction}>
                  <Zap className="h-4 w-4" aria-hidden="true" />
                  获取我的会员身份卡
                </Link>
              </div>
            ) : (
              <div className={styles.actionBlock}>
                <button
                  type="button"
                  disabled={
                    isPaying ||
                    phase === "free" ||
                    (isFree && !membership?.payment_contract_address) ||
                    (!isFree && (!membership?.payment_contract_address || !membership.payment_id))
                  }
                  onClick={() => {
                    const action = isFree ? activateFree() : transactionHash ? verifyTransaction(transactionHash) : pay();
                    void action.catch((verificationError) => {
                      setError(paymentErrorMessage(verificationError));
                    });
                  }}
                  className={styles.primaryAction}
                >
                  {isPaying ? (
                    <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  ) : phase !== "free" ? (
                    <Zap className="h-5 w-5" aria-hidden="true" />
                  ) : null}
                  {phase === "free"
                    ? "正在激活免费会员..."
                    : phase === "wallet"
                      ? `请在钱包中确认 ${feeLabel} 交易`
                      : phase === "verifying"
                        ? "正在等待 Monad 确认…"
                        : transactionHash
                          ? "继续确认已提交的交易"
                          : isFree
                            ? "限时免费入会"
                            : `使用钱包确认支付 ${feeLabel}`}
                </button>
                {transactionHash && phase === "idle" ? <p className={styles.pendingNote}>已保留这笔交易，无需再次支付。</p> : null}
              </div>
            )}

            <div className={styles.capabilities}>
              {isActive ? (
                <>
                  <p><span>01</span>Monad 已确认正式会员关系</p>
                  <p><span>02</span>签到、粉丝任务和会员权益已开放</p>
                  <p><span>03</span>入会记录与链上交易凭证可审计</p>
                </>
              ) : (
                <>
                  <p><span>01</span>{isFree ? "限时免费激活，无需支付 Gas 费用" : "支持 RainbowKit、MetaMask、WalletConnect 等直连钱包"}</p>
                  <p><span>02</span>{isFree ? "会员身份永久上链，可公开验证" : "合约精确校验并托管当前会费，管理员可审计提现"}</p>
                  <p><span>03</span>一个身份，仅属于一个钱包</p>
                </>
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
