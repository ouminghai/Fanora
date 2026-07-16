"use client";

import { badgeAbi } from "@/lib/web3/abi/badge";
import { getBadgeContractAddress } from "@/lib/web3/contracts";
import { zeroAddress } from "viem";
import { useAccount, useReadContract } from "wagmi";

export function useBadgeBalance(badgeId: bigint = 1n) {
  const { address: owner, chainId } = useAccount();
  const contractAddress = getBadgeContractAddress(chainId);

  const result = useReadContract({
    address: contractAddress ?? zeroAddress,
    abi: badgeAbi,
    functionName: "balanceOf",
    args: [owner ?? zeroAddress, badgeId],
    query: {
      enabled: Boolean(owner && contractAddress),
    },
  });

  return {
    ...result,
    contractAddress,
    isConfigured: Boolean(contractAddress),
  };
}
