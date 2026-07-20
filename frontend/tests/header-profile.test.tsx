import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { HeaderBrand } from "../components/headers/Header3";
import { ProfileMenuPanel } from "../components/headers/component/Profile";
import type { FanoraUser } from "../lib/api/types";

const user: FanoraUser = {
  id: "user-1",
  display_name: "Fanora Tester",
  username: "fanora_tester",
  email: null,
  avatar_url: null,
  bio: null,
  locale: "zh-CN",
  level: "Silver",
  fan_token_balance: 1280,
  fan_type: "Loyal Fan",
  profile_visibility: "public",
  onboarding_completed: true,
  roles: ["fan"],
  primary_wallet: {
    address: "0x1234567890abcdef1234567890abcdef12345678",
    wallet_type: "embedded",
    provider: "web3auth",
    is_primary: true,
  },
  communities: [],
  created_at: "2026-07-20T00:00:00Z",
  updated_at: "2026-07-20T00:00:00Z",
};

test("profile menu shows wallet, Fan Token balance, fan level and account actions", () => {
  const markup = renderToStaticMarkup(<ProfileMenuPanel user={user} onClose={() => undefined} onLogout={() => undefined} />);

  assert.match(markup, /0x123456…345678/);
  assert.match(markup, /1,280/);
  assert.match(markup, /Fan Token/);
  assert.match(markup, /data-fan-token-amount="true"/);
  assert.match(markup, /Silver/);
  assert.match(markup, /href="\/profile"/);
  assert.match(markup, /My Profile/);
  assert.match(markup, /退出登录/);
});

test("header brand communicates that Fanora is built on Monad", () => {
  const markup = renderToStaticMarkup(<HeaderBrand />);

  assert.match(markup, /Fanora 与 Monad 融合构建/);
  assert.match(markup, /data-brand-blend="true"/);
  assert.match(markup, /monad-mark\.svg/);
  assert.match(markup, /monad-logo-light\.svg/);
  assert.match(markup, /monad-logo-dark\.svg/);
  assert.doesNotMatch(markup, />×</);
});
