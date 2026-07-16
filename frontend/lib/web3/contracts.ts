import { isAddress, type Address } from "viem";
import { monad, monadTestnet } from "wagmi/chains";

const addresses: Partial<Record<number, string | undefined>> = {
  [monadTestnet.id]:
    process.env.NEXT_PUBLIC_BADGE_CONTRACT_ADDRESS_MONAD_TESTNET,
  [monad.id]: process.env.NEXT_PUBLIC_BADGE_CONTRACT_ADDRESS_MONAD,
};

export function getBadgeContractAddress(
  chainId?: number,
): Address | undefined {
  if (!chainId) return undefined;

  const address = addresses[chainId];
  return address && isAddress(address) ? address : undefined;
}
