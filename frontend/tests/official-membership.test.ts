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
  const checkoutStyles = source("../components/membership/OfficialMembershipCheckout.module.css");
  const authProvider = source("../components/providers/AuthProvider.tsx");

  assert.match(hero, /缴纳会费正式加入/);
  assert.match(hero, /href="\/membership\/join"/);
  assert.match(missions, /user\.is_official_member/);
  assert.match(checkout, /api\.get<OfficialMembershipStatus>\("\/membership\/me"\)/);
  assert.match(checkout, /"\/membership\/verify"/);
  assert.match(authProvider, /method: "eth_sendTransaction"/);
  assert.match(authProvider, /functionName: "join"/);
  assert.match(authProvider, /paymentContractAddress/);
  assert.match(authProvider, /membershipGatewayArtifact\.abi/);
  assert.match(authProvider, /useConnectModal\(\)/);
  assert.match(authProvider, /useChainModal\(\)/);
  assert.match(authProvider, /useAccountModal\(\)/);
  assert.match(authProvider, /getWalletClient\(wagmiConfig/);
  assert.doesNotMatch(authProvider, /switchChain\(wagmiConfig/);
  assert.doesNotMatch(authProvider, /getInjectedMetaMaskProvider/);
  assert.doesNotMatch(authProvider, /wallet_requestPermissions/);
  assert.match(authProvider, /getWalletClient\(wagmiConfig/);
  assert.match(authProvider, /当前钱包与 Fanora 登录钱包不一致/);
  assert.doesNotMatch(authProvider, /instance\.connectTo\(WALLET_CONNECTORS\.METAMASK\)/);
  assert.match(checkout, /使用钱包确认支付/);
  assert.match(checkout, /fanora\.membership\.pending/);
  assert.match(checkout, /继续确认已提交的交易/);
  assert.match(checkout, /RainbowKit 直连钱包/);
  assert.doesNotMatch(checkout, /Web3Auth/);
  assert.match(checkout, /membership\.fee_mon/);
  assert.doesNotMatch(checkout, /treasuryAddress:\s*"0x[a-fA-F0-9]{40}"/);
  assert.doesNotMatch(authProvider, /to:\s*treasuryAddress/);
  assert.match(checkout, /membership\?\.fee_wei === "0"/);
  assert.match(checkout, /"\/membership\/activate-free"/);
  assert.match(checkout, /限时免费/);
  assert.match(checkout, /你的 Fanora Identity 已正式激活/);
  assert.match(checkout, /正式会员 · 已激活/);
  assert.match(checkout, /免费激活完成/);
  assert.match(checkout, /入会记录与链上交易凭证可审计/);
  assert.match(checkout, /isFree \? activateFree\(\) :/);
  assert.match(checkout, /fanora\.membership\.card\.onboarding/);
  assert.match(checkout, /const FREE_SUCCESS_CELEBRATION_MS = 4_000/);
  assert.match(checkout, /startRealisticConfetti\(FREE_SUCCESS_CELEBRATION_MS\)/);
  assert.match(checkout, /!membership\?\.is_official_member \|\| celebratedMembershipRef\.current/);
  assert.match(checkout, /const shouldRedirect = phase === "success" && membership\.fee_wei === "0"/);
  assert.match(checkout, /router\.push\("\/collection\?welcome=member-card"\)/);
  assert.match(checkout, /styles\.cyberGrid/);
  assert.match(checkout, /styles\.systemBar/);
  assert.match(checkout, /FANORA IDENTITY PROTOCOL/);
  assert.match(checkout, /styles\.primaryAction/);
  assert.match(checkout, /styles\.metricNode/);
  assert.match(checkoutStyles, /@keyframes metricIlluminate/);
  assert.match(checkoutStyles, /@keyframes metricConnect/);
  assert.match(checkoutStyles, /@keyframes metricParticle/);
  const freeActivation = checkout.slice(checkout.indexOf("const activateFree"), checkout.indexOf("if (!user || loading)"));
  assert.ok(freeActivation.indexOf("await hideGlobalProcessModal()") < freeActivation.indexOf("void refreshUser().catch"));
  assert.ok(freeActivation.indexOf("await hideGlobalProcessModal()") < freeActivation.indexOf('setPhase("success")'));
});
