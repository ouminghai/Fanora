import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import Contact from "@/components/pages/contact/Contact";
import PageTitle from "@/components/pages/contact/PageTitle";

export const metadata = {
  title: "Contact || Xhibiter | NFT Marketplace Nextjs Template",
};

export default function ContactPage() {
  return (
    <>
      <Header1 />
      <main className="pt-[5.5rem] lg:pt-24">
        <PageTitle />
        <Contact />
      </main>
      <Footer1 />
    </>
  );
}
