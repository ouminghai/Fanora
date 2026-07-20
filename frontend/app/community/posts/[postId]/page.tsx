import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";
import PostDetail from "@/components/community/PostDetail";

export default async function CommunityPostPage({
  params,
}: {
  params: Promise<{ postId: string }>;
}) {
  const { postId } = await params;
  return (
    <>
      <Header3 />
      <PostDetail postId={postId} />
      <Footer1 />
    </>
  );
}
