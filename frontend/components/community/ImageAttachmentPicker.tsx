"use client";

import Image from "next/image";
import { useId, type ChangeEvent } from "react";

type ImageAttachmentPickerProps = {
  value: string[];
  onChange: (value: string[]) => void;
  onError?: (message: string) => void;
  maxImages?: number;
  compact?: boolean;
};

const acceptedTypes = ["image/jpeg", "image/png", "image/webp", "image/gif"];

export default function ImageAttachmentPicker({ value, onChange, onError, maxImages = 6, compact = false }: ImageAttachmentPickerProps) {
  const inputId = useId();

  const selectImages = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files.length) return;
    if (value.length + files.length > maxImages) {
      onError?.(`最多上传 ${maxImages} 张图片。`);
      return;
    }
    if (files.some((file) => !acceptedTypes.includes(file.type) || file.size > 1024 * 1024)) {
      onError?.("每张图片需为 1 MB 以内的 JPEG、PNG、WebP 或 GIF。 ");
      return;
    }
    try {
      const dataUrls = await Promise.all(files.map((file) => new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = () => reject(new Error("图片读取失败"));
        reader.readAsDataURL(file);
      })));
      onChange([...value, ...dataUrls]);
    } catch {
      onError?.("图片读取失败，请重新选择。 ");
    }
  };

  return (
    <div className={compact ? "mt-3" : "mt-4"}>
      <div className="flex items-center justify-between gap-3">
        <label htmlFor={inputId} className="cursor-pointer text-xs font-semibold text-accent-lighter transition-colors hover:text-white">图片</label>
        <span className="text-[11px] text-white/30">{value.length}/{maxImages} · 单张最大 1 MB</span>
      </div>
      <input id={inputId} type="file" accept="image/jpeg,image/png,image/webp,image/gif" multiple onChange={selectImages} className="sr-only" />
      <div className="mt-2 flex flex-wrap gap-2">
        {value.map((imageUrl, index) => (
          <div key={imageUrl} className="group relative h-16 w-16 overflow-hidden rounded-lg border border-white/10 bg-white/5">
            <Image src={imageUrl} alt={`待发布图片 ${index + 1}`} fill sizes="64px" className="object-cover" />
            <button type="button" aria-label={`移除图片 ${index + 1}`} onClick={() => onChange(value.filter((_, itemIndex) => itemIndex !== index))} className="absolute inset-0 bg-black/55 text-lg text-white opacity-0 transition-opacity group-hover:opacity-100">×</button>
          </div>
        ))}
        {value.length < maxImages && <label htmlFor={inputId} className="flex h-16 w-16 cursor-pointer items-center justify-center rounded-lg border border-dashed border-white/20 bg-white/[.035] text-xl text-white/45 transition-colors hover:border-accent/50 hover:text-accent-lighter">+</label>}
      </div>
    </div>
  );
}
