import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

function source(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

const authProvider = source("../components/providers/AuthProvider.tsx");
const loginExperience = source("../components/auth/LoginExperience.tsx");
const walletButton = source("../components/web3/RainbowWalletLoginButton.tsx");
const fanoraData = source("../data/fanora.ts");
const processSection = source("../components/homes/common/Process.tsx");

test("uses only the wallet challenge login endpoint", () => {
  assert.match(authProvider, /api\.post<AuthSession>\("\/auth\/wallet"/);
  assert.doesNotMatch(authProvider, /web3auth/i);
  assert.match(loginExperience, /<RainbowWalletLoginButton variant="full" \/>/);
  assert.doesNotMatch(loginExperience, /web3auth/i);
  assert.match(loginExperience, /src="\/img\/avatars\/login-icon\.jpg"/);
  assert.match(loginExperience, /src="\/img\/fanora\/login\/login-bg\.jpg"/);
  assert.match(loginExperience, /alt="Fanora 粉丝身份"/);
  assert.match(loginExperience, /styles\.stepFlow/);
  assert.match(loginExperience, /styles\.stepCard/);
  assert.match(loginExperience, /styles\.photonSecondary/);
  assert.match(loginExperience, /styles\.typewriterBrand/);
  assert.match(loginExperience, /styles\.typewriterFandom/);
  assert.match(loginExperience, /styles\.typewriterForever/);
});

test("opens RainbowKit modals and signs immediately after connection", () => {
  assert.match(walletButton, /useConnectModal\(\)/);
  assert.match(walletButton, /useChainModal\(\)/);
  assert.match(walletButton, /awaitingConnectionRef\.current/);
  assert.match(walletButton, /void signIn\(address\)/);
  assert.doesNotMatch(walletButton, /ConnectButton\.Custom/);
  assert.match(walletButton, /connector\.getProvider\(\)/);
  assert.match(walletButton, /method: "wallet_switchEthereumChain"/);
  assert.match(walletButton, /createWalletClient\(/);
  assert.doesNotMatch(walletButton, /useSignMessage/);
  assert.doesNotMatch(authProvider, /switchChain\(wagmiConfig/);
});

test("redirects wallet login directly to collection", () => {
  assert.match(loginExperience, /router\.replace\("\/collection"\)/);
  assert.doesNotMatch(loginExperience, /wallet_type/);
});

test("homepage journey describes direct wallet ownership and deterministic FAN rewards", () => {
  assert.match(fanoraData, /RainbowKit/);
  assert.match(fanoraData, /Agent 只分析画像和解释结果/);
  assert.match(processSection, /登录签名不消耗 Gas/);
  assert.match(processSection, /Fanora 不读取或保存私钥与助记词/);
  assert.doesNotMatch(fanoraData, /使用邮箱或社交账号快速加入/);
  assert.doesNotMatch(processSection, /注册流程中完成钱包创建/);
  assert.doesNotMatch(fanoraData, /Agent .*更新 Fan Token/);
});
