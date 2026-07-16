import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import AggregatorTable from "@/components/homes/home-13/AggregatorTable";
import Hero from "@/components/homes/home-13/Hero";

export const metadata = {
  title: "Home 13 || Xhibiter | NFT Marketplace Nextjs Template",
};
export default function HomePage13() {
  return (
    <>
      <Header1 />
      <main>
        <Hero />
        <AggregatorTable />
      </main>
      <Footer1 />
    </>
  );
}
