import "@nomicfoundation/hardhat-toolbox";
import "dotenv/config";
import type { HardhatUserConfig } from "hardhat/config";

const privateKey = process.env.DEPLOYER_PRIVATE_KEY;

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.28",
    settings: {
      evmVersion: "cancun",
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  networks: {
    monadTestnet: {
      url: process.env.MONAD_RPC_URL || "https://testnet-rpc.monad.xyz",
      chainId: Number(process.env.MONAD_CHAIN_ID || 10143),
      accounts: privateKey ? [privateKey] : [],
    },
  },
};

export default config;
