import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";
import NftStudioWorkbench from "@/components/nft/NftStudioWorkbench";

export const metadata = {
  title: "发布粉丝 NFT | Fanora",
};

export default function CreateFanNftPage() {
  return (
    <>
      <Header3 />
      <NftStudioWorkbench />
      <div className="relative z-30">
        <Footer1 />
      </div>
    </>
  );
}
