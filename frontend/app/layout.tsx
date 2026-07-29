import "@rainbow-me/rainbowkit/styles.css";
import "../public/styles/style.css";
import "swiper/css";
import "swiper/css/pagination";
import "photoswipe/dist/photoswipe.css";
import "tippy.js/dist/tippy.css";

import AppShell from "@/components/providers/AppShell";

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
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
