"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { Gallery, Item } from "react-photoswipe-gallery";
import type { PhotoSwipeOptions } from "photoswipe";

type ImageDimensions = {
  width: number;
  height: number;
};

const galleryOptions: PhotoSwipeOptions = {
  bgOpacity: 0.92,
  closeOnVerticalDrag: true,
  showHideAnimationType: "zoom",
  wheelToZoom: true,
  paddingFn: () => ({ top: 32, right: 24, bottom: 32, left: 24 }),
};

function CommentPhotoItem({ imageUrl, authorName, index }: { imageUrl: string; authorName: string; index: number }) {
  const [dimensions, setDimensions] = useState<ImageDimensions>({ width: 1600, height: 1200 });
  const alt = `${authorName} 的评论图片 ${index + 1}`;

  useEffect(() => {
    let cancelled = false;
    const sourceImage = new window.Image();
    sourceImage.onload = () => {
      if (!cancelled && sourceImage.naturalWidth > 0 && sourceImage.naturalHeight > 0) {
        setDimensions({ width: sourceImage.naturalWidth, height: sourceImage.naturalHeight });
      }
    };
    sourceImage.src = imageUrl;
    return () => {
      cancelled = true;
    };
  }, [imageUrl]);

  return (
    <Item<HTMLButtonElement>
      original={imageUrl}
      thumbnail={imageUrl}
      width={dimensions.width}
      height={dimensions.height}
      alt={alt}
      caption={alt}
      cropped
    >
      {({ ref, open }) => (
        <button
          ref={ref}
          type="button"
          onClick={open}
          aria-label={`大图预览：${alt}`}
          className="group relative h-[150px] w-[150px] overflow-hidden rounded-xl border border-white/10 bg-white/5 transition-all hover:-translate-y-0.5 hover:border-accent/60 hover:shadow-[0_12px_30px_rgba(5,6,25,.35)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        >
          <Image
            src={imageUrl}
            alt={alt}
            fill
            sizes="150px"
            className="object-cover transition-transform duration-300 group-hover:scale-105"
          />
        </button>
      )}
    </Item>
  );
}

export default function CommentPhotoGallery({ images, authorName }: { images: string[]; authorName: string }) {
  if (!images.length) return null;

  return (
    <Gallery options={galleryOptions} withCaption>
      <div className="mt-3 flex flex-wrap gap-2">
        {images.map((imageUrl, index) => (
          <CommentPhotoItem key={`${imageUrl}-${index}`} imageUrl={imageUrl} authorName={authorName} index={index} />
        ))}
      </div>
    </Gallery>
  );
}
