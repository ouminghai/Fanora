import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import Create from "@/components/create/Create";

export const metadata = {
  title: "Create || Xhibiter | NFT Marketplace Nextjs Template",
};

export default function CreatePage() {
  return (
    <>
      <Header1 />
      <main>
        <Create />
      </main>
      <Footer1 />
    </>
  );
}
