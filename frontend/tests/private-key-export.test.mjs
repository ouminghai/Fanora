import assert from "node:assert/strict";
import test from "node:test";

import { requestEmbeddedPrivateKey } from "../lib/web3auth/privateKey.ts";

test("uses the Web3Auth private-key RPC supported by the auth connector", async () => {
  const provider = {
    async request({ method }) {
      if (method === "private_key") return "a".repeat(64);
      throw new Error("Method not found");
    },
  };

  const privateKey = await requestEmbeddedPrivateKey(provider);
  assert.equal(privateKey, `0x${"a".repeat(64)}`);
});
