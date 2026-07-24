import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";
import PublicCollectionDashboard from "@/components/profile/PublicCollectionDashboard";

export const metadata = {
  title: "用户主页 | Fanora",
};

export default async function UserPublicPage({
  params,
}: {
  params: Promise<{ userId: string }>;
}) {
  const { userId } = await params;
  return (
    <>
      <Header3 />
      <PublicCollectionDashboard userId={userId} />
      <Footer1 />
    </>
  );
}
