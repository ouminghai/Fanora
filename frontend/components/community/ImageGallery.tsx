"use client";

import Image from "next/image";
import { Pagination } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/react";

export default function ImageGallery({ images, alt, className = "" }: { images: string[]; alt: string; className?: string }) {
  if (!images.length) return null;
  if (images.length === 1) return <div className={`relative overflow-hidden ${className}`}><Image src={images[0]} alt={alt} fill sizes="(max-width: 1200px) 100vw, 1152px" className="object-cover" /></div>;
  return (
    <div className={`relative overflow-hidden ${className}`}>
      <Swiper modules={[Pagination]} pagination={{ clickable: true }} className="h-full w-full [--swiper-pagination-bottom:0.75rem] [--swiper-pagination-bullet-inactive-color:#fff] [--swiper-pagination-bullet-inactive-opacity:0.45] [--swiper-pagination-color:#fff]">
        {images.map((imageUrl, index) => <SwiperSlide key={imageUrl} className="relative h-full"><Image src={imageUrl} alt={`${alt} ${index + 1}`} fill sizes="(max-width: 1200px) 100vw, 1152px" className="object-cover" /></SwiperSlide>)}
      </Swiper>
    </div>
  );
}
