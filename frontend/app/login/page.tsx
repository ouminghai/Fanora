import Header3 from "@/components/headers/Header3";
import LoginExperience from "@/components/auth/LoginExperience";

export const metadata = {
  title: "登录 | Fanora",
  description: "使用 Web3Auth 快捷登录并获得 Fanora 钱包身份。",
};

export default function LoginPage() {
  return (
    <>
      <Header3 />
      <LoginExperience />
    </>
  );
}
