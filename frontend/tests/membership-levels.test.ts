import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import type { MembershipLevel } from "../lib/api/types";
import { formatMembershipTokenRange, getMembershipProgress } from "../lib/membership";

const level: MembershipLevel = {
  code: "moderate-neuro",
  name: "中度神经",
  description: "开始活跃发帖、签到",
  rank: 3,
  min_token_balance: 500,
  max_token_balance: 1499,
  badge_image_url: "/img/badges/moderate.png",
  is_management: false,
};

test("membership presentation uses lifetime FAN threshold fields", () => {
  assert.equal(formatMembershipTokenRange(level), "500 - 1,499");
  assert.equal(getMembershipProgress(level, 120, "轻度神经"), "还差 380 FAN");
  assert.equal(getMembershipProgress(level, 600, "中度神经"), "当前等级");
  assert.equal(getMembershipProgress(level, 2000, "重度神经"), "已达到");
  assert.equal(
    getMembershipProgress(level, 0, "待入会", false),
    "缴纳 1 MON 后解锁",
  );
});

test("membership levels use the database-backed animated autoplay slider", () => {
  const source = readFileSync(
    new URL("../components/homes/common/Auction.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /api\.get<MembershipLevel\[]>\("\/membership-levels"\)/);
  assert.match(source, /modules=\{\[Autoplay, EffectCoverflow\]\}/);
  assert.match(source, /autoplay=\{\{/);
  assert.match(source, /575:\s*\{\s*slidesPerView: 2,/);
  assert.match(source, /992:\s*\{\s*slidesPerView: 6,/);
  assert.match(source, /user\?\.fan_token_lifetime_earned \?\? null/);
  assert.match(source, /delay: 1200,/);
  assert.match(source, /\sloop\s/);
  assert.match(source, /const \[isReady, setIsReady\] = useState\(false\)/);
  assert.match(source, /onAfterInit=\{\(\) => setIsReady\(true\)\}/);
  assert.match(source, /transition-opacity duration-500/);
  assert.match(source, /isReady \? "opacity-100" : "opacity-0"/);
  assert.match(source, /animate-gradient--no-text-fill/);
  assert.match(source, /badge-level-card-reveal/);
  assert.match(source, /IDENTITY GROWTH NETWORK/);
  assert.match(source, /networkStyles\.universe/);
  assert.match(source, /networkStyles\.stars/);
  assert.match(source, /networkStyles\.nebulaOne/);
  assert.doesNotMatch(source, /badgeLevels/);
  assert.doesNotMatch(source, /\[\.\.\.levels, \.\.\.levels\]/);
});
