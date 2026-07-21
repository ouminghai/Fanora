import "@rainbow-me/rainbowkit/styles.css";
import "../public/styles/style.css";
import "swiper/css";
import "swiper/css/pagination";
import "photoswipe/dist/photoswipe.css";
import "tippy.js/dist/tippy.css";

import BidModal from "@/components/modals/BidModal";
import BuyModal from "@/components/modals/BuyModal";
import LevelsModal from "@/components/modals/LevelsModal";
import PropertiesModal from "@/components/modals/PropertiesModal";
import ModeChanger from "@/components/common/ModeChanger";
import Web3Provider from "@/components/providers/Web3Provider";

export const metadata = {
  title: "Fanora Protocol",
  description: "AI-powered Proof of Fandom identities on Monad.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        itemScope
        itemType="http://schema.org/WebPage"
        className="overflow-x-hidden font-body text-jacarta-500 dark:bg-jacarta-900"
      >
        <Web3Provider>
          <ModeChanger />
          {children}
          <BuyModal />
          <BidModal />
          <PropertiesModal />
          <LevelsModal />
        </Web3Provider>
      </body>
    </html>
  );
}
