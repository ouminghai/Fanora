import Footer1 from "@/components/footer/Footer1";

import Header3 from "@/components/headers/Header3";
import Auction from "@/components/homes/common/Auction";
import Collections from "@/components/homes/common/Collections";
import Process from "@/components/homes/common/Process";
import CoverFlowSlider from "@/components/homes/home/CoverFlowSlider";
import Hero from "@/components/homes/home/Hero";

import Partners from "@/components/common/Partners";

export const metadata = {
  title: "Fanora | 链上粉丝社区与 AI NFT 创作",
};
export default function HomePage() {
  return (
    <>
      <Header3 showVideoSoundControl />
      <main>
        <Hero />
        <CoverFlowSlider />
        <div className="relative isolate overflow-hidden bg-[#09051c]">
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_15%_8%,rgba(101,69,220,.25),transparent_30%),radial-gradient(circle_at_88%_48%,rgba(45,184,224,.12),transparent_27%),radial-gradient(circle_at_30%_92%,rgba(131,88,255,.16),transparent_32%),linear-gradient(180deg,#0d0a28_0%,#100a2c_38%,#0d0a27_72%,#0a071f_100%)]" />
          <Collections />
          <Auction />
          <Process />
        </div>
        {/* <Partners /> */}
      </main>
      <Footer1 />
    </>
  );
}
