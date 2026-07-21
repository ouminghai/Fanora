import CollectionDashboard from "@/components/collection/CollectionDashboard";
import Header3 from "@/components/headers/Header3";

export const metadata = {
  title: "我的收藏 | Fanora",
  description: "查看 Fanora 会员身份、纪念卡与限定 Badge。",
};

export default function CollectionPage() {
  return <><Header3 /><CollectionDashboard /></>;
}
