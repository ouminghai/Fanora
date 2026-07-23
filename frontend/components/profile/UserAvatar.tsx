"use client";

import Avatar from "boring-avatars";
import React from "react";

const FANORA_AVATAR_COLORS = ["#5D32D5", "#8358FF", "#46C7FF", "#23B6A4", "#FF7A59"];

type UserAvatarProps = {
  avatarUrl?: string | null;
  seed: string;
  displayName?: string | null;
  className?: string;
};

function normalizeAvatarUrl(value?: string | null) {
  const normalized = value?.trim();
  if (!normalized || ["null", "undefined", "none"].includes(normalized.toLowerCase())) return null;
  if (
    normalized.startsWith("https://")
    || normalized.startsWith("http://")
    || normalized.startsWith("data:image/")
    || normalized.startsWith("/")
  ) {
    return normalized;
  }
  return null;
}

export default function UserAvatar({
  avatarUrl,
  seed,
  displayName,
  className = "",
}: UserAvatarProps) {
  const label = `${displayName || "Fanora 用户"}的头像`;
  const customAvatarUrl = normalizeAvatarUrl(avatarUrl);

  return (
    <span
      role="img"
      aria-label={label}
      className={`relative block shrink-0 overflow-hidden bg-accent/10 ${className}`}
    >
      <Avatar
        aria-hidden="true"
        focusable="false"
        name={seed}
        variant="beam"
        colors={FANORA_AVATAR_COLORS}
        size="100%"
        square
        className="h-full w-full"
      />
      {customAvatarUrl && (
        <span
          aria-hidden="true"
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${customAvatarUrl})` }}
        />
      )}
    </span>
  );
}
