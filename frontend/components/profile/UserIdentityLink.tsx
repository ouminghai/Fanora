"use client";

import Image from "next/image";
import Link from "next/link";
import { createPortal } from "react-dom";
import { useCallback, useEffect, useRef, useState } from "react";
import FanTokenAmount from "@/components/common/FanTokenAmount";
import UserAvatar from "@/components/profile/UserAvatar";
import { api } from "@/lib/api/client";
import type { CommunityAuthor, PublicCollection } from "@/lib/api/types";

const publicCollectionCache = new Map<string, Promise<PublicCollection>>();

function loadPublicCollection(userId: string) {
  const cached = publicCollectionCache.get(userId);
  if (cached) return cached;
  const request = api.get<PublicCollection>(`/nft/users/${userId}`).then((response) => response.data);
  publicCollectionCache.set(userId, request);
  return request;
}

export default function UserIdentityLink({
  author,
  avatarClassName = "h-8 w-8 rounded-full",
  nameClassName = "text-sm font-semibold",
  showName = true,
  compact = false,
}: {
  author: CommunityAuthor;
  avatarClassName?: string;
  nameClassName?: string;
  showName?: boolean;
  compact?: boolean;
}) {
  const [collection, setCollection] = useState<PublicCollection | null>(null);
  const [failed, setFailed] = useState(false);
  const [cardVisible, setCardVisible] = useState(false);
  const [cardPosition, setCardPosition] = useState({ left: 12, top: 12, width: 288 });
  const triggerRef = useRef<HTMLSpanElement | null>(null);
  const href = `/users/${author.id}`;
  const primeCard = useCallback(() => {
    if (collection || failed) return;
    void loadPublicCollection(author.id)
      .then(setCollection)
      .catch(() => setFailed(true));
  }, [author.id, collection, failed]);
  const identity = collection?.identity;
  const cardImage = identity?.is_member_card && identity.image_url ? identity.image_url : "/img/membercard/membercard.jpg";
  const displayName = collection?.user.display_name || author.display_name;
  const level = collection?.user.level || author.level;

  const positionCard = useCallback(() => {
    const trigger = triggerRef.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const margin = 12;
    const gap = 10;
    const footerHeight = 82;
    const availableHeight = Math.max(480, window.innerHeight - margin * 2);
    const widthFromHeight = (availableHeight - footerHeight) * (421 / 734);
    const width = Math.min(288, window.innerWidth - margin * 2, Math.max(220, widthFromHeight));
    const cardHeight = width * (734 / 421) + footerHeight;
    const preferredLeft = rect.left + (compact ? -8 : 0);
    const left = Math.min(Math.max(margin, preferredLeft), window.innerWidth - width - margin);
    const below = rect.bottom + gap;
    const top = below + cardHeight <= window.innerHeight - margin
      ? below
      : Math.max(margin, rect.top - gap - cardHeight);
    setCardPosition({ left, top, width });
  }, [compact]);

  useEffect(() => {
    if (!cardVisible) return;
    positionCard();
    const update = () => positionCard();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [cardVisible, positionCard]);

  const revealCard = () => {
    primeCard();
    positionCard();
    setCardVisible(true);
  };

  const card = cardVisible && typeof document !== "undefined" ? createPortal(
    <span
      className="pointer-events-none fixed z-[1600] block overflow-hidden rounded-lg border border-white/12 bg-[#101436] text-left text-white opacity-100 shadow-[0_28px_90px_rgba(0,0,0,.55)]"
      style={{ left: cardPosition.left, top: cardPosition.top, width: cardPosition.width }}
      role="status"
      aria-label={`${displayName} 的 Fanora 会员证`}
    >
      <span className="relative block aspect-[421/734] w-full bg-[#080a20]">
        <Image fill unoptimized src={cardImage} alt={`${displayName} Fanora 会员证`} sizes="288px" className="object-cover" />
        <span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-4">
          <span className="block font-display text-lg font-semibold">{displayName}</span>
          <span className="mt-1 block text-xs text-white/70">{level}</span>
        </span>
      </span>
      <span className="grid grid-cols-3 gap-2 p-3 text-center">
        <span className="rounded-md bg-white/[.06] px-2 py-2">
          <span className="block text-[10px] text-white/45">累计 FAN</span>
          <FanTokenAmount amount={collection?.user.fan_token_lifetime_earned || 0} className="mt-1 justify-center text-xs font-semibold text-accent-lighter" />
        </span>
        <span className="rounded-md bg-white/[.06] px-2 py-2">
          <span className="block text-[10px] text-white/45">收藏</span>
          <span className="mt-1 block text-xs font-semibold">{collection?.collectibles.length ?? "--"}</span>
        </span>
        <span className="rounded-md bg-white/[.06] px-2 py-2">
          <span className="block text-[10px] text-white/45">创作</span>
          <span className="mt-1 block text-xs font-semibold">{collection?.creations.length ?? "--"}</span>
        </span>
      </span>
    </span>,
    document.body,
  ) : null;

  return (
    <span
      ref={triggerRef}
      className="group/user relative inline-flex min-w-0 items-center gap-2"
      onMouseEnter={revealCard}
      onMouseLeave={() => setCardVisible(false)}
      onFocus={revealCard}
      onBlur={() => setCardVisible(false)}
    >
      <Link href={href} className="inline-flex min-w-0 items-center gap-2 text-inherit">
        <UserAvatar avatarUrl={author.avatar_url} seed={author.id} displayName={author.display_name} className={avatarClassName} />
        {showName ? <span className={`min-w-0 truncate transition-colors group-hover/user:text-accent ${nameClassName}`}>{author.display_name}</span> : null}
      </Link>
      {card}
    </span>
  );
}
