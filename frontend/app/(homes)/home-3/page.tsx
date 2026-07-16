import Footer1 from "@/components/footer/Footer1";
import Header2 from "@/components/headers/Header2";
import Featured from "@/components/homes/home-3/Featured";

import Categories from "@/components/homes/home-3/Categories";
import Collections from "@/components/homes/home-3/Collections";
import Hero from "@/components/homes/home-3/Hero";
import HotBits from "@/components/homes/home-3/HotBits";

import Process from "@/components/homes/home-3/Process";
import Partners from "@/components/common/Partners";

export const metadata = {
  title: "Home 3 || Xhibiter | NFT Marketplace Nextjs Template",
};
export default function HomePage3() {
  return (
    <>
      <Header2 />
      <main>
        <Hero />
        <Categories />
        <HotBits />
        <Collections />
        <Featured />
        <Process />
        <Partners />
      </main>
      <Footer1 />
    </>
  );
}
