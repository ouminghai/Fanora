import { getDefaultConfig } from "@rainbow-me/rainbowkit";
import { http } from "wagmi";
import { monad, monadTestnet } from "wagmi/chains";

export const supportedChains = [monadTestnet, monad] as const;

const walletConnectProjectId =
  process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || "YOUR_PROJECT_ID";

export const wagmiConfig = getDefaultConfig({
  appName: process.env.NEXT_PUBLIC_APP_NAME || "Fanora Protocol",
  appDescription: "AI-powered Proof of Fandom identities on Monad.",
  appUrl: process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  projectId: walletConnectProjectId,
  chains: supportedChains,
  ssr: true,
  transports: {
    [monadTestnet.id]: http(process.env.NEXT_PUBLIC_MONAD_TESTNET_RPC_URL),
    [monad.id]: http(process.env.NEXT_PUBLIC_MONAD_RPC_URL),
  },
});
