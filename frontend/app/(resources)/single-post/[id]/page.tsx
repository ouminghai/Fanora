import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import SinglePost from "@/components/resources/SinglePost";

export const metadata = {
  title: "Single Post || Xhibiter | NFT Marketplace Nextjs Template",
};

export default async function SinglePostPage(props) {
  const params = await props.params;
  return (
    <>
      <Header1 />
      <main className="pt-[5.5rem] lg:pt-24">
        <SinglePost id={params.id} />
      </main>
      <Footer1 />
    </>
  );
}
