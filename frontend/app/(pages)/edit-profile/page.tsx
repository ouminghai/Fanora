import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import Banner from "@/components/pages/edit-profile/Banner";
import EditProfile from "@/components/pages/edit-profile/EditProfile";

export const metadata = {
  title: "Edit Profile || Xhibiter | NFT Marketplace Nextjs Template",
};

export default function EditProfilePage() {
  return (
    <>
      <Header1 />
      <main className="pt-[5.5rem] lg:pt-24">
        <Banner />
        <EditProfile />
      </main>
      <Footer1 />
    </>
  );
}
