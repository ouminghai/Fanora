"use client";

import Link from "next/link";
import React, { useEffect, useRef } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import {
  VIDEO_SOUND_STATE_EVENT,
  VIDEO_SOUND_TOGGLE_EVENT,
  type VideoSoundDetail,
} from "@/lib/videoSound";

export default function Hero() {
  const { user, status } = useAuth();

  return <HeroView status={status} hasUser={Boolean(user)} />;
}

type HeroViewProps = {
  status: string;
  hasUser: boolean;
};

export function HeroView({ status, hasUser }: HeroViewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const showJoinButton = shouldShowHeroJoinButton(status, hasUser);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const publishSoundState = () => {
      window.dispatchEvent(
        new CustomEvent<VideoSoundDetail>(VIDEO_SOUND_STATE_EVENT, {
          detail: { muted: video.muted },
        }),
      );
    };

    const handleSoundToggle = (event: Event) => {
      const { muted } = (event as CustomEvent<VideoSoundDetail>).detail;
      video.muted = muted;

      if (muted) {
        publishSoundState();
        return;
      }

      void video
        .play()
        .then(publishSoundState)
        .catch(() => {
          video.muted = true;
          publishSoundState();
        });
    };

    video.muted = true;
    void video.play().catch(() => undefined);
    publishSoundState();

    window.addEventListener(VIDEO_SOUND_TOGGLE_EVENT, handleSoundToggle);
    video.addEventListener("volumechange", publishSoundState);

    return () => {
      window.removeEventListener(VIDEO_SOUND_TOGGLE_EVENT, handleSoundToggle);
      video.removeEventListener("volumechange", publishSoundState);
    };
  }, []);

  return (
    <section className="hero hero-parallax relative min-h-[630px] overflow-hidden md:min-h-[630px]">
      <video
        ref={videoRef}
        className="hero-parallax__media pointer-events-none absolute inset-0 -z-20 h-full w-full object-cover opacity-90"
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        poster="/img/fanora/eason-concert.webp"
        aria-hidden="true"
      >
        <source src="/video/bg.mp4" type="video/mp4" />
      </video>
      <div className="pointer-events-none absolute inset-0 -z-10 bg-white/30 dark:bg-jacarta-900/55" />
      <div className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-b from-transparent via-white/10 to-white dark:to-jacarta-900" />

      <div className="container">
        <div className="mx-auto flex min-h-[630px] max-w-5xl flex-col pb-12 pt-32 text-center md:min-h-[630px] md:pt-40">
          <h1 className="mx-auto max-w-6xl font-display text-[clamp(1.35rem,6.1vw,4.5rem)] font-bold leading-[1.08] tracking-tight text-white [text-shadow:0_3px_18px_rgba(0,0,0,0.9)]">
            <span className="block">
              <span
                data-hero-typewriter
                className="hero-typewriter hero-typewriter--1"
              >
                Now Is the Only Reality.
              </span>
            </span>
            <span className="mt-3 block">
              <span
                data-hero-typewriter
                className="hero-typewriter hero-typewriter--2"
              >
                Every Support Lives Forever.
              </span>
            </span>
          </h1>

          <div
            className="h-10 shrink-0 sm:h-12 md:h-14"
            aria-hidden="true"
          />

          <div className="mx-auto w-full max-w-2xl">
            <h2
              data-hero-reveal
              className="animate-gradient hero-reveal hero-reveal--3 mb-7 font-display text-[3.375rem] leading-tight sm:text-[4.5rem] lg:text-[5.625rem]"
            >
              Eason Fans Club
            </h2>

            {showJoinButton && <HeroJoinButton />}

            <span
              data-hero-reveal
              className="hero-reveal hero-reveal--5 inline-block text-jacarta-600 dark:text-jacarta-300"
            >
              参与活动、积累 Fan Token，并解锁属于你的链上粉丝 Badge
            </span>

          </div>
        </div>
      </div>
    </section>
  );
}

export function shouldShowHeroJoinButton(status: string, hasUser: boolean) {
  return !hasUser && (status === "anonymous" || status === "error");
}

export function HeroJoinButton() {
  return (
    <Link
      href="/login"
      data-hero-reveal
      className="hero-reveal hero-reveal--4 group relative mb-4 flex w-full items-center justify-center rounded-full bg-accent py-3 px-8 text-center font-semibold text-white shadow-accent-volume transition-all hover:-translate-y-0.5 hover:bg-accent-dark"
    >
      加入 Eason Fans Club
    </Link>
  );
}
