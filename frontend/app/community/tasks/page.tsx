import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";
import TaskGallery from "@/components/community/TaskGallery";

export const metadata = {
  title: "粉丝任务中心 | Fanora",
  description: "浏览、领取并完成 Fanora 官方社区粉丝任务。",
};

export default function CommunityTasksPage() {
  return <><Header3 /><TaskGallery /><Footer1 /></>;
}
