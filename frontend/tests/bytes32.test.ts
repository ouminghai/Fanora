import assert from "node:assert/strict";
import test from "node:test";
import { encodeFunctionData } from "viem";
import membershipGatewayArtifact from "../../shared/contracts/FanoraMembershipGateway.json";
import { normalizeBytes32 } from "../lib/web3/bytes";

const rawPaymentId = "b1002f89a11fa86abe0caec3c774f31f7ffd0712bbd9942c48cc25364f28ad77";

test("normalizes a backend payment id before encoding join(bytes32)", () => {
  const paymentId = normalizeBytes32(rawPaymentId);
  const data = encodeFunctionData({
    abi: membershipGatewayArtifact.abi,
    functionName: "join",
    args: [paymentId],
  });

  assert.equal(paymentId, `0x${rawPaymentId}`);
  assert.match(data, /^0x[0-9a-f]+$/i);
});

test("rejects malformed payment ids before opening the wallet", () => {
  assert.throws(() => normalizeBytes32("not-a-payment-id"), /订单编号格式无效/);
});
