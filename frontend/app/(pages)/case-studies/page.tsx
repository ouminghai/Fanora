import Partners from "@/components/common/Partners";
import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import CaseStudies from "@/components/pages/case-studies";

export const metadata = {
  title: "Case Studies || Xhibiter | NFT Marketplace Nextjs Template",
};

export default function CaseStudiesPage() {
  return (
    <>
      <Header1 />
      <main className="pt-[5.5rem] lg:pt-24">
        <CaseStudies />
        <Partners />
      </main>
      <Footer1 />
    </>
  );
}
