import Partners from "@/components/common/Partners";
import Footer1 from "@/components/footer/Footer1";
import Header1 from "@/components/headers/Header1";
import Testimonials from "@/components/common/Testimonials";
import Approach from "@/components/pages/case-studies/Approach";
import Post from "@/components/pages/case-studies/Post";
import RelatedPost from "@/components/pages/case-studies/RelatedPost";
import Result from "@/components/pages/case-studies/Result";

export const metadata = {
  title: "Case Study Details || Xhibiter | NFT Marketplace Nextjs Template",
};

export default async function CaseStudyDetailsPage(props) {
  const params = await props.params;
  return (
    <>
      <Header1 />
      <main className="pt-[5.5rem] lg:pt-24">
        <Post id={params.id} />
        <Approach />
        <Result />
        <Testimonials />
        <RelatedPost />
        <Partners />
      </main>
      <Footer1 />
    </>
  );
}
