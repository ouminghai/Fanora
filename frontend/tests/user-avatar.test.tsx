import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import UserAvatar from "../components/profile/UserAvatar";

test("renders a generated SVG when avatarUrl is blank", () => {
  const markup = renderToStaticMarkup(
    <UserAvatar avatarUrl=" " seed="test-user-id" displayName="Test User" className="h-24 w-24" />,
  );

  assert.match(markup, /<svg/);
});

test("keeps the generated SVG behind a custom avatar", () => {
  const markup = renderToStaticMarkup(
    <UserAvatar
      avatarUrl="https://example.com/avatar.png"
      seed="test-user-id"
      displayName="Test User"
      className="h-24 w-24"
    />,
  );

  assert.match(markup, /<svg/);
  assert.match(markup, /background-image:url\(https:\/\/example\.com\/avatar\.png\)/);
});
