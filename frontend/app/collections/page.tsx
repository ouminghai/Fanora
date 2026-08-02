import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";
import FanNftMarket from "@/components/nft/FanNftMarket";

export const metadata = {
  title: "粉丝 NFT 广场 | Fanora",
};

export default function CollectionsPage() {
  return (
    <div className="relative isolate bg-[#08040f]">
      <Header3 />
      <FanNftMarket mode="market" />
      <div className="relative z-20">
        <Footer1 />
      </div>
    </div>
  );
}
