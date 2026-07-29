import AiNftCreationWorkbench from "@/components/nft/AiNftCreationWorkbench";

export const metadata = {
  title: "免钱包试玩 | Fanora",
};

export default function AiNftDemoPage() {
  return (
    <>
      <div className="fixed inset-x-0 top-0 z-50 border-b border-fuchsia-200 bg-white/95 px-4 py-3 text-center text-sm font-medium text-[#3d286c] shadow-sm backdrop-blur dark:border-fuchsia-300/20 dark:bg-[#171522]/95 dark:text-fuchsia-100">
        本地试玩模式：无需连接钱包；可生成 AI 草稿，但不会扣除 FAN、发布或上链。
      </div>
      <AiNftCreationWorkbench demoMode />
    </>
  );
}
