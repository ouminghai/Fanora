"use client";

import { useState } from "react";

export default function Hero() {
  const [hasJoined, setHasJoined] = useState(false);

  return (
    <section className="hero relative overflow-hidden py-20 md:pt-32">
      <video
        className="pointer-events-none absolute inset-0 -z-20 h-full w-full object-cover opacity-50"
        autoPlay
        muted
        loop
        playsInline
        poster="/img/fanora/eason-concert.webp"
        aria-hidden="true"
      >
        <source src="/img/fanora/eason-hero.mp4" type="video/mp4" />
      </video>
      <div className="pointer-events-none absolute inset-0 -z-10 bg-white/30 dark:bg-jacarta-900/55" />
      <div className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-b from-transparent via-white/10 to-white dark:to-jacarta-900" />

      <div className="container">
        <div className="mx-auto max-w-2xl pt-24 text-center">
          <h1 className="mb-10 font-display text-5xl text-jacarta-700 dark:text-white lg:text-6xl xl:text-7xl">
            让每一次支持，都成为可验证的{" "}
            <span className="animate-gradient">Eason Fans Club 身份</span>
          </h1>

          <button
            type="button"
            onClick={() => setHasJoined(true)}
            className="group relative mb-4 flex w-full items-center justify-center rounded-2xl border border-jacarta-100 bg-white py-4 px-4 text-md font-semibold text-jacarta-700 shadow-white-volume transition-all hover:border-accent hover:bg-accent hover:text-white dark:border-transparent dark:bg-white/[.15] dark:text-white dark:hover:bg-accent"
          >
            <span className="absolute left-0 top-0 flex h-full w-12 items-center justify-center rounded-2xl">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                width="24"
                height="24"
                className="h-4 w-4 fill-jacarta-500 transition-colors group-hover:fill-white dark:fill-white"
              >
                <path fill="none" d="M0 0h24v24H0z" />
                <path d="M12 2a10 10 0 1 1-7.07 2.93A9.97 9.97 0 0 1 12 2zm-1 5v4H7v2h4v4h2v-4h4v-2h-4V7h-2z" />
              </svg>
            </span>
            {hasJoined ? "进入 Eason Fans Club" : "加入 Eason Fans Club"}
          </button>

          <span className="text-jacarta-600 dark:text-jacarta-300">
            参与活动、积累身份积分，并解锁属于你的链上粉丝 Badge
          </span>
        </div>
      </div>
    </section>
  );
}
