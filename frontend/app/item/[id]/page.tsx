import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";
import FanNftMarket from "@/components/nft/FanNftMarket";

export const metadata = {
  title: "NFT 详情 | Fanora",
};

export default function FanNftItemPage() {
  return (
    <>
      <Header3 />
      <FanNftMarket mode="item" />
      <Footer1 />
    </>
  );
}
