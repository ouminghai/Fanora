import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import Activity from "@/components/pages/Activity";

export const metadata = {
  title: "Activity || Xhibiter | NFT Marketplace Nextjs Template",
};

export default function ActivityPage() {
  return (
    <>
      <Header1 />
      <main>
        <Activity />
      </main>
      <Footer1 />
    </>
  );
}
