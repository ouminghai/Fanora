import { redirect } from "next/navigation";

export const metadata = {
  title: "我的身份 | Fanora",
  description: "维护 Fanora 用户资料、钱包身份与社区关系。",
};

export default function ProfilePage() {
  redirect("/collection?tab=profile");
}
