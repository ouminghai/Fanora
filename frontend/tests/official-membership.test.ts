import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

function source(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

test("unpaid users are routed to the backend-verified membership fee flow", () => {
  const hero = source("../components/homes/home/Hero.tsx");
  const missions = source("../components/homes/common/Collections.tsx");
  const checkout = source("../components/membership/OfficialMembershipCheckout.tsx");
  const authProvider = source("../components/providers/AuthProvider.tsx");

  assert.match(hero, /缴纳会费正式加入/);
  assert.match(hero, /href="\/membership\/join"/);
  assert.match(missions, /user\.is_official_member/);
  assert.match(checkout, /api\.get<OfficialMembershipStatus>\("\/membership\/me"\)/);
  assert.match(checkout, /"\/membership\/verify"/);
  assert.match(authProvider, /method: "eth_sendTransaction"/);
  assert.match(authProvider, /connectorName !== "metamask"/);
  assert.match(authProvider, /wallet_type !== "external"/);
  assert.match(authProvider, /functionName: "join"/);
  assert.match(authProvider, /paymentContractAddress/);
  assert.match(authProvider, /membershipGatewayArtifact\.abi/);
  assert.match(checkout, /使用 MetaMask 确认支付/);
  assert.match(checkout, /membership\.fee_mon/);
  assert.doesNotMatch(checkout, /treasuryAddress:\s*"0x[a-fA-F0-9]{40}"/);
  assert.doesNotMatch(authProvider, /to:\s*treasuryAddress/);
});
