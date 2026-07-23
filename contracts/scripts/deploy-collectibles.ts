import { ethers, network } from "hardhat";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

type DeploymentManifest = {
  network: string;
  chainId: number;
  deployedAt: string;
  deployer: string;
  admin: string;
  roles: Record<string, string>;
  contracts: {
    FanoraMembershipGateway: Record<string, unknown>;
    FanoraMembershipIdentity: Record<string, unknown>;
    FanoraCollectibles: {
      address: string;
      transactionHash?: string;
      startBlock?: number;
    };
  };
};

function requiredAddress(name: string, fallback?: string): string {
  const value = process.env[name] || fallback;
  if (!value || !ethers.isAddress(value)) {
    throw new Error(`${name} must be a valid EVM address`);
  }
  return ethers.getAddress(value);
}

async function grantRoleIfNeeded(contract: any, role: string, account: string) {
  if (!(await contract.hasRole(role, account))) {
    await (await contract.grantRole(role, account)).wait();
  }
}

async function main() {
  const manifestPath = join(__dirname, `../deployments/${network.name}.json`);
  if (!existsSync(manifestPath)) throw new Error(`Deployment manifest does not exist: ${manifestPath}`);
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as DeploymentManifest;
  const [deployer] = await ethers.getSigners();
  if (!deployer) throw new Error("DEPLOYER_PRIVATE_KEY is not configured");

  const chain = await ethers.provider.getNetwork();
  if (Number(chain.chainId) !== manifest.chainId) {
    throw new Error(`Connected chain ${chain.chainId} does not match manifest chain ${manifest.chainId}`);
  }

  const admin = requiredAddress("CONTRACT_ADMIN_ADDRESS", manifest.admin || deployer.address);
  const roles = {
    collectibleTypeManager: requiredAddress("COLLECTIBLE_TYPE_MANAGER_ADDRESS", manifest.roles.collectibleTypeManager || admin),
    collectibleMinter: requiredAddress("COLLECTIBLE_MINTER_ADDRESS", manifest.roles.collectibleMinter || admin),
    collectibleUriManager: requiredAddress("COLLECTIBLE_URI_MANAGER_ADDRESS", manifest.roles.collectibleUriManager || admin),
    collectiblePauser: requiredAddress("COLLECTIBLE_PAUSER_ADDRESS", manifest.roles.collectiblePauser || admin),
  };

  console.log(`Deploying FanoraCollectibles to ${network.name} (${chain.chainId})`);
  const collectibles = await ethers.deployContract("FanoraCollectibles", [deployer.address]);
  await collectibles.waitForDeployment();
  await grantRoleIfNeeded(collectibles, await collectibles.TOKEN_TYPE_MANAGER_ROLE(), roles.collectibleTypeManager);
  await grantRoleIfNeeded(collectibles, await collectibles.MINTER_ROLE(), roles.collectibleMinter);
  await grantRoleIfNeeded(collectibles, await collectibles.URI_MANAGER_ROLE(), roles.collectibleUriManager);
  await grantRoleIfNeeded(collectibles, await collectibles.PAUSER_ROLE(), roles.collectiblePauser);
  await grantRoleIfNeeded(collectibles, await collectibles.DEFAULT_ADMIN_ROLE(), admin);

  const receipt = await collectibles.deploymentTransaction()?.wait();
  manifest.deployedAt = new Date().toISOString();
  manifest.deployer = deployer.address;
  manifest.admin = admin;
  manifest.roles = {...manifest.roles, ...roles};
  manifest.contracts.FanoraCollectibles = {
    address: await collectibles.getAddress(),
    transactionHash: collectibles.deploymentTransaction()?.hash,
    startBlock: receipt?.blockNumber,
  };
  writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(`Collectibles deployment updated in ${manifestPath}`);
  console.log(JSON.stringify(manifest.contracts.FanoraCollectibles, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
