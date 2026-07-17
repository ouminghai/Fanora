import Image from "next/image";
import { badgeLevels } from "@/data/fanora";

export default function Auction() {
  return (
    <section id="badges" className="py-24">
      <div className="container">
        <h2 className="mb-8 text-center font-display text-3xl text-jacarta-700 dark:text-white">
          <span className="mr-1 inline-block animate-heartBeat text-xl">🏅</span>
          粉丝等级与 Badge 成长
        </h2>

        <div className="grid grid-cols-1 gap-[1.875rem] md:grid-cols-2 lg:grid-cols-4">
          {badgeLevels.map((badge) => (
            <article key={badge.id}>
              <div className="block rounded-2.5xl border border-jacarta-100 bg-white p-[1.1875rem] transition-shadow hover:shadow-lg dark:border-jacarta-700 dark:bg-jacarta-700">
                <div className="mb-4 flex items-center justify-between">
                  <span className="rounded-full bg-accent-lighter py-1 px-3 text-2xs font-semibold text-accent">
                    {badge.level}
                  </span>
                  <span className="text-2xs text-jacarta-400 dark:text-jacarta-300">
                    动态身份凭证
                  </span>
                </div>

                <figure className="relative">
                  <Image
                    width={230}
                    height={230}
                    src={badge.imageSrc}
                    alt={badge.title}
                    className="aspect-square w-full rounded-[0.625rem] object-cover"
                    loading="lazy"
                  />
                  <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center justify-center rounded-full bg-white py-2.5 px-6 text-2xs font-medium whitespace-nowrap text-jacarta-700 shadow-lg">
                    {badge.progress}
                  </div>
                </figure>

                <div className="mt-7 flex items-center justify-between">
                  <span className="font-display text-base text-jacarta-700 dark:text-white">
                    {badge.title}
                  </span>
                  <span className="flex items-center whitespace-nowrap rounded-md border border-jacarta-100 py-1 px-2 text-2xs font-semibold text-accent dark:border-jacarta-600">
                    SBT
                  </span>
                </div>

                <div className="mt-2 text-sm">
                  <span className="dark:text-jacarta-300">升级门槛：</span>{" "}
                  <span className="text-jacarta-700 dark:text-jacarta-100">
                    {badge.points}
                  </span>
                </div>

                <div className="mt-8 flex items-center justify-between border-t border-jacarta-100 pt-4 dark:border-jacarta-600">
                  <span className="font-display text-sm font-semibold text-accent">
                    {badge.benefit}
                  </span>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    width="24"
                    height="24"
                    className="h-4 w-4 fill-jacarta-500 dark:fill-jacarta-200"
                  >
                    <path fill="none" d="M0 0h24v24H0z" />
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 21 12 17.77 5.82 21 7 14.14l-5-4.87 6.91-1.01L12 2z" />
                  </svg>
                </div>
              </div>
            </article>
          ))}
        </div>

        <div className="mt-10 text-center">
          <a
            href="#fan-journey"
            className="inline-block rounded-full bg-accent py-3 px-8 text-center font-semibold text-white shadow-accent-volume transition-all hover:bg-accent-dark"
          >
            查看我的成长路径
          </a>
        </div>
      </div>
    </section>
  );
}
