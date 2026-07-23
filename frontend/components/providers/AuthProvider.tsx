"use client";

import axios from "axios";
import { disconnect, getWalletClient } from "@wagmi/core";
import {
  useAccountModal,
  useChainModal,
  useConnectModal,
} from "@rainbow-me/rainbowkit";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { encodeFunctionData, type Abi } from "viem";
import { useAccount } from "wagmi";
import { api, SESSION_TOKEN_KEY } from "@/lib/api/client";
import type { AuthSession, FanoraUser } from "@/lib/api/types";
import { normalizeBytes32 } from "@/lib/web3/bytes";
import { wagmiConfig } from "@/lib/web3/config";
import membershipGatewayArtifact from "../../../shared/contracts/FanoraMembershipGateway.json";

type AuthStatus =
  | "initializing"
  | "anonymous"
  | "connecting"
  | "signing"
  | "authenticated"
  | "error";

type AuthContextValue = {
  user: FanoraUser | null;
  status: AuthStatus;
  error: string | null;
  loginWithWallet: (
    address: string,
    signMessage: (message: string) => Promise<string>,
  ) => Promise<FanoraUser>;
  logout: () => Promise<void>;
  sendMembershipPayment: (payment: {
    paymentContractAddress: string;
    paymentId: string;
    feeWei: string;
    chainId: number;
  }) => Promise<string>;
  refreshUser: () => Promise<FanoraUser | null>;
  clearError: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    return (
      error.response?.data?.detail ||
      "本地服务暂时无法连接，请确认后端已在 8000 端口运行。"
    );
  }
  if (error instanceof Error) return error.message;
  return "登录没有完成，请重试。";
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  const {
    address: rainbowAddress,
    chainId: rainbowChainId,
    isConnected: rainbowConnected,
  } = useAccount();
  const { openConnectModal } = useConnectModal();
  const { openChainModal } = useChainModal();
  const { openAccountModal } = useAccountModal();
  const [user, setUser] = useState<FanoraUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("initializing");
  const [error, setError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    const token = window.localStorage.getItem(SESSION_TOKEN_KEY);
    if (!token) {
      setUser(null);
      setStatus("anonymous");
      return null;
    }
    const response = await api.get<FanoraUser>("/users/me");
    setUser(response.data);
    setStatus("authenticated");
    return response.data;
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      if (!window.localStorage.getItem(SESSION_TOKEN_KEY)) {
        if (!cancelled) setStatus("anonymous");
        return;
      }
      try {
        await refreshUser();
      } catch {
        window.localStorage.removeItem(SESSION_TOKEN_KEY);
        if (!cancelled) {
          setUser(null);
          setStatus("anonymous");
        }
      }
    }

    void restoreSession();
    return () => {
      cancelled = true;
    };
  }, [refreshUser]);

  const loginWithWallet = useCallback(
    async (
      address: string,
      signMessage: (message: string) => Promise<string>,
    ) => {
      setError(null);
      setStatus("signing");
      try {
        const challenge = await api.post<{
          challenge_id: string;
          message: string;
        }>("/auth/challenge", { wallet_address: address });
        const signature = await signMessage(challenge.data.message);
        const response = await api.post<AuthSession>("/auth/wallet", {
          challenge_id: challenge.data.challenge_id,
          wallet_address: address,
          signature,
        });
        window.localStorage.setItem(SESSION_TOKEN_KEY, response.data.access_token);
        setUser(response.data.user);
        setStatus("authenticated");
        return response.data.user;
      } catch (walletLoginError) {
        setError(getErrorMessage(walletLoginError));
        setStatus(user ? "authenticated" : "anonymous");
        throw walletLoginError;
      }
    },
    [user],
  );

  const logout = useCallback(async () => {
    const token = window.localStorage.getItem(SESSION_TOKEN_KEY);
    try {
      if (token) await api.post("/auth/logout");
    } catch {
      // The local session and wallet connection are still cleared if the API is offline.
    }
    window.localStorage.removeItem(SESSION_TOKEN_KEY);
    await disconnect(wagmiConfig);
    setUser(null);
    setError(null);
    setStatus("anonymous");
  }, []);

  const sendMembershipPayment = useCallback(
    async ({
      paymentContractAddress,
      paymentId,
      feeWei,
      chainId,
    }: {
      paymentContractAddress: string;
      paymentId: string;
      feeWei: string;
      chainId: number;
    }) => {
      if (!user) throw new Error("请先连接钱包并完成签名登录。");
      if (chainId !== 10143 && chainId !== 143) {
        throw new Error("当前钱包网络不受支持。");
      }

      const supportedChainId: 10143 | 143 = chainId;
      const walletAddress = user.primary_wallet.address as `0x${string}`;
      if (!rainbowConnected || !rainbowAddress) {
        openConnectModal?.();
        throw new Error("请先在 RainbowKit 中选择钱包，连接后再次点击支付。");
      }
      if (rainbowAddress.toLowerCase() !== walletAddress.toLowerCase()) {
        openAccountModal?.();
        throw new Error("当前钱包与 Fanora 登录钱包不一致，请切换账户后重试。");
      }
      if (rainbowChainId !== supportedChainId) {
        openChainModal?.();
        throw new Error("请在 RainbowKit 中切换到 Monad 网络，然后再次点击支付。");
      }

      const walletClient = await getWalletClient(wagmiConfig, { chainId: supportedChainId });
      if (!walletClient) {
        throw new Error("RainbowKit 钱包会话尚未准备好，请重新连接后再缴纳会费。");
      }
      const transactionHash = await walletClient.request({
        method: "eth_sendTransaction",
        params: [
          {
            from: walletAddress,
            to: paymentContractAddress as `0x${string}`,
            value: `0x${BigInt(feeWei).toString(16)}`,
            data: encodeFunctionData({
              abi: membershipGatewayArtifact.abi as Abi,
              functionName: "join",
              args: [normalizeBytes32(paymentId)],
            }),
          },
        ],
      });
      return String(transactionHash);
    },
    [
      openAccountModal,
      openChainModal,
      openConnectModal,
      rainbowAddress,
      rainbowChainId,
      rainbowConnected,
      user,
    ],
  );

  const value = useMemo(
    () => ({
      user,
      status,
      error,
      loginWithWallet,
      logout,
      sendMembershipPayment,
      refreshUser,
      clearError: () => setError(null),
    }),
    [
      user,
      status,
      error,
      loginWithWallet,
      logout,
      sendMembershipPayment,
      refreshUser,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
