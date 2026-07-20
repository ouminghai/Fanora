import assert from "node:assert/strict";
import test from "node:test";

import { api } from "../lib/api/client";

test("API requests wait up to one minute before the client times out", () => {
  assert.equal(api.defaults.timeout, 60_000);
});
