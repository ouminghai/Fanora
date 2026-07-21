"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { href: "/", label: "首页" },
  { href: "/community/creations", label: "链上社区" },
  { href: "/community#check-in", label: "每日签到" },
  { href: "/community/tasks", label: "粉丝任务" },
  { href: "/collection", label: "我的收藏" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <>
      {navigation.map((item) => (
        <li key={item.href} className="group">
          <Link
            href={item.href}
            aria-current={
              item.href === "/community" && pathname.startsWith("/community")
                ? "page"
                : item.href === pathname
                  ? "page"
                  : undefined
            }
            className="flex items-center justify-between py-3.5 font-display text-base text-jacarta-700 hover:text-accent focus:text-accent aria-[current=page]:text-accent dark:text-white dark:hover:text-accent dark:focus:text-accent lg:px-4 xl:px-5"
          >
            {item.label}
          </Link>
        </li>
      ))}
    </>
  );
}
