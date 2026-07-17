"use client";

import { useState } from "react";
import Image from "next/image";
import { fanMissions } from "@/data/fanora";

const labels = ["进行中", "即将开始", "已完成"];

export default function Collections() {
  const [activeLabel, setActiveLabel] = useState(labels[0]);

  return (
    <section id="missions" className="relative py-24 dark:bg-jacarta-800">
      <picture className="pointer-events-none absolute inset-0 -z-10 dark:hidden">
        <Image
          width={1920}
          height={789}
          src="/img/gradient_light.jpg"
          priority
          alt="gradient"
          className="h-full w-full"
        />
      </picture>
      <div className="container">
        <div className="mb-12 text-center font-display text-3xl text-jacarta-700 dark:text-white">
          <h2 className="inline">热门粉丝任务</h2>{" "}
          <div className="dropdown inline cursor-pointer">
            <button
              className="dropdown-toggle inline-flex items-center text-accent"
              type="button"
              id="missionSort"
              data-bs-toggle="dropdown"
              aria-expanded="false"
            >
              · {activeLabel}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                width="24"
                height="24"
                className="h-8 w-8 fill-accent"
              >
                <path fill="none" d="M0 0h24v24H0z" />
                <path d="M12 13.172l4.95-4.95 1.414 1.414L12 16 5.636 9.636 7.05 8.222z" />
              </svg>
            </button>
            <div
              className="dropdown-menu z-10 hidden min-w-[200px] whitespace-nowrap rounded-xl bg-white py-4 px-2 text-left shadow-xl dark:bg-jacarta-800"
              aria-labelledby="missionSort"
            >
              {labels.map((label) => (
                <button
                  type="button"
                  onClick={() => setActiveLabel(label)}
                  key={label}
                  className="dropdown-item block w-full cursor-pointer rounded-xl px-5 py-2 text-left text-sm transition-colors hover:bg-jacarta-50 dark:hover:bg-jacarta-600"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-[1.875rem] lg:grid-cols-4">
          {fanMissions.map((mission) => (
            <div
              key={mission.id}
              className="flex rounded-2.5xl border border-jacarta-100 bg-white py-4 px-7 transition-shadow hover:shadow-lg dark:border-transparent dark:bg-jacarta-700"
            >
              <figure className="mr-4 shrink-0 rtl:mr-0 rtl:ml-4">
                <a href="#fan-journey" className="relative block">
                  <Image
                    width={48}
                    height={48}
                    src={mission.avatar}
                    alt={mission.name}
                    className="h-12 w-12 rounded-2lg object-cover"
                    loading="lazy"
                  />
                  <div className="absolute -left-3 top-1/2 flex h-6 w-6 -translate-y-2/4 items-center justify-center rounded-full border-2 border-white bg-jacarta-700 text-xs text-white dark:border-jacarta-600">
                    {mission.id}
                  </div>
                </a>
              </figure>
              <div>
                <a href="#fan-journey" className="block">
                  <span className="font-display font-semibold text-jacarta-700 hover:text-accent dark:text-white">
                    {mission.name}
                  </span>
                </a>
                <span className="text-sm dark:text-jacarta-300">
                  {mission.detail}
                </span>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-10 text-center">
          <a
            href="#fan-journey"
            className="inline-block rounded-full bg-accent py-3 px-8 text-center font-semibold text-white shadow-accent-volume transition-all hover:bg-accent-dark"
          >
            查看全部任务
          </a>
        </div>
      </div>
    </section>
  );
}
