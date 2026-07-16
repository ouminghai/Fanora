"use client";

import { ConnectButton } from "@rainbow-me/rainbowkit";
import type { ReactNode } from "react";

type WalletButtonProps = {
  children?: ReactNode;
  variant?: "custom" | "login";
};

export default function WalletButton({
  children,
  variant = "custom",
}: WalletButtonProps) {
  return (
    <ConnectButton.Custom>
      {({
        account,
        chain,
        mounted,
        openAccountModal,
        openChainModal,
        openConnectModal,
      }) => {
        const ready = mounted;
        const connected = ready && account && chain;
        const action = !connected
          ? openConnectModal
          : chain.unsupported
            ? openChainModal
            : openAccountModal;

        const label = !connected
          ? "Connect Wallet"
          : chain.unsupported
            ? "Switch Network"
            : account.displayName;

        if (variant === "login") {
          return (
            <button
              type="button"
              onClick={action}
              disabled={!ready}
              className="mb-4 flex w-full items-center justify-center rounded-full border-2 border-transparent bg-accent py-4 px-8 text-center font-semibold text-white transition-all hover:bg-accent-dark disabled:cursor-wait disabled:opacity-60"
            >
              <svg
                viewBox="0 0 24 24"
                className="mr-2.5 h-6 w-6 fill-current"
                aria-hidden="true"
              >
                <path d="M22 6h-7a6 6 0 1 0 0 12h7v2a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h18a1 1 0 0 1 1 1v2zm-7 2h8v8h-8a4 4 0 1 1 0-8zm0 3v2h3v-2h-3z" />
              </svg>
              <span>{ready ? label : "Loading wallets..."}</span>
            </button>
          );
        }

        return (
          <div
            role="button"
            tabIndex={ready ? 0 : -1}
            aria-label={label}
            aria-disabled={!ready}
            onClick={ready ? action : undefined}
            onKeyDown={(event) => {
              if (ready && (event.key === "Enter" || event.key === " ")) {
                event.preventDefault();
                action();
              }
            }}
          >
            {children}
          </div>
        );
      }}
    </ConnectButton.Custom>
  );
}

