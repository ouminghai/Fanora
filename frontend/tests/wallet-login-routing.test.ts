import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

function source(path: string) {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

const authProvider = source("../components/providers/AuthProvider.tsx");
const loginExperience = source("../components/auth/LoginExperience.tsx");
const walletButton = source("../components/web3/RainbowWalletLoginButton.tsx");

test("uses only the wallet challenge login endpoint", () => {
  assert.match(authProvider, /api\.post<AuthSession>\("\/auth\/wallet"/);
  assert.doesNotMatch(authProvider, /web3auth/i);
  assert.match(loginExperience, /<RainbowWalletLoginButton variant="full" \/>/);
  assert.doesNotMatch(loginExperience, /web3auth/i);
});

test("opens RainbowKit modals and signs immediately after connection", () => {
  assert.match(walletButton, /useConnectModal\(\)/);
  assert.match(walletButton, /useChainModal\(\)/);
  assert.match(walletButton, /awaitingConnectionRef\.current/);
  assert.match(walletButton, /void signIn\(address\)/);
  assert.doesNotMatch(walletButton, /ConnectButton\.Custom/);
});

test("redirects wallet login directly to collection", () => {
  assert.match(loginExperience, /router\.replace\("\/collection"\)/);
  assert.doesNotMatch(loginExperience, /wallet_type/);
});
