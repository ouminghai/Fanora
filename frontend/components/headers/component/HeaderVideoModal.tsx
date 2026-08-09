"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Maximize2, Volume2, VolumeX, X } from "lucide-react";
import { useBodyScrollLock } from "@/components/modals/useBodyScrollLock";

type HeaderVideoModalProps = {
  open: boolean;
  onClose: () => void;
  videoUrl: string;
};

export default function HeaderVideoModal({
  open,
  onClose,
  videoUrl,
}: HeaderVideoModalProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const frameRef = useRef<HTMLDivElement | null>(null);
  const [muted, setMuted] = useState(false);
  useBodyScrollLock(open);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  useEffect(() => {
    if (open) return;
    videoRef.current?.pause();
    if (videoRef.current) videoRef.current.currentTime = 0;
    setMuted(false);
  }, [open]);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.muted = muted;
    }
  }, [muted]);

  const fullscreenLabel = useMemo(() => "全屏播放视频", []);
  const soundLabel = muted ? "打开声音" : "关闭声音";

  const toggleMuted = () => {
    setMuted((current) => !current);
  };

  const handleFullscreen = async () => {
    const frame = frameRef.current;
    const video = videoRef.current as HTMLVideoElement & {
      webkitEnterFullscreen?: () => void;
    };

    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return;
    }

    if (frame?.requestFullscreen) {
      await frame.requestFullscreen();
      return;
    }

    if (video?.webkitEnterFullscreen) {
      video.webkitEnterFullscreen();
    }
  };

  if (!open) return null;

  return (
    <div
      role="presentation"
      className="fixed inset-0 z-[1400] flex items-center justify-center bg-black/80 px-4 py-6 backdrop-blur-sm"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-label="演示视频"
        className="relative flex w-[90vw] max-w-[1440px] flex-col overflow-hidden rounded-[20px] border border-white/10 bg-[#050816] shadow-[0_40px_140px_rgba(0,0,0,.7)]"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-white/10 px-4 py-3 text-white sm:px-5">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-cyan-200/80">
              Fanora Demo
            </p>
            <h2 className="mt-1 text-sm font-semibold text-white/90">
              演示视频
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={toggleMuted}
              aria-label={soundLabel}
              title={soundLabel}
              className="group flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 transition-colors hover:border-cyan-300/40 hover:bg-cyan-400/15"
            >
              {muted ? (
                <VolumeX className="h-4 w-4 text-white/80 transition-colors group-hover:text-white" />
              ) : (
                <Volume2 className="h-4 w-4 text-white/80 transition-colors group-hover:text-white" />
              )}
            </button>
            <button
              type="button"
              onClick={handleFullscreen}
              aria-label={fullscreenLabel}
              title={fullscreenLabel}
              className="group flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 transition-colors hover:border-cyan-300/40 hover:bg-cyan-400/15"
            >
              <Maximize2 className="h-4 w-4 text-white/80 transition-colors group-hover:text-white" />
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="关闭视频"
              title="关闭视频"
              className="group flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 transition-colors hover:border-transparent hover:bg-accent"
            >
              <X className="h-4 w-4 text-white/80 transition-colors group-hover:text-white" />
            </button>
          </div>
        </header>

        <div ref={frameRef} className="bg-black">
          <video
            ref={videoRef}
            className="block w-full bg-black"
            controls
            muted={muted}
            playsInline
            preload="metadata"
          >
            <source src={videoUrl} type="video/quicktime" />
            <source src={videoUrl} type="video/mp4" />
            你的浏览器暂不支持视频播放。
          </video>
        </div>
      </section>
    </div>
  );
}
