import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";
import FanNftMarket from "@/components/nft/FanNftMarket";

export const metadata = {
  title: "发布粉丝 NFT | Fanora",
};

export default function CreateFanNftPage() {
  return (
    <>
      <Header3 />
      <FanNftMarket mode="create" />
      <Footer1 />
    </>
  );
}
