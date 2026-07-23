import type { MembershipLevel } from "@/lib/api/types";

export function formatMembershipTokenRange(level: MembershipLevel) {
  if (level.is_management || level.min_token_balance === null) {
    return "非 Token 自动获得";
  }
  const minimum = level.min_token_balance.toLocaleString("en-US");
  if (level.max_token_balance === null) return `${minimum}+`;
  return `${minimum} - ${level.max_token_balance.toLocaleString("en-US")}`;
}

export function getMembershipProgress(
  level: MembershipLevel,
  fanTokenLifetimeEarned: number | null,
  currentLevel: string | null,
  isOfficialMember: boolean | null = true,
) {
  if (fanTokenLifetimeEarned === null || isOfficialMember === null) return "登录后查看进度";
  if (!isOfficialMember) return "缴纳 1 MON 后解锁";
  if (currentLevel === level.name) return "当前等级";
  if (level.is_management || level.min_token_balance === null) return "管理身份";
  if (fanTokenLifetimeEarned >= level.min_token_balance) return "已达到";
  return `还差 ${(level.min_token_balance - fanTokenLifetimeEarned).toLocaleString("en-US")} FAN`;
}
