import { ethers } from "hardhat";

async function main() {
  const [deployer] = await ethers.getSigners();
  const baseUri = process.env.BADGE_BASE_URI || "ipfs://replace-me/{id}.json";

  const badge = await ethers.deployContract("ProofOfFandomBadge", [
    deployer.address,
    baseUri,
  ]);
  await badge.waitForDeployment();

  console.log("ProofOfFandomBadge deployed to:", await badge.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

