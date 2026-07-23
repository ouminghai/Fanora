"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { href: "/", label: "Explore" },
  { href: "/community/creations", label: "Echo" },
  { href: "/community#check-in", label: "Check In" },
  { href: "/community/tasks", label: "Quests" },
  { href: "/collections", label: "Gallery" },
  { href: "/collection", label: "Collection" },
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
