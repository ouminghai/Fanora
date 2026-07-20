export type Web3AuthKeyProvider = {
  request: (args: { method: string }) => Promise<unknown>;
};

export async function requestEmbeddedPrivateKey(provider: Web3AuthKeyProvider) {
  const result = await provider.request({ method: "private_key" });
  if (typeof result !== "string" || !/^(0x)?[a-fA-F0-9]{64}$/.test(result)) {
    throw new Error("Web3Auth 未返回可导出的 EVM 私钥，请检查 Dashboard 的 Key Export 设置。");
  }
  return result.startsWith("0x") ? result : `0x${result}`;
}
