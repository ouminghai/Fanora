import { Bot, Boxes, RadioTower, ShieldCheck } from "lucide-react";
import Link from "next/link";

const footerGroups = [
  {
    title: "社区",
    links: [
      ["链上社区", "/community"],
      ["粉丝任务", "/community/tasks"],
      ["创作社区", "/community/creations"],
      ["Fan Token 排行", "/community/leaderboard"],
    ],
  },
  {
    title: "NFT 创作",
    links: [
      ["NFT Gallery", "/collections"],
      ["AI Agent 创作台", "/collections/create"],
      ["我的链上收藏", "/collection"],
      ["视觉模板与参考图", "/collections/create"],
    ],
  },
  {
    title: "身份",
    links: [
      ["我的身份资料", "/profile"],
      ["正式会员激活", "/membership/join"],
      ["连接钱包登录", "/login"],
      ["身份成长链路", "/#fan-journey"],
    ],
  },
] as const;

export default function Footer1() {
  return (
    <footer id="site-footer" className="relative overflow-hidden border-t border-white/10 bg-[#05020c] text-white">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(192,132,252,.045)_1px,transparent_1px),linear-gradient(90deg,rgba(192,132,252,.045)_1px,transparent_1px)] bg-[size:38px_38px] opacity-70" />
      <div className="container relative z-10">
        <div className="grid grid-cols-1 gap-12 py-20 md:grid-cols-12">
          <div className="md:col-span-5">
            <Link href="/" className="inline-flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-md border border-accent/35 bg-accent/10 text-accent-light"><RadioTower className="h-5 w-5" /></span>
              <span className="font-display text-2xl font-bold">Fanor<span className="text-accent">A</span></span>
            </Link>
            <p className="mt-6 max-w-md text-sm leading-7 text-white/55">连接钱包、参与社区、积累 FAN，并通过 AI Agent 把真实粉丝故事创作为 NFT 与粉丝周边，让身份、记忆与收藏持续留在链上。</p>
            <div className="mt-7 flex flex-wrap gap-2 text-[10px] font-bold text-white/55">
              <span className="inline-flex items-center gap-2 border border-white/10 px-3 py-2"><ShieldCheck className="h-3.5 w-3.5 text-green" /> SELF-CUSTODY</span>
              <span className="inline-flex items-center gap-2 border border-white/10 px-3 py-2"><Bot className="h-3.5 w-3.5 text-accent-light" /> LANGGRAPH AGENT</span>
              <span className="inline-flex items-center gap-2 border border-white/10 px-3 py-2"><Boxes className="h-3.5 w-3.5 text-blue" /> MONAD NFT</span>
            </div>
          </div>

          {footerGroups.map((group, index) => (
            <nav key={group.title} className={index === 2 ? "md:col-span-3" : "md:col-span-2"} aria-label={group.title}>
              <h3 className="mb-5 font-display text-sm text-white">{group.title}</h3>
              <ul className="space-y-3 text-sm text-white/50">
                {group.links.map(([label, href]) => <li key={label}><Link href={href} className="transition-colors hover:text-accent-light">{label}</Link></li>)}
              </ul>
            </nav>
          ))}
        </div>

        <div className="flex flex-col gap-3 border-t border-white/10 py-7 text-xs text-white/35 sm:flex-row sm:items-center sm:justify-between">
          <span>&copy; {new Date().getFullYear()} Fanora Protocol. Built for verifiable fandom on Monad.</span>
          <span className="inline-flex items-center gap-2 font-mono"><i className="h-1.5 w-1.5 rounded-full bg-accent shadow-[0_0_8px_#8358ff]" /> NETWORK STATUS: ONLINE</span>
        </div>
      </div>
    </footer>
  );
}
