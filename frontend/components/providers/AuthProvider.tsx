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
import { encodeFunctionData, type Abi } from "viem";
import { api, SESSION_TOKEN_KEY } from "@/lib/api/client";
import type { AuthSession, FanoraUser } from "@/lib/api/types";
import { requestEmbeddedPrivateKey } from "@/lib/web3auth/privateKey";
import { withWeb3AuthTimeout } from "@/lib/web3auth/timeout";
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
  login: () => Promise<void>;
  logout: () => Promise<void>;
  exportPrivateKey: () => Promise<string>;
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

const clientId =
  process.env.NEXT_PUBLIC_WEB3AUTH_CLIENT_ID ||
  "BICxTe9MSpkkwRIrgNGa8cGgksO4VvNiBHqt694T88J_WecKTHn474CmkEtFvaOqfE0CxrtZUmUoZCPYiOf8r88";
const WEB3AUTH_CONNECT_TIMEOUT_MS = 30_000;

function encodePersonalSignMessage(message: string) {
  return `0x${Array.from(new TextEncoder().encode(message))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("")}`;
}

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
    const signature = await provider.request<unknown[], string>({
      method: "personal_sign",
      params: [encodePersonalSignMessage(challenge.data.message), address],
    });
    const response = await api.post<AuthSession>("/auth/web3auth", {
      challenge_id: challenge.data.challenge_id,
      wallet_address: address,
      signature,
      id_token: (await web3auth.getIdentityToken()).idToken,
      app_pub_key:
        String(web3auth.connectedConnectorName || "") === "auth"
          ? await provider.request<never, string>({ method: "public_key" })
          : undefined,
      wallet_type:
        String(web3auth.connectedConnectorName || "") === "auth" ? "embedded" : "external",
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
        const { Web3Auth, WEB3AUTH_NETWORK, CHAIN_NAMESPACES, WALLET_CONNECTORS } = await import(
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
          modalConfig: {
            connectors: {
              [WALLET_CONNECTORS.AUTH]: {
                label: "auth",
                showOnModal: true,
              },
              [WALLET_CONNECTORS.METAMASK]: {
                label: "metamask",
                showOnModal: true,
              },
              [WALLET_CONNECTORS.WALLET_CONNECT_V2]: {
                label: "wallet-connect",
                showOnModal: Boolean(process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID),
              },
              [WALLET_CONNECTORS.COINBASE]: {
                label: "coinbase",
                showOnModal: false,
              },
            },
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
      if (!instance.connected) {
        await withWeb3AuthTimeout(
          instance.connect(),
          WEB3AUTH_CONNECT_TIMEOUT_MS,
          "钱包确认没有完成，请重试，或改用邮箱/社交账号登录。",
        );
      }
      await completeFanoraLogin(instance);
    } catch (loginError) {
      setError(getErrorMessage(loginError));
      setStatus(user ? "authenticated" : "anonymous");
      throw loginError;
    }
  }, [completeFanoraLogin, user]);

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
      const instance = web3AuthRef.current;
      if (!user || !instance?.connected || !instance.provider) {
        throw new Error("钱包会话尚未准备好，请重新登录后再缴纳会费。");
      }
      const connectorName = String(instance.connectedConnectorName || "").toLowerCase();
      if (user.primary_wallet.wallet_type !== "external" || connectorName !== "metamask") {
        throw new Error(
          "入会付款必须由 MetaMask 确认。请退出当前钱包，并在 Web3Auth Modal 中选择 MetaMask 重新连接。",
        );
      }
      const provider = instance.provider;
      const accounts = await provider.request<never, string[]>({ method: "eth_accounts" });
      const activeAccount = accounts?.[0];
      if (!activeAccount || activeAccount.toLowerCase() !== user.primary_wallet.address.toLowerCase()) {
        throw new Error("MetaMask 当前账户与 Fanora 登录主钱包不一致，请切换账户后重试。");
      }
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
        // eth_sendTransaction 只请求 MetaMask 弹窗签名，不读取、导出或上传用户私钥。
        method: "eth_sendTransaction",
        params: [
          {
            from: user.primary_wallet.address,
            to: paymentContractAddress,
            value: `0x${BigInt(feeWei).toString(16)}`,
            data: encodeFunctionData({
              abi: membershipGatewayArtifact.abi as Abi,
              functionName: "join",
              args: [paymentId],
            }),
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
