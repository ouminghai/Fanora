import Header3 from "@/components/headers/Header3";
import OfficialMembershipCheckout from "@/components/membership/OfficialMembershipCheckout";

export const metadata = {
  title: "正式加入 Fans Club | Fanora",
  description: "完成一次链上身份认证，开启你的 Fanora 粉丝身份。",
};

export default function OfficialMembershipJoinPage() {
  return (
    <>
      <Header3 />
      <OfficialMembershipCheckout />
    </>
  );
}
