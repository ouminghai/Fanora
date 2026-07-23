import { ethers, network } from "hardhat";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const DEFAULT_LEVEL_RANKS = [1, 2, 3, 4, 5, 6, 100];

type DeploymentManifest = {
  network: string;
  chainId: number;
  deployedAt: string;
  deployer: string;
  admin: string;
  membershipLevelRanks?: number[];
  roles: Record<string, string>;
  contracts: {
    FanoraMembershipGateway: Record<string, unknown>;
    FanoraMembershipIdentity: {
      address: string;
      transactionHash?: string;
      startBlock?: number;
    };
    FanoraCollectibles: Record<string, unknown>;
  };
};

function requiredAddress(name: string, fallback?: string): string {
  const value = process.env[name] || fallback;
  if (!value || !ethers.isAddress(value)) {
    throw new Error(`${name} must be a valid EVM address`);
  }
  return ethers.getAddress(value);
}

function membershipLevelRanks(manifest: DeploymentManifest): number[] {
  const configured = process.env.MEMBERSHIP_LEVEL_RANKS;
  const ranks = configured
    ? configured.split(",").map((value) => Number(value.trim()))
    : manifest.membershipLevelRanks || DEFAULT_LEVEL_RANKS;
  if (!ranks.length || ranks.some((rank) => !Number.isSafeInteger(rank) || rank <= 0)) {
    throw new Error("MEMBERSHIP_LEVEL_RANKS must contain positive integers separated by commas");
  }
  return ranks;
}

async function grantRoleIfNeeded(contract: any, role: string, account: string) {
  if (!(await contract.hasRole(role, account))) {
    await (await contract.grantRole(role, account)).wait();
  }
}

async function main() {
  const manifestPath = join(__dirname, `../deployments/${network.name}.json`);
  if (!existsSync(manifestPath)) {
    throw new Error(`Deployment manifest does not exist: ${manifestPath}`);
  }
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as DeploymentManifest;
  const [deployer] = await ethers.getSigners();
  if (!deployer) throw new Error("DEPLOYER_PRIVATE_KEY is not configured");

  const chain = await ethers.provider.getNetwork();
  if (Number(chain.chainId) !== manifest.chainId) {
    throw new Error(`Connected chain ${chain.chainId} does not match manifest chain ${manifest.chainId}`);
  }

  const admin = requiredAddress("CONTRACT_ADMIN_ADDRESS", manifest.admin || deployer.address);
  const roles = {
    identityMinter: requiredAddress("IDENTITY_MINTER_ADDRESS", manifest.roles.identityMinter || admin),
    identityLevelManager: requiredAddress(
      "IDENTITY_LEVEL_MANAGER_ADDRESS",
      manifest.roles.identityLevelManager || admin,
    ),
    identityUriManager: requiredAddress("IDENTITY_URI_MANAGER_ADDRESS", manifest.roles.identityUriManager || admin),
    identityPauser: requiredAddress("IDENTITY_PAUSER_ADDRESS", manifest.roles.identityPauser || admin),
  };

  console.log(`Deploying FanoraMembershipIdentity to ${network.name} (${chain.chainId})`);
  const identity = await ethers.deployContract("FanoraMembershipIdentity", [deployer.address]);
  await identity.waitForDeployment();

  for (const rank of membershipLevelRanks(manifest)) {
    await (await identity.configureMembershipLevel(rank, rank, true)).wait();
  }

  await grantRoleIfNeeded(identity, await identity.MINTER_ROLE(), roles.identityMinter);
  await grantRoleIfNeeded(identity, await identity.LEVEL_MANAGER_ROLE(), roles.identityLevelManager);
  await grantRoleIfNeeded(identity, await identity.URI_MANAGER_ROLE(), roles.identityUriManager);
  await grantRoleIfNeeded(identity, await identity.PAUSER_ROLE(), roles.identityPauser);
  await grantRoleIfNeeded(identity, await identity.DEFAULT_ADMIN_ROLE(), admin);

  const receipt = await identity.deploymentTransaction()?.wait();
  manifest.deployedAt = new Date().toISOString();
  manifest.deployer = deployer.address;
  manifest.admin = admin;
  manifest.roles = {...manifest.roles, ...roles};
  manifest.contracts.FanoraMembershipIdentity = {
    address: await identity.getAddress(),
    transactionHash: identity.deploymentTransaction()?.hash,
    startBlock: receipt?.blockNumber,
  };
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(`Identity deployment updated in ${manifestPath}`);
  console.log(JSON.stringify(manifest.contracts.FanoraMembershipIdentity, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
