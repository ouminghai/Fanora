"use client";

const navigation = [
  { href: "#missions", label: "粉丝任务" },
  { href: "#badges", label: "Badge 成长" },
  { href: "#fan-journey", label: "加入流程" },
  { href: "#proof-of-fandom", label: "粉丝身份" },
  { href: "#technology", label: "技术架构" },
];

export default function Nav() {
  return (
    <>
      {navigation.map((item) => (
        <li key={item.href} className="group">
          <a
            href={item.href}
            className="flex items-center justify-between py-3.5 font-display text-base text-jacarta-700 hover:text-accent focus:text-accent dark:text-white dark:hover:text-accent dark:focus:text-accent lg:px-5"
          >
            {item.label}
          </a>
        </li>
      ))}
    </>
  );
}
