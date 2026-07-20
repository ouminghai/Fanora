"use client";
import { useState } from "react";
import { Swiper, SwiperSlide } from "swiper/react";
import { Autoplay, EffectCoverflow } from "swiper/modules";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import { recentActivities } from "@/data/fanora";
import Image from "next/image";

const carouselActivities =
  recentActivities.length > 5
    ? recentActivities
    : [...recentActivities, ...recentActivities];

export default function CoverFlowSlider() {
  const [isReady, setIsReady] = useState(false);

  return (
    <div className="relative px-6 pb-10 sm:px-0">
      <Swiper
        breakpoints={{
          // when window width is >= 640px
          100: {
            // width: 640,
            slidesPerView: 1,
          },
          575: {
            // width: 640,
            slidesPerView: 3,
          },
          // when window width is >= 768px
          992: {
            // width: 768,
            slidesPerView: 5,
          },
        }}
        effect={"coverflow"}
        grabCursor={true}
        centeredSlides={true}
        loop={true}
        speed={900}
        autoplay={{
          delay: 1200,
          disableOnInteraction: false,
          pauseOnMouseEnter: true,
          waitForTransition: true,
        }}
        coverflowEffect={{
          rotate: 30,
          stretch: 0,
          depth: 100,
          modifier: 1,
          slideShadows: true,
        }}
        modules={[Autoplay, EffectCoverflow]}
        onAfterInit={() => setIsReady(true)}
        className={`swiper coverflow-slider !py-5 transition-opacity duration-500 ${
          isReady ? "opacity-100" : "opacity-0"
        }`}
      >
        {carouselActivities.map((elm, index) => (
          <SwiperSlide key={`${elm.id}-${index}`}>
            <article>
              <div className="block overflow-hidden rounded-2.5xl bg-white shadow-md transition-shadow hover:shadow-lg dark:bg-jacarta-700">
                <figure className="relative">
                  <a href="#missions">
                    <Image
                      src={elm.imageSrc}
                      alt={elm.title}
                      className="swiper-lazy h-[430px] w-full object-cover"
                      height="430"
                      width="379"
                    />
                    {/* <div className="swiper-lazy-preloader"></div> */}
                  </a>
                </figure>
                <div className="p-6">
                  <div className="flex">
                    <span className="shrink-0">
                      <Image
                        width={40}
                        height={40}
                        src={elm.avatarSrc}
                        alt="Eason Fans Club"
                        className="mr-4 h-10 w-10 rounded-full"
                      />
                    </span>
                    <div>
                      <a href="#missions" className="block">
                        <span className="font-display text-lg leading-none text-jacarta-700 hover:text-accent dark:text-white">
                          {elm.title}
                        </span>
                      </a>
                      <span className="block text-2xs text-accent">
                        {elm.meta}
                      </span>
                      {elm.fanTokenReward !== null ? (
                        <FanTokenAmount
                          amount={elm.fanTokenReward}
                          prefix="+"
                          className="text-2xs text-jacarta-400 dark:text-jacarta-300"
                        />
                      ) : (
                        <span className="text-2xs text-jacarta-400 dark:text-jacarta-300">
                          {elm.rewardLabel}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </article>
          </SwiperSlide>
        ))}
      </Swiper>
    </div>
  );
}
