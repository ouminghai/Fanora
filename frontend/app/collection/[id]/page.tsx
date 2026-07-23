import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";
import FanNftMarket from "@/components/nft/FanNftMarket";

export const metadata = {
  title: "粉丝 NFT 集合 | Fanora",
};

export default function FanNftCollectionPage() {
  return (
    <>
      <Header3 />
      <FanNftMarket mode="collection" />
      <Footer1 />
    </>
  );
}
