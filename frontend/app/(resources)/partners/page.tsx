import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import Benefits from "@/components/resources/partners/Benefits";
import Collcetions from "@/components/resources/partners/Collcetions";
import Faq from "@/components/resources/partners/Faq";
import Process from "@/components/resources/partners/Process";
import Testimonials from "@/components/resources/partners/Testimonials";
import Image from "next/image";

export const metadata = {
  title: "Partners || Xhibiter | NFT Marketplace Nextjs Template",
};

export default function PartnersPage() {
  return (
    <>
      <Header1 />
      <main className="pt-[5.5rem] lg:pt-24">
        <Benefits />
        <Process />
        <section className="relative py-24">
          <picture className="pointer-events-none absolute inset-0 -z-10 dark:hidden">
            <Image
              width={1920}
              height={789}
              src="/img/gradient_light.jpg"
              priority
              alt="gradient"
              className="h-full w-full"
            />
          </picture>
          <div className="container">
            <div className="mx-auto mb-8 max-w-xl text-center">
              <h2 className="mb-6 text-center font-display text-3xl font-medium text-jacarta-700 dark:text-white">
                Who has partnered with us
              </h2>
              <p className="dark:text-jacarta-300">
                While we take pride in being the first and largest marketplace
                and in our robust feature set, we also help our partners succeed
                with the following...
              </p>
            </div>
            <Collcetions />
            <Faq />
            <Testimonials />
          </div>
        </section>
      </main>
      <Footer1 />
    </>
  );
}
