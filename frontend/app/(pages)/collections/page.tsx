import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import Collections from "@/components/pages/Collections";

export const metadata = {
  title: "Collcetions || Xhibiter | NFT Marketplace Nextjs Template",
};

export default function CollectionsPage() {
  return (
    <>
      <Header1 />
      <main>
        <Collections />
      </main>
      <Footer1 />
    </>
  );
}
