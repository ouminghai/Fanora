import Header3 from "@/components/headers/Header3";
import LoginExperience from "@/components/auth/LoginExperience";

export const metadata = {
  title: "登录 | Fanora",
  description: "使用 Privy、邮箱、Google 或钱包快速获得 Fanora 粉丝身份。",
};

export default function LoginPage() {
  return (
    <>
      <Header3 />
      <LoginExperience />
    </>
  );
}
