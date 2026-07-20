import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import FanTokenAmount from "../components/common/FanTokenAmount";

test("fan token amounts use the shared Ethereum diamond visual", () => {
  const markup = renderToStaticMarkup(
    <FanTokenAmount amount={500} prefix="+" showSymbol />,
  );

  assert.match(markup, /data-fan-token-amount="true"/);
  assert.match(markup, /aria-label="\+500 Fan Token"/);
  assert.match(markup, /viewBox="0 0 24 36"/);
  assert.match(markup, />FAN</);
});
