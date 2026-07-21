import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";
import CommunityHub from "@/components/community/CommunityHub";

export const metadata = {
  title: "Fanora 链上社区 | 签到、任务与创作",
  description: "进入 Fanora 链上社区，完成每日签到、粉丝任务并参与内容共创。",
};

export default function CommunityPage() {
  return (
    <>
      <Header3 />
      <CommunityHub />
      <Footer1 />
    </>
  );
}
