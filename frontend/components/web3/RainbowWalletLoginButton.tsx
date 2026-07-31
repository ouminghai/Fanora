"use client";

import {
  useChainModal,
  useConnectModal,
} from "@rainbow-me/rainbowkit";
import { useCallback, useEffect, useRef, useState } from "react";
import { createWalletClient, custom, type EIP1193Provider } from "viem";
import { useAccount } from "wagmi";
import { monadTestnet } from "wagmi/chains";
import { useAuth } from "@/components/providers/AuthProvider";
import { supportedChains } from "@/lib/web3/config";

type RainbowWalletLoginButtonProps = {
  variant?: "icon" | "full";
};

function providerErrorCode(error: unknown): number | undefined {
  if (!error || typeof error !== "object") return undefined;
  if ("code" in error && typeof error.code === "number") return error.code;
  if ("cause" in error) return providerErrorCode(error.cause);
  return undefined;
}

export default function RainbowWalletLoginButton({
  variant = "icon",
}: RainbowWalletLoginButtonProps) {
  const { user, status, loginWithWallet, clearError } = useAuth();
  const { address, chain, connector, isConnected } = useAccount();
  const { openConnectModal } = useConnectModal();
  const { openChainModal } = useChainModal();
  const [mounted, setMounted] = useState(false);
  const awaitingConnectionRef = useRef(false);
  const signingRef = useRef(false);
  const busy = status === "signing";

  useEffect(() => setMounted(true), []);

  const connected = Boolean(mounted && isConnected && address && chain);
  const chainSupported = Boolean(
    chain && supportedChains.some((supportedChain) => supportedChain.id === chain.id),
  );
  const label = !connected
    ? "直连钱包"
    : !chainSupported
      ? "切换网络"
      : busy
        ? "确认签名中"
        : "钱包签名登录";

  const signIn = useCallback(async (walletAddress: `0x${string}`) => {
    if (signingRef.current) return;
    if (!connector) throw new Error("钱包连接尚未准备好，请重新连接后再试。");
    signingRef.current = true;
    awaitingConnectionRef.current = false;
    try {
      const provider = await connector.getProvider() as EIP1193Provider;
      try {
        await provider.request({
          method: "wallet_switchEthereumChain",
          params: [{ chainId: `0x${monadTestnet.id.toString(16)}` }],
        });
      } catch (switchError) {
        if (providerErrorCode(switchError) !== 4902) throw switchError;
        await provider.request({
          method: "wallet_addEthereumChain",
          params: [{
            chainId: `0x${monadTestnet.id.toString(16)}`,
            chainName: monadTestnet.name,
            nativeCurrency: monadTestnet.nativeCurrency,
            rpcUrls: [
              process.env.NEXT_PUBLIC_MONAD_TESTNET_RPC_URL
                || monadTestnet.rpcUrls.default.http[0],
            ],
            blockExplorerUrls: monadTestnet.blockExplorers
              ? [monadTestnet.blockExplorers.default.url]
              : undefined,
          }],
        });
      }
      const walletClient = createWalletClient({
        account: walletAddress,
        chain: monadTestnet,
        transport: custom(provider),
      });
      await loginWithWallet(walletAddress, (message) => walletClient.signMessage({
        account: walletAddress,
        message,
      }));
    } finally {
      signingRef.current = false;
    }
  }, [connector, loginWithWallet]);

  useEffect(() => {
    if (
      !awaitingConnectionRef.current ||
      !connected ||
      !address ||
      signingRef.current
    ) return;
    if (!chainSupported) {
      openChainModal?.();
      return;
    }
    void signIn(address).catch(() => undefined);
  }, [address, chainSupported, connected, openChainModal, signIn]);

  if (user) return null;

  const handleClick = () => {
    clearError();
    if (!connected) {
      awaitingConnectionRef.current = true;
      openConnectModal?.();
      return;
    }
    if (!chainSupported) {
      awaitingConnectionRef.current = true;
      openChainModal?.();
      return;
    }
    if (address) void signIn(address).catch(() => undefined);
  };

  if (variant === "full") {
    return (
      <button
        type="button"
        onClick={handleClick}
        disabled={!mounted || busy}
        className="flex w-full items-center justify-center gap-2 rounded-full bg-accent px-8 py-3 font-semibold text-white shadow-accent-volume transition-colors hover:bg-accent-dark disabled:cursor-wait disabled:opacity-65"
      >
        {busy ? (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
        ) : (
          <WalletIcon className="h-4 w-4" />
        )}
        {label}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={!mounted || busy}
      aria-label={label}
      title={connected && chainSupported ? `${label} · ${address}` : label}
      className="group ml-2 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-jacarta-100 bg-white transition-colors hover:border-transparent hover:bg-accent disabled:cursor-wait disabled:opacity-60 dark:border-transparent dark:bg-white/[.15] dark:hover:bg-accent"
    >
      {busy ? (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-jacarta-400 border-t-accent group-hover:border-white/40 group-hover:border-t-white" />
      ) : (
        <WalletIcon className="h-4 w-4 fill-jacarta-700 transition-colors group-hover:fill-white dark:fill-white" />
      )}
    </button>
  );
}

function WalletIcon({ className }: { className: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path d="M3 4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h17a2 2 0 0 0 2-2v-3h-6a4 4 0 1 1 0-8h6V6a2 2 0 0 0-2-2H3Zm13 6h7v4h-7a2 2 0 1 1 0-4Zm0 1.25a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Z" />
    </svg>
  );
}
