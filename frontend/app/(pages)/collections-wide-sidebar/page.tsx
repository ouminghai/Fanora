import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import Collections from "@/components/pages/collections-wide-sidebar/Collections";

export const metadata = {
  title:
    "Collcetions Wide Sidebar || Xhibiter | NFT Marketplace Nextjs Template",
};

export default function CollectionWideSidebarPage() {
  return (
    <>
      <Header1 />
      <main className="mt-24">
        <Collections />
      </main>
      <Footer1 />
    </>
  );
}
