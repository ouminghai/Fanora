"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Swiper, SwiperSlide } from "swiper/react";
import { Autoplay, EffectCoverflow } from "swiper/modules";
import { api } from "@/lib/api/client";
import type { CommunityPostSummary } from "@/lib/api/types";

export default function CoverFlowSlider() {
  const [posts, setPosts] = useState<CommunityPostSummary[]>([]);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => { void api.get<CommunityPostSummary[]>("/community/posts?sort=hot&limit=10").then((response) => setPosts(response.data)).catch(() => setPosts([])); }, []);
  const carouselPosts = useMemo(() => {
    if (!posts.length) return [];
    const repetitions = Math.max(1, Math.ceil(12 / posts.length));
    return Array.from({ length: repetitions }, () => posts).flat();
  }, [posts]);
  if (!carouselPosts.length) return null;

  return <div className="relative px-6 pb-10 sm:px-0"><Swiper breakpoints={{ 100: { slidesPerView: 1 }, 575: { slidesPerView: 3 }, 992: { slidesPerView: 5 } }} effect="coverflow" grabCursor centeredSlides loop={carouselPosts.length > 1} loopAdditionalSlides={5} loopPreventsSliding={false} speed={900} autoplay={{ delay: 1200, disableOnInteraction: false, pauseOnMouseEnter: true, waitForTransition: true }} coverflowEffect={{ rotate: 30, stretch: 0, depth: 100, modifier: 1, slideShadows: true }} modules={[Autoplay, EffectCoverflow]} onAfterInit={() => setIsReady(true)} className={`swiper coverflow-slider !py-5 transition-opacity duration-500 ${isReady ? "opacity-100" : "opacity-0"}`}>
    {carouselPosts.map((post, index) => { const imageUrl = post.cover_url || post.image_urls[0] || "/img/fanora/activity-community.jpg"; return <SwiperSlide key={`${post.id}-${index}`} className="h-auto"><article className="h-full"><div className="block h-full overflow-hidden rounded-2.5xl bg-white shadow-md transition-shadow hover:shadow-lg dark:bg-jacarta-700"><figure className="relative"><Link href={`/community/posts/${post.id}`}><Image src={imageUrl} alt={post.title} className="swiper-lazy h-[430px] w-full object-cover" height="430" width="379" /></Link></figure><div className="p-6"><div className="flex"><span className="shrink-0"><Image width={40} height={40} src={post.author.avatar_url || imageUrl} alt={post.author.display_name} className="mr-4 h-10 w-10 rounded-full object-cover" /></span><div className="min-w-0"><Link href={`/community/posts/${post.id}`} className="block"><span className="line-clamp-2 font-display text-lg leading-tight text-jacarta-700 hover:text-accent dark:text-white">{post.title}</span></Link><span className="mt-2 block text-2xs text-accent">{post.category}</span><span className="text-2xs text-jacarta-400 dark:text-jacarta-300">{post.reply_count} 评论 · {post.like_count} 点赞</span></div></div></div></div></article></SwiperSlide>; })}
  </Swiper></div>;
}
