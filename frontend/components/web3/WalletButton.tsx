"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "@/components/providers/AuthProvider";

type WalletButtonProps = {
  children?: ReactNode;
  variant?: "custom" | "login";
};

export default function WalletButton({
  children,
  variant = "custom",
}: WalletButtonProps) {
  const router = useRouter();
  const { user, status, login } = useAuth();
  const busy = ["initializing", "connecting", "signing"].includes(status);

  const loginAction = async () => {
    if (user) {
      router.push("/profile");
      return;
    }
    try {
      await login();
      router.push("/profile");
    } catch {
      // AuthProvider exposes the actionable error inside the login experience.
    }
  };

  if (variant === "login") {
    const label =
      status === "initializing"
        ? "正在准备安全登录…"
        : status === "connecting"
          ? "打开登录方式…"
          : status === "signing"
            ? "正在确认钱包身份…"
            : user
              ? "进入我的 Fanora"
              : "邮箱 / 社交账号快捷登录";
    return (
      <button
        type="button"
        onClick={loginAction}
        disabled={busy}
        className="group relative mb-4 flex w-full items-center justify-center overflow-hidden rounded-full border-2 border-transparent bg-accent py-4 px-8 text-center font-semibold text-white shadow-accent-volume transition-all duration-300 hover:-translate-y-0.5 hover:bg-accent-dark disabled:cursor-wait disabled:opacity-70"
      >
        <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
        {busy ? (
          <span className="mr-3 h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
        ) : (
          <svg viewBox="0 0 24 24" className="mr-2.5 h-6 w-6 fill-current">
            <path d="M12 1a7 7 0 0 0-7 7v2H4a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-1V8a7 7 0 0 0-7-7Zm-5 9V8a5 5 0 0 1 10 0v2H7Zm5 4a2 2 0 0 1 1 3.732V20h-2v-2.268A2 2 0 0 1 12 14Z" />
          </svg>
        )}
        <span className="relative">{label}</span>
      </button>
    );
  }

  if (user) return null;

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="前往登录页面"
      className="cursor-pointer"
      onClick={() => router.push("/login")}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          router.push("/login");
        }
      }}
    >
      {children}
    </div>
  );
}
