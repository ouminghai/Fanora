import { erc1155Abi } from "viem";

// The first Fanora contract uses ERC-1155 so one contract can represent
// Bronze, Silver, Gold, and Core fan identity levels.
export const badgeAbi = erc1155Abi;
