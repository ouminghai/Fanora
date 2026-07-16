import Footer1 from "@/components/footer/Footer1";
import Header2 from "@/components/headers/Header2";
import Benefits from "@/components/homes/home-9/Benefits";
import Cta from "@/components/homes/home-9/Cta";
import Faq from "@/components/homes/home-9/Faq";

import Hero from "@/components/homes/home-9/Hero";
import Intro from "@/components/homes/home-9/Intro";
import Partners from "@/components/common/Partners2";
import Partners2 from "@/components/homes/home-9/Partners2";

export const metadata = {
  title: "Home 9 || Xhibiter | NFT Marketplace Nextjs Template",
};
export default function HomePage9() {
  return (
    <>
      <Header2 />
      <main>
        <Hero />
        <Partners />
        <Intro />
        <Benefits />
        <Faq />
        <Partners2 />
        <Cta />
      </main>
      <Footer1 />
    </>
  );
}
