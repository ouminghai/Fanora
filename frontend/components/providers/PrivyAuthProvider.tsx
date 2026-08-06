"use client";

import { PrivyProvider } from "@privy-io/react-auth";
import type { ReactNode } from "react";
import { monad, monadTestnet } from "wagmi/chains";

type PrivyAuthProviderProps = {
  children: ReactNode;
};

const privyAppId = process.env.NEXT_PUBLIC_PRIVY_APP_ID;
const walletConnectProjectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID;

export const isPrivyConfigured = Boolean(privyAppId);

export default function PrivyAuthProvider({ children }: PrivyAuthProviderProps) {
  if (!privyAppId) return <>{children}</>;

  return (
    <PrivyProvider
      appId={privyAppId}
      config={{
        appearance: {
          theme: "dark",
          accentColor: "#8358ff",
          logo: "/img/logo_white.png",
          showWalletLoginFirst: false,
        },
        loginMethods: ["email", "google", "wallet"],
        embeddedWallets: {
          ethereum: {
            createOnLogin: "users-without-wallets",
          },
        },
        supportedChains: [monadTestnet, monad],
        defaultChain: monadTestnet,
        walletConnectCloudProjectId: walletConnectProjectId || undefined,
      }}
    >
      {children}
    </PrivyProvider>
  );
}
