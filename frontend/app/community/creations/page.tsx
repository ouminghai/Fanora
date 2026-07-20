import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";
import CreationWall from "@/components/community/CreationWall";

export const metadata = {
  title: "创作社区 | Fanora",
  description: "浏览 Fanora 粉丝故事、歌单与社区共创。",
};

export default function CommunityCreationsPage() {
  return <><Header3 /><CreationWall /><Footer1 /></>;
}
