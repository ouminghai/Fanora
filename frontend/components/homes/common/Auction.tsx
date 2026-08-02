"use client";

import axios from "axios";
import { Orbit } from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useState, type CSSProperties } from "react";
import { Swiper, SwiperSlide } from "swiper/react";
import { Autoplay, EffectCoverflow } from "swiper/modules";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import { useAuth } from "@/components/providers/AuthProvider";
import { api } from "@/lib/api/client";
import type { MembershipLevel } from "@/lib/api/types";
import { formatMembershipTokenRange, getMembershipProgress } from "@/lib/membership";
import networkStyles from "./Process.module.css";

export default function Auction() {
  const { user } = useAuth();
  const [levels, setLevels] = useState<MembershipLevel[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  const loadLevels = useCallback(async () => {
    setError(null);
    setIsReady(false);
    try {
      const response = await api.get<MembershipLevel[]>("/membership-levels");
      setLevels(response.data);
    } catch (requestError) {
      setLevels(null);
      setError(
        axios.isAxiosError(requestError)
          ? requestError.response?.data?.detail || "会员等级暂时无法读取，请确认后端服务已启动。"
          : "会员等级暂时无法读取，请稍后重试。",
      );
    }
  }, []);

  useEffect(() => {
    void loadLevels();
  }, [loadLevels]);

  return (
    <section id="badges" className={networkStyles.networkSection}>
      <div className={networkStyles.universe} aria-hidden="true">
        <div className={networkStyles.stars} />
        <div className={networkStyles.nebulaOne} />
        <div className={networkStyles.nebulaTwo} />
      </div>

      <div className={`${networkStyles.networkContainer} container`}>
        <header className={networkStyles.networkHeader}>
          <span><Orbit /> IDENTITY GROWTH NETWORK</span>
          <h2>粉丝等级与 Badge 成长</h2>
          <p>等级按历史累计获得的 FAN 成长且只升不降，消费可用余额不会影响已获得的会员身份。</p>
        </header>

        {levels === null && !error && (
          <div className="flex min-h-72 items-center justify-center rounded-3xl border border-white/10 bg-black/10 text-white/75 backdrop-blur-sm">
            <span className="mr-3 h-5 w-5 animate-spin rounded-full border-2 border-white/25 border-t-white" />

          </div>
        )}

        {error && (
          <div className="mx-auto flex min-h-64 max-w-xl flex-col items-center justify-center rounded-3xl border border-red/20 bg-black/20 px-8 text-center text-white backdrop-blur-sm">
            <p className="leading-7 text-white/80">{error}</p>
            <button
              type="button"
              onClick={() => void loadLevels()}
              className="mt-5 rounded-full bg-white px-6 py-2.5 text-sm font-semibold text-jacarta-700 transition-transform hover:-translate-y-0.5"
            >
              重新读取
            </button>
          </div>
        )}

        {levels && (
          <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 sm:px-8">
            <div
              className={`badge-slider-reveal relative pb-5 ${
                isReady ? "is-ready" : ""
              }`}
            >
              <Swiper
                breakpoints={{
                  100: {
                    slidesPerView: 1,
                  },
                  575: {
                    slidesPerView: 2,
                  },
                  992: {
                    slidesPerView: 6,
                  },
                }}
                effect={"coverflow"}
                grabCursor
                loop
                speed={900}
                autoplay={{
                  delay: 1200,
                  disableOnInteraction: false,
                  pauseOnMouseEnter: true,
                  waitForTransition: true,
                }}
                coverflowEffect={{
                  rotate: 15,
                  stretch: 0,
                  depth: 100,
                  modifier: 1,
                  slideShadows: true,
                }}
                modules={[Autoplay, EffectCoverflow]}
                onAfterInit={() => setIsReady(true)}
                className={`swiper badge-level-slider coverflow-slider !overflow-visible !py-6 transition-opacity duration-500 ${
                  isReady ? "opacity-100" : "opacity-0"
                }`}
                aria-label="粉丝等级与 Badge 自动轮播"
              >
                {levels.map((level, index) => (
                  <SwiperSlide key={level.code} className="!h-auto">
                    <article
                      className={`badge-level-card-reveal h-full ${isReady ? "is-visible" : ""}`}
                      style={
                        {
                          "--badge-reveal-delay": `${Math.min(index, 5) * 85}ms`,
                        } as CSSProperties
                      }
                    >
                      <div className="animate-gradient--no-text-fill block h-full animate-gradient overflow-hidden rounded-2.5xl !bg-clip-border p-[2px] shadow-xl shadow-black/20 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl">
                        <div className="flex h-full flex-col rounded-[1.125rem] bg-jacarta-900 p-5">
                          <div className="mb-4 flex items-center justify-between gap-2">
                            <span className="whitespace-nowrap rounded-full bg-white/10 py-1 px-3 text-2xs font-semibold text-white backdrop-blur">
                              {level.is_management ? "管理身份" : `Lv.${level.rank} ${level.name}`}
                            </span>
                            <span className="text-2xs text-jacarta-300">动态身份凭证</span>
                          </div>

                          <figure className="relative overflow-hidden rounded-2lg bg-jacarta-800">
                            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_42%,rgba(131,88,255,.35),transparent_68%)]" />
                            <Image
                              width={300}
                              height={300}
                              src={level.badge_image_url}
                              alt={`${level.name} Badge`}
                              className="swiper-lazy relative aspect-square w-full object-cover transition-transform duration-500 hover:scale-[1.03]"
                              loading="lazy"
                            />
                            <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center justify-center rounded-full bg-white py-2.5 px-5 text-2xs font-semibold whitespace-nowrap text-jacarta-700 shadow-lg">
                              {getMembershipProgress(
                                level,
                                user?.fan_token_lifetime_earned ?? null,
                                user?.level ?? null,
                                user ? user.is_official_member : null,
                              )}
                            </div>
                          </figure>

                          <div className="relative mt-5 flex flex-1 flex-col rounded-2lg bg-jacarta-700/90 p-5">
                            <div className="flex items-center justify-between gap-3">
                              <h3 className="whitespace-nowrap font-display text-lg font-semibold leading-tight text-white">
                                {level.name} Badge
                              </h3>
                              <span className="rounded-md border border-accent/40 py-1 px-2 text-2xs font-semibold text-accent-lighter">
                                SBT
                              </span>
                            </div>

                            <div className="mt-3 text-sm text-jacarta-200">
                              <span>升级门槛：</span>{" "}
                              <span className="font-semibold text-white">
                                {level.is_management ? (
                                  formatMembershipTokenRange(level)
                                ) : (
                                  <FanTokenAmount
                                    amount={formatMembershipTokenRange(level)}
                                    showSymbol
                                  />
                                )}
                              </span>
                            </div>

                            <div className="mt-auto flex items-center justify-between gap-3 border-t border-white/10 pt-4 text-sm">
                              <span className="font-display font-semibold text-accent-lighter">
                                {level.description}
                              </span>
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 24 24"
                                width="24"
                                height="24"
                                className="h-4 w-4 shrink-0 fill-white/70"
                              >
                                <path fill="none" d="M0 0h24v24H0z" />
                                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 21 12 17.77 5.82 21 7 14.14l-5-4.87 6.91-1.01L12 2z" />
                              </svg>
                            </div>
                          </div>
                        </div>
                      </div>
                    </article>
                  </SwiperSlide>
                ))}
              </Swiper>
            </div>
          </div>
        )}

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
