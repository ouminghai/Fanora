import Header3 from "@/components/headers/Header3";
import ProfileDashboard from "@/components/profile/ProfileDashboard";

export const metadata = {
  title: "我的身份 | Fanora",
  description: "维护 Fanora 用户资料、钱包身份与社区关系。",
};

export default function ProfilePage() {
  return (
    <>
      <Header3 />
      <ProfileDashboard />
    </>
  );
}
