"use client";

import { usePrivy, useWallets } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import { privyLoginMethods } from "@/components/providers/PrivyAuthProvider";

type PrivyLoginButtonProps = {
  className?: string;
};

function normalizePrivyError(error: unknown) {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Privy 登录没有完成，请重试。";
}

export default function PrivyLoginButton({ className }: PrivyLoginButtonProps) {
  const router = useRouter();
  const { ready, authenticated, login, logout: privyLogout } = usePrivy();
  const { wallets, ready: walletsReady } = useWallets();
  const { user, status, loginWithWallet, clearError, logout } = useAuth();
  const [privyError, setPrivyError] = useState<string | null>(null);
  const [isLinkingFanora, setIsLinkingFanora] = useState(false);
  const loginAttemptRef = useRef<string | null>(null);

  const connectFanoraSession = useCallback(async () => {
    if (!ready || !authenticated || !walletsReady || user || isLinkingFanora) return;
    const wallet = wallets.find((candidate) => candidate.type === "ethereum" && candidate.address);
    if (!wallet) {
      setPrivyError(
        "Privy 已登录，但还没有可用于 Fanora 的 EVM 钱包。请在 Privy Dashboard 开启 Embedded Wallet，或使用钱包方式登录。",
      );
      return;
    }

    const attemptKey = `${wallet.address}:${wallets.length}`;
    if (loginAttemptRef.current === attemptKey) return;
    loginAttemptRef.current = attemptKey;

    setPrivyError(null);
    setIsLinkingFanora(true);
    try {
      await loginWithWallet(wallet.address, (message) => wallet.sign(message));
      router.replace("/collection");
    } catch (error) {
      loginAttemptRef.current = null;
      setPrivyError(normalizePrivyError(error));
    } finally {
      setIsLinkingFanora(false);
    }
  }, [
    authenticated,
    isLinkingFanora,
    loginWithWallet,
    ready,
    router,
    user,
    wallets,
    walletsReady,
  ]);

  useEffect(() => {
    void connectFanoraSession();
  }, [connectFanoraSession]);

  const handleLogin = () => {
    clearError();
    setPrivyError(null);
    if (!ready) return;
    if (authenticated) {
      void connectFanoraSession();
      return;
    }
    login({ loginMethods: [...privyLoginMethods] });
  };

  const handleSwitchMethod = async () => {
    clearError();
    setPrivyError(null);
    loginAttemptRef.current = null;
    if (authenticated) {
      await privyLogout();
    }
    await logout();
  };

  const isBusy = !ready || isLinkingFanora || status === "signing";

  return (
    <div>
      <div className="space-y-3">
        <button
          type="button"
          onClick={handleLogin}
          disabled={isBusy}
          className={
            className ||
            "web3-action-button flex w-full items-center justify-center rounded-2xl px-6 py-4 text-center font-semibold text-white transition-opacity disabled:cursor-not-allowed disabled:opacity-60"
          }
        >
          {!ready
            ? "正在初始化 Privy..."
            : isLinkingFanora || status === "signing"
              ? "正在确认 Fanora 身份..."
              : authenticated
                ? "继续进入 Fanora"
                : "使用 Privy 快速登录"}
        </button>
        <button
          type="button"
          onClick={() => void handleSwitchMethod()}
          disabled={!ready || isBusy}
          className="w-full rounded-2xl border border-white/10 bg-white/5 px-6 py-3 text-sm font-medium text-white/80 transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
        >
          切换其他登录方式
        </button>
      </div>
      {privyError && (
        <p className="mt-3 rounded-xl border border-red/20 bg-red/5 px-4 py-3 text-sm leading-6 text-red">
          {privyError}
        </p>
      )}
    </div>
  );
}
