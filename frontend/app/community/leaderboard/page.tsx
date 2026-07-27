import FanTokenLeaderboard from "@/components/community/FanTokenLeaderboard";
import Footer1 from "@/components/footer/Footer1";
import Header3 from "@/components/headers/Header3";

export const metadata = {
  title: "Fan Token 排行榜 | Fanora",
  description: "查看 Fanora 社区 Fan Token 排名前 10 的公开用户。",
};

export default function CommunityLeaderboardPage() {
  return <><Header3 /><FanTokenLeaderboard /><Footer1 /></>;
}
