"use client";

import Link from "next/link";
import React, { useEffect, useRef, useState } from "react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import UserAvatar from "@/components/profile/UserAvatar";
import { useAuth } from "@/components/providers/AuthProvider";
import type { FanoraUser } from "@/lib/api/types";

function shortAddress(address: string) {
  return `${address.slice(0, 8)}…${address.slice(-6)}`;
}

type ProfileMenuPanelProps = {
  user: FanoraUser;
  onClose: () => void;
  onLogout: () => void;
};

export function ProfileMenuPanel({ user, onClose, onLogout }: ProfileMenuPanelProps) {
  const [copied, setCopied] = useState(false);

  const copyAddress = async () => {
    await navigator.clipboard.writeText(user.primary_wallet.address);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1_500);
  };

  return (
    <div
      role="menu"
      className="absolute right-0 top-[calc(100%+12px)] z-50 w-[18rem] animate-[fadeIn_.18s_ease-out] overflow-hidden rounded-2xl border border-white/10 bg-[#121638] p-3 text-white shadow-[0_24px_70px_rgba(9,11,35,.45)]"
    >
      <div className="rounded-xl bg-white/[.055] p-4">
        <div className="flex items-center gap-3">
          <UserAvatar
            avatarUrl={user.avatar_url}
            seed={user.id}
            displayName={user.display_name}
            className="h-11 w-11 rounded-full ring-2 ring-white/10"
          />
          <div className="min-w-0 flex-1">
            <p className="truncate font-display text-sm font-semibold">
              {user.display_name || "Fanora 用户"}
            </p>
            <button
              type="button"
              onClick={() => void copyAddress()}
              title={user.primary_wallet.address}
              className="mt-1 flex max-w-full items-center gap-1.5 font-mono text-xs text-white/60 transition-colors hover:text-white"
            >
              <span className="truncate">{shortAddress(user.primary_wallet.address)}</span>
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 shrink-0 fill-current" aria-hidden="true">
                <path d="M8 7V3a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1h-4v4a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h4Zm2 0h5a1 1 0 0 1 1 1v5h3V4h-9v3Zm4 2H5v9h9V9Z" />
              </svg>
              {copied && <span className="font-sans text-[10px] text-green">已复制</span>}
            </button>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-3">
            <p className="text-[11px] text-white/50">Fan Token</p>
            <FanTokenAmount
              amount={user.fan_token_balance}
              className="mt-1 font-display text-lg font-semibold text-green"
            />
          </div>
          <div className="rounded-xl border border-white/10 bg-black/10 px-3 py-3">
            <p className="text-[11px] text-white/50">粉丝等级</p>
            <p className="mt-1 truncate font-display text-sm font-semibold text-accent-lighter">{user.level}</p>
          </div>
        </div>
        {!user.is_official_member && (
          <Link
            href="/membership/join"
            onClick={onClose}
            className="mt-3 flex items-center justify-center rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-dark"
          >
            缴纳 1 MON 正式加入
          </Link>
        )}
      </div>

      <div className="mt-2 space-y-1">
        <Link
          href="/community"
          role="menuitem"
          onClick={onClose}
          className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-colors hover:bg-white/[.07]"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current text-white/70" aria-hidden="true">
            <path d="M4 3h16a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-5l-3 3-3-3H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm2 5v2h12V8H6Zm0 4v2h8v-2H6Z" />
          </svg>
          官方社区
        </Link>
        <Link
          href="/profile"
          role="menuitem"
          onClick={onClose}
          className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-colors hover:bg-white/[.07]"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current text-white/70" aria-hidden="true">
            <path d="M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm-9 9a9 9 0 0 1 18 0H3Z" />
          </svg>
          My Profile
        </Link>
        <button
          type="button"
          role="menuitem"
          onClick={onLogout}
          className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm font-semibold text-white/70 transition-colors hover:bg-red/10 hover:text-red"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden="true">
            <path d="M5 3h8a2 2 0 0 1 2 2v3h-2V5H5v14h8v-3h2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm11.586 5.586L18 7.172 22.828 12 18 16.828l-1.414-1.414L19 13h-8v-2h8l-2.414-2.414Z" />
          </svg>
          退出登录
        </button>
      </div>
    </div>
  );
}

export default function Profile() {
  const { user, status, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };

    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  if (!user) {
    return (
      <Link
        href="/login"
        aria-label={status === "initializing" ? "登录服务准备中" : "登录后查看个人资料"}
        className="group ml-2 flex h-10 w-10 items-center justify-center rounded-full border border-jacarta-100 bg-white transition-colors hover:border-transparent hover:bg-accent dark:border-transparent dark:bg-white/[.15] dark:hover:bg-accent"
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-jacarta-700 group-hover:fill-white dark:fill-white" aria-hidden="true">
          <path d="M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm-9 9a9 9 0 0 1 18 0H3Z" />
        </svg>
      </Link>
    );
  }

  const handleLogout = async () => {
    setOpen(false);
    await logout();
  };

  return (
    <div ref={containerRef} className="relative ml-2">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-label="打开用户资料菜单"
        aria-haspopup="menu"
        aria-expanded={open}
        className="group flex h-10 w-10 items-center justify-center overflow-hidden rounded-full bg-transparent p-0 transition-transform hover:scale-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white/60"
      >
        <UserAvatar
          avatarUrl={user.avatar_url}
          seed={user.id}
          displayName={user.display_name}
          className="h-10 w-10 rounded-full"
        />
      </button>
      {open && (
        <ProfileMenuPanel user={user} onClose={() => setOpen(false)} onLogout={() => void handleLogout()} />
      )}
    </div>
  );
}
