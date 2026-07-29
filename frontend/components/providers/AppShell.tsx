"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import ModeChanger from "@/components/common/ModeChanger";
import BidModal from "@/components/modals/BidModal";
import BuyModal from "@/components/modals/BuyModal";
import LevelsModal from "@/components/modals/LevelsModal";
import PropertiesModal from "@/components/modals/PropertiesModal";
import Web3Provider from "@/components/providers/Web3Provider";

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  // The local demo is intentionally isolated from all wallet and session code.
  if (pathname.startsWith("/demo/")) return <>{children}</>;

  return (
    <Web3Provider>
      <ModeChanger />
      {children}
      <BuyModal />
      <BidModal />
      <PropertiesModal />
      <LevelsModal />
    </Web3Provider>
  );
}
