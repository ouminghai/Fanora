export type Bytes32Hex = `0x${string}`;

export function normalizeBytes32(value: string): Bytes32Hex {
  const normalized = value.startsWith("0x") ? value : `0x${value}`;
  if (!/^0x[0-9a-fA-F]{64}$/.test(normalized)) {
    throw new Error("入会订单编号格式无效，请刷新页面后重试。");
  }
  return normalized as Bytes32Hex;
}
