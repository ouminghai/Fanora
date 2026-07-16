import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import Banner from "@/components/pages/user/Banner";
import Collcetions from "@/components/pages/user/Collcetions";
import Profile from "@/components/pages/user/Profile";

export const metadata = {
  title: "User || Xhibiter | NFT Marketplace Nextjs Template",
};

export default function UserPage() {
  return (
    <>
      <Header1 />
      <main className="pt-[5.5rem] lg:pt-24">
        <Banner />
        <Profile />
        <Collcetions />
      </main>
      <Footer1 />
    </>
  );
}
