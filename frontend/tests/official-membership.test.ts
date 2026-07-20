import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

function source(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

test("unpaid users are routed to the backend-verified 1 MON membership flow", () => {
  const hero = source("../components/homes/home/Hero.tsx");
  const missions = source("../components/homes/common/Collections.tsx");
  const checkout = source("../components/membership/OfficialMembershipCheckout.tsx");
  const authProvider = source("../components/providers/AuthProvider.tsx");

  assert.match(hero, /缴纳 1 MON 正式加入/);
  assert.match(hero, /href="\/membership\/join"/);
  assert.match(missions, /user\.is_official_member/);
  assert.match(checkout, /api\.get<OfficialMembershipStatus>\("\/membership\/me"\)/);
  assert.match(checkout, /"\/membership\/verify"/);
  assert.match(authProvider, /method: "eth_sendTransaction"/);
  assert.doesNotMatch(checkout, /treasuryAddress:\s*"0x[a-fA-F0-9]{40}"/);
});
