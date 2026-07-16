import Footer1 from "@/components/footer/Footer1";
import Header2 from "@/components/headers/Header2";
import Hero from "@/components/pages/maintenance/Hero";

export const metadata = {
  title: "Maintenance || Xhibiter | NFT Marketplace Nextjs Template",
};

export default function MaintenancePage() {
  return (
    <>
      <Header2 />
      <main>
        <Hero />
      </main>
      <Footer1 />
    </>
  );
}
