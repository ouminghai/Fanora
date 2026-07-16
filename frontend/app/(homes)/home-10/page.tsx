import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import Features from "@/components/homes/home-10/Features";
import Hero from "@/components/homes/home-10/Hero";
import Promo from "@/components/homes/home-10/Promo";
import Partners from "@/components/common/Partners2";
import Benefits from "@/components/homes/home-10/Benefits";
import Testimonials from "@/components/homes/common/Testimonials";
import Cta from "@/components/homes/common/Cta";
import Help from "@/components/homes/home-10/Help";

export const metadata = {
  title: "Home 10 || Xhibiter | NFT Marketplace Nextjs Template",
};
export default function HomePage10() {
  return (
    <>
      <Header1 />
      <main>
        <Hero />
        <Features />
        <Promo />
        <Partners />
        <Benefits />
        <Testimonials />
        <Cta />
        <Help />
      </main>
      <Footer1 />
    </>
  );
}
