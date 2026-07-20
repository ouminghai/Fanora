"use client";

import axios from "axios";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { Web3Auth } from "@web3auth/modal";
import { api, SESSION_TOKEN_KEY } from "@/lib/api/client";
import type { AuthSession, FanoraUser } from "@/lib/api/types";
import { requestEmbeddedPrivateKey } from "@/lib/web3auth/privateKey";

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
  login: () => Promise<void>;
  logout: () => Promise<void>;
  exportPrivateKey: () => Promise<string>;
  sendMembershipPayment: (payment: {
    treasuryAddress: string;
    feeWei: string;
    chainId: number;
  }) => Promise<string>;
  refreshUser: () => Promise<FanoraUser | null>;
  clearError: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const clientId =
  process.env.NEXT_PUBLIC_WEB3AUTH_CLIENT_ID ||
  "BICxTe9MSpkkwRIrgNGa8cGgksO4VvNiBHqt694T88J_WecKTHn474CmkEtFvaOqfE0CxrtZUmUoZCPYiOf8r88";

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
  const web3AuthRef = useRef<Web3Auth | null>(null);
  const [user, setUser] = useState<FanoraUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("initializing");
  const [error, setError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    const token = window.localStorage.getItem(SESSION_TOKEN_KEY);
    if (!token) {
      setUser(null);
      return null;
    }
    const response = await api.get<FanoraUser>("/users/me");
    setUser(response.data);
    setStatus("authenticated");
    return response.data;
  }, []);

  const completeFanoraLogin = useCallback(async (web3auth: Web3Auth) => {
    const provider = web3auth.provider;
    if (!provider) throw new Error("钱包尚未准备好，请重新连接。 ");

    setStatus("signing");
    const accounts = await provider.request<never, string[]>({
      method: "eth_accounts",
    });
    const address = accounts?.[0];
    if (!address) throw new Error("未能从 Web3Auth 获取钱包地址。 ");

    const challenge = await api.post<{
      challenge_id: string;
      message: string;
    }>("/auth/challenge", { wallet_address: address });
    const messageHex = `0x${Array.from(new TextEncoder().encode(challenge.data.message))
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("")}`;
    const signature = await provider.request<unknown[], string>({
      method: "personal_sign",
      params: [messageHex, address],
    });
    const { idToken } = await web3auth.getIdentityToken();
    const connector = String(web3auth.connectedConnectorName || "");
    const response = await api.post<AuthSession>("/auth/web3auth", {
      challenge_id: challenge.data.challenge_id,
      wallet_address: address,
      signature,
      id_token: idToken,
      wallet_type: connector === "auth" ? "embedded" : "external",
    });
    window.localStorage.setItem(SESSION_TOKEN_KEY, response.data.access_token);
    setUser(response.data.user);
    setStatus("authenticated");
    return response.data.user;
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function initialize() {
      try {
        const { Web3Auth, WEB3AUTH_NETWORK, CHAIN_NAMESPACES } = await import(
          "@web3auth/modal"
        );
        const web3AuthNetwork =
          process.env.NEXT_PUBLIC_WEB3AUTH_NETWORK === "sapphire_mainnet"
            ? WEB3AUTH_NETWORK.SAPPHIRE_MAINNET
            : WEB3AUTH_NETWORK.SAPPHIRE_DEVNET;
        const instance = new Web3Auth({
          clientId,
          // Web3Auth's Sapphire network is independent from the configured EVM chain.
          web3AuthNetwork,
          ssr: true,
          storageType: "local",
          sessionTime: 7 * 24 * 60 * 60,
          walletServicesConfig: {
            loginMode: "plugin",
            enableKeyExport: true,
          },
          chains: [
            {
              chainNamespace: CHAIN_NAMESPACES.EIP155,
              chainId: "0x279f",
              rpcTarget:
                process.env.NEXT_PUBLIC_MONAD_TESTNET_RPC_URL ||
                "https://testnet-rpc.monad.xyz",
              displayName: "Monad Testnet",
              blockExplorerUrl: "https://testnet.monadexplorer.com",
              ticker: "MON",
              tickerName: "Monad",
              logo: "https://web3auth.io/images/web3authlog.png",
            },
          ],
          defaultChainId: "0x279f",
          uiConfig: {
            appName: "Fanora",
            mode: "dark",
            theme: { primary: "#8358ff" },
            defaultLanguage: "zh",
            loginGridCol: 3,
            primaryButton: "socialLogin",
          },
        });
        await instance.init();
        if (cancelled) return;
        web3AuthRef.current = instance;

        const token = window.localStorage.getItem(SESSION_TOKEN_KEY);
        if (token) {
          try {
            await refreshUser();
            return;
          } catch {
            window.localStorage.removeItem(SESSION_TOKEN_KEY);
          }
        }
        if (instance.connected) {
          await completeFanoraLogin(instance);
        } else {
          setStatus("anonymous");
        }
      } catch (initializationError) {
        if (!cancelled) {
          setError(getErrorMessage(initializationError));
          setStatus("error");
        }
      }
    }

    initialize();
    return () => {
      cancelled = true;
    };
  }, [completeFanoraLogin, refreshUser]);

  const login = useCallback(async () => {
    const instance = web3AuthRef.current;
    if (!instance) {
      setError("登录服务仍在初始化，请稍候。 ");
      return;
    }
    setError(null);
    setStatus("connecting");
    try {
      if (!instance.connected) await instance.connect();
      await completeFanoraLogin(instance);
    } catch (loginError) {
      setError(getErrorMessage(loginError));
      setStatus("error");
      throw loginError;
    }
  }, [completeFanoraLogin]);

  const logout = useCallback(async () => {
    const token = window.localStorage.getItem(SESSION_TOKEN_KEY);
    try {
      if (token) await api.post("/auth/logout");
    } catch {
      // Local and provider sessions are still cleared if the API is offline.
    }
    window.localStorage.removeItem(SESSION_TOKEN_KEY);
    if (web3AuthRef.current?.connected) {
      await web3AuthRef.current.logout({ cleanup: true });
    }
    setUser(null);
    setError(null);
    setStatus("anonymous");
  }, []);

  const exportPrivateKey = useCallback(async () => {
    const instance = web3AuthRef.current;
    if (!user || user.primary_wallet.wallet_type !== "embedded") {
      throw new Error("外部钱包的私钥只能在对应钱包应用中导出。");
    }
    if (!instance?.connected || !instance.provider) {
      throw new Error("Web3Auth 钱包会话已断开，请退出后重新登录再导出。");
    }
    if (String(instance.connectedConnectorName || "") !== "auth") {
      throw new Error("当前连接不是 Web3Auth 嵌入式钱包。");
    }

    return requestEmbeddedPrivateKey(instance.provider);
  }, [user]);

  const sendMembershipPayment = useCallback(
    async ({
      treasuryAddress,
      feeWei,
      chainId,
    }: {
      treasuryAddress: string;
      feeWei: string;
      chainId: number;
    }) => {
      const instance = web3AuthRef.current;
      if (!user || !instance?.connected || !instance.provider) {
        throw new Error("钱包会话尚未准备好，请重新登录后再缴纳会费。");
      }
      const provider = instance.provider;
      const expectedChainId = `0x${chainId.toString(16)}`;
      const currentChainId = await provider.request<never, string>({ method: "eth_chainId" });
      if (currentChainId.toLowerCase() !== expectedChainId.toLowerCase()) {
        try {
          await provider.request<unknown[], null>({
            method: "wallet_switchEthereumChain",
            params: [{ chainId: expectedChainId }],
          });
        } catch (switchError) {
          throw new Error("请先将钱包切换到 Monad Testnet 后再缴纳会费。", {
            cause: switchError,
          });
        }
      }
      return provider.request<unknown[], string>({
        method: "eth_sendTransaction",
        params: [
          {
            from: user.primary_wallet.address,
            to: treasuryAddress,
            value: `0x${BigInt(feeWei).toString(16)}`,
          },
        ],
      });
    },
    [user],
  );

  const value = useMemo(
    () => ({
      user,
      status,
      error,
      login,
      logout,
      exportPrivateKey,
      sendMembershipPayment,
      refreshUser,
      clearError: () => setError(null),
    }),
    [
      user,
      status,
      error,
      login,
      logout,
      exportPrivateKey,
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
