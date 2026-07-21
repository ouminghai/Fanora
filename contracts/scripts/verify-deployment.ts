import { ethers, network } from "hardhat";
import { readFileSync } from "node:fs";
import { join } from "node:path";

type Manifest = {
  chainId: number;
  admin: string;
  treasury: string;
  membershipFeeWei: string;
  membershipLevelRanks: number[];
  roles: Record<string, string>;
  contracts: Record<string, { address: string }>;
};

async function requireCode(address: string, name: string) {
  if ((await ethers.provider.getCode(address)) === "0x") throw new Error(`${name} has no deployed bytecode`);
}

async function requireRole(contract: any, role: string, account: string, label: string) {
  if (!(await contract.hasRole(role, account))) throw new Error(`${label} is not assigned to ${account}`);
}

async function main() {
  const manifestPath = join(__dirname, `../deployments/${network.name}.json`);
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as Manifest;
  const chain = await ethers.provider.getNetwork();
  if (Number(chain.chainId) !== manifest.chainId) throw new Error("Deployment manifest chain id mismatch");

  const gatewayAddress = manifest.contracts.FanoraMembershipGateway.address;
  const identityAddress = manifest.contracts.FanoraMembershipIdentity.address;
  const collectiblesAddress = manifest.contracts.FanoraCollectibles.address;
  await requireCode(gatewayAddress, "FanoraMembershipGateway");
  await requireCode(identityAddress, "FanoraMembershipIdentity");
  await requireCode(collectiblesAddress, "FanoraCollectibles");

  const gateway = await ethers.getContractAt("FanoraMembershipGateway", gatewayAddress);
  const identity = await ethers.getContractAt("FanoraMembershipIdentity", identityAddress);
  const collectibles = await ethers.getContractAt("FanoraCollectibles", collectiblesAddress);
  if ((await gateway.treasury()).toLowerCase() !== manifest.treasury.toLowerCase()) throw new Error("Treasury mismatch");
  if ((await gateway.membershipFee()).toString() !== manifest.membershipFeeWei) throw new Error("Membership fee mismatch");

  await requireRole(gateway, await gateway.DEFAULT_ADMIN_ROLE(), manifest.admin, "Gateway admin");
  await requireRole(gateway, await gateway.TREASURY_MANAGER_ROLE(), manifest.roles.treasuryManager, "Treasury manager");
  await requireRole(gateway, await gateway.PAUSER_ROLE(), manifest.roles.gatewayPauser, "Gateway pauser");
  await requireRole(identity, await identity.DEFAULT_ADMIN_ROLE(), manifest.admin, "Identity admin");
  await requireRole(identity, await identity.MINTER_ROLE(), manifest.roles.identityMinter, "Identity minter");
  await requireRole(identity, await identity.LEVEL_MANAGER_ROLE(), manifest.roles.identityLevelManager, "Level manager");
  await requireRole(identity, await identity.URI_MANAGER_ROLE(), manifest.roles.identityUriManager, "Identity URI manager");
  await requireRole(collectibles, await collectibles.DEFAULT_ADMIN_ROLE(), manifest.admin, "Collectibles admin");
  await requireRole(collectibles, await collectibles.TOKEN_TYPE_MANAGER_ROLE(), manifest.roles.collectibleTypeManager, "Token type manager");
  await requireRole(collectibles, await collectibles.MINTER_ROLE(), manifest.roles.collectibleMinter, "Collectible minter");
  await requireRole(collectibles, await collectibles.URI_MANAGER_ROLE(), manifest.roles.collectibleUriManager, "Collectible URI manager");

  for (const rank of manifest.membershipLevelRanks) {
    const config = await identity.membershipLevels(rank);
    if (!config.exists || !config.active || Number(config.rank) !== rank) {
      throw new Error(`Membership level ${rank} is not configured correctly`);
    }
  }
  console.log(`Verified ${network.name} deployment on chain ${manifest.chainId}`);
  console.log(JSON.stringify(manifest.contracts, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
