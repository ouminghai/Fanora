"use client";

import axios from "axios";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import type { OfficialMembershipStatus } from "@/lib/api/types";

type PaymentPhase = "idle" | "wallet" | "verifying" | "success";

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
      setPhase("verifying");
      const response = await api.post<OfficialMembershipStatus>("/membership/verify", {
        transaction_hash: hash,
      });
      setMembership(response.data);
      await refreshUser();
      setPhase("success");
    } catch (paymentError) {
      setError(paymentErrorMessage(paymentError));
      setPhase("idle");
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
  const feeLabel = membership?.fee_mon ? `${membership.fee_mon} MON` : "当前会费";

  return (
    <main className="relative isolate min-h-screen overflow-hidden bg-[#09051c] pb-24 pt-32 text-white">
      <Image
        fill
        priority
        src="/img/fanora/membership-join-bg.jpg"
        alt=""
        aria-hidden="true"
        sizes="100vw"
        className="pointer-events-none -z-30 object-cover object-center opacity-60"
      />
      <div className="pointer-events-none absolute inset-0 -z-20 bg-[radial-gradient(circle_at_50%_15%,rgba(131,88,255,.42),transparent_48%)]" />
      <div className="pointer-events-none absolute -left-32 top-48 -z-10 h-96 w-96 rounded-full bg-blue/15 blur-3xl" />
      <div className="pointer-events-none absolute -right-32 bottom-20 -z-10 h-96 w-96 rounded-full bg-pink/15 blur-3xl" />

      <div className="mx-auto max-w-3xl px-6">
        <section className="animate-[hero-fade-up_.65s_cubic-bezier(.22,1,.36,1)] overflow-hidden rounded-[2rem] border border-white/15 bg-white/[.07] shadow-[0_30px_100px_rgba(0,0,0,.35)] backdrop-blur-xl">
          <div className="border-b border-white/10 px-7 py-8 text-center md:px-12 md:py-10">
            <span className="inline-flex rounded-full border border-accent/35 bg-accent/15 px-4 py-1.5 text-xs font-bold uppercase tracking-[.18em] text-accent-lighter">
              Eason Fans Club Membership
            </span>
            <h1 className="mt-5 font-display text-3xl font-semibold md:text-5xl">
              {isActive ? "你已成为正式会员" : "Activate your on-chain identity and become part of Fanora."}
            </h1>
            <p className="mx-auto mt-4 max-w-xl leading-7 text-white/65">
              请在 Web3Auth Modal 中连接 MetaMask，再由 MetaMask 弹窗确认 {feeLabel}
              入会交易。Fanora 不会读取、保存或上传你的钱包私钥。
            </p>
          </div>

          <div className="px-7 py-8 md:px-12 md:py-10">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-black/15 p-4">
                <p className="text-xs text-white/45">当前身份</p>
                <p className="mt-2 font-display font-semibold text-accent-lighter">
                  {isActive ? user.level : "待入会"}
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/15 p-4">
                <p className="text-xs text-white/45">入会费用</p>
                <p className="mt-2 font-display text-xl font-semibold">{feeLabel}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/15 p-4">
                <p className="text-xs text-white/45">网络</p>
                <p className="mt-2 font-display font-semibold">Monad Testnet</p>
              </div>
            </div>

            {!membership?.payment_contract_address && !isActive && (
              <div className="mt-6 rounded-2xl border border-orange/25 bg-orange/10 px-5 py-4 text-sm leading-6 text-orange">
                后端尚未配置入会付款合约。部署后设置 `MEMBERSHIP_PAYMENT_CONTRACT_ADDRESS`，系统不会把普通地址转账当作入会凭证。
              </div>
            )}

            {error && (
              <div className="mt-6 rounded-2xl border border-red/25 bg-red/10 px-5 py-4 text-sm leading-6 text-red">
                {error}
              </div>
            )}

            {transactionHash && (
              <a
                href={`https://testnet.monadexplorer.com/tx/${transactionHash}`}
                target="_blank"
                rel="noreferrer"
                className="mt-6 block truncate rounded-2xl border border-white/10 bg-black/15 px-5 py-4 font-mono text-xs text-accent-lighter transition-colors hover:border-accent/40"
              >
                交易：{transactionHash}
              </a>
            )}

            {isActive ? (
              <div className="mt-8 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green text-2xl shadow-lg shadow-green/20">
                  ✓
                </div>
                <p className="mt-4 text-white/70">签到和粉丝任务参与资格已经解锁。</p>
                <Link
                  href="/community"
                  className="mt-6 inline-flex rounded-full bg-accent px-8 py-3.5 font-semibold text-white shadow-accent-volume transition-all hover:-translate-y-0.5 hover:bg-accent-dark"
                >
                  前往链上社区
                </Link>
              </div>
            ) : (
              <button
                type="button"
                disabled={isPaying || !membership?.payment_contract_address || !membership.payment_id}
                onClick={() => void pay()}
                className="mt-8 flex w-full items-center justify-center rounded-full bg-accent px-8 py-4 text-lg font-semibold text-white shadow-accent-volume transition-all hover:-translate-y-0.5 hover:bg-accent-dark disabled:cursor-not-allowed disabled:opacity-45"
              >
                {isPaying && (
                  <span className="mr-3 h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                )}
                {phase === "wallet"
                  ? `请在 MetaMask 中确认 ${feeLabel} 交易`
                  : phase === "verifying"
                    ? "正在等待 Monad 确认…"
                    : `使用 MetaMask 确认支付 ${feeLabel}`}
              </button>
            )}

            <div className="mt-8 grid gap-3 text-sm leading-6 text-white/55 sm:grid-cols-3">
              <p>✓ 交易由当前登录主钱包的 MetaMask 弹窗签名</p>
              <p>✓ 合约精确校验并托管当前会费，管理员可审计提现</p>
              <p>✓ Fanora 不接触用户私钥，paymentId 与钱包仅可入会一次</p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
