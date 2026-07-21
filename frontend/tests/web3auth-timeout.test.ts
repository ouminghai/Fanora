import assert from "node:assert/strict";
import test from "node:test";

import {
  Web3AuthTimeoutError,
  withWeb3AuthTimeout,
} from "../lib/web3auth/timeout";

test("rejects Web3Auth operations that do not settle", async () => {
  await assert.rejects(
    withWeb3AuthTimeout(new Promise(() => undefined), 5),
    Web3AuthTimeoutError,
  );
});

test("returns Web3Auth operations that finish before the timeout", async () => {
  const result = await withWeb3AuthTimeout(Promise.resolve("connected"), 50);

  assert.equal(result, "connected");
});
