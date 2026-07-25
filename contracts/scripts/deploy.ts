import { ethers, network } from "hardhat";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const DEFAULT_LEVEL_RANKS = [1, 2, 3, 4, 5, 6, 100];

function requiredAddress(name: string, fallback?: string): string {
  const value = process.env[name] || fallback;
  if (!value || !ethers.isAddress(value)) {
    throw new Error(`${name} must be a valid EVM address`);
  }
  return ethers.getAddress(value);
}

function nonNegativeBigInt(name: string, fallback: bigint): bigint {
  const value = BigInt(process.env[name] || fallback.toString());
  if (value < 0n) throw new Error(`${name} must be zero or greater`);
  return value;
}

function membershipLevelRanks(): number[] {
  const configured = process.env.MEMBERSHIP_LEVEL_RANKS;
  const ranks = configured
    ? configured.split(",").map((value) => Number(value.trim()))
    : DEFAULT_LEVEL_RANKS;
  if (!ranks.length || ranks.some((rank) => !Number.isSafeInteger(rank) || rank <= 0)) {
    throw new Error("MEMBERSHIP_LEVEL_RANKS must contain positive integers separated by commas");
  }
  if (new Set(ranks).size !== ranks.length) {
    throw new Error("MEMBERSHIP_LEVEL_RANKS must not contain duplicates");
  }
  return ranks;
}

async function grantRoleIfNeeded(contract: any, role: string, account: string) {
  if (!(await contract.hasRole(role, account))) {
    await (await contract.grantRole(role, account)).wait();
  }
}

async function main() {
  const [deployer] = await ethers.getSigners();
  if (!deployer) throw new Error("DEPLOYER_PRIVATE_KEY is not configured");

  const chain = await ethers.provider.getNetwork();
  const expectedChainId = Number(process.env.MONAD_CHAIN_ID || 10143);
  if (Number(chain.chainId) !== expectedChainId) {
    throw new Error(`Connected chain ${chain.chainId} does not match MONAD_CHAIN_ID ${expectedChainId}`);
  }

  const deployerBalance = await ethers.provider.getBalance(deployer.address);
  if (deployerBalance === 0n) {
    throw new Error("The deployer wallet has no MON for contract deployment gas");
  }

  const admin = requiredAddress("CONTRACT_ADMIN_ADDRESS", deployer.address);
  const treasury = requiredAddress("MEMBERSHIP_TREASURY_ADDRESS", deployer.address);
  const fee = nonNegativeBigInt("MEMBERSHIP_FEE_WEI", ethers.parseEther("1"));
  const levelRanks = membershipLevelRanks();

  console.log(`Deploying Fanora contracts to ${network.name} (${chain.chainId})`);
  console.log(`Deployer balance: ${ethers.formatEther(deployerBalance)} MON`);

  const gateway = await ethers.deployContract("FanoraMembershipGateway", [deployer.address, treasury]);
  await gateway.waitForDeployment();
  const identity = await ethers.deployContract("FanoraMembershipIdentity", [deployer.address]);
  await identity.waitForDeployment();
  const collectibles = await ethers.deployContract("FanoraCollectibles", [deployer.address]);
  await collectibles.waitForDeployment();

  for (const rank of levelRanks) {
    await (await identity.configureMembershipLevel(rank, rank, true)).wait();
  }
  if ((await gateway.membershipFee()) !== fee) {
    await (await gateway.setMembershipFee(fee)).wait();
  }

  const roles = {
    treasuryManager: requiredAddress("TREASURY_MANAGER_ADDRESS", admin),
    gatewayPauser: requiredAddress("GATEWAY_PAUSER_ADDRESS", admin),
    identityMinter: requiredAddress("IDENTITY_MINTER_ADDRESS", admin),
    identityLevelManager: requiredAddress("IDENTITY_LEVEL_MANAGER_ADDRESS", admin),
    identityUriManager: requiredAddress("IDENTITY_URI_MANAGER_ADDRESS", admin),
    identityPauser: requiredAddress("IDENTITY_PAUSER_ADDRESS", admin),
    collectibleTypeManager: requiredAddress("COLLECTIBLE_TYPE_MANAGER_ADDRESS", admin),
    collectibleMinter: requiredAddress("COLLECTIBLE_MINTER_ADDRESS", admin),
    collectibleUriManager: requiredAddress("COLLECTIBLE_URI_MANAGER_ADDRESS", admin),
    collectiblePauser: requiredAddress("COLLECTIBLE_PAUSER_ADDRESS", admin),
  };

  const roleAssignments = [
    [gateway, await gateway.TREASURY_MANAGER_ROLE(), roles.treasuryManager],
    [gateway, await gateway.PAUSER_ROLE(), roles.gatewayPauser],
    [identity, await identity.MINTER_ROLE(), roles.identityMinter],
    [identity, await identity.LEVEL_MANAGER_ROLE(), roles.identityLevelManager],
    [identity, await identity.URI_MANAGER_ROLE(), roles.identityUriManager],
    [identity, await identity.PAUSER_ROLE(), roles.identityPauser],
    [collectibles, await collectibles.TOKEN_TYPE_MANAGER_ROLE(), roles.collectibleTypeManager],
    [collectibles, await collectibles.MINTER_ROLE(), roles.collectibleMinter],
    [collectibles, await collectibles.URI_MANAGER_ROLE(), roles.collectibleUriManager],
    [collectibles, await collectibles.PAUSER_ROLE(), roles.collectiblePauser],
  ] as const;
  for (const [contract, role, account] of roleAssignments) {
    await grantRoleIfNeeded(contract, role, account);
  }
  for (const contract of [gateway, identity, collectibles]) {
    await grantRoleIfNeeded(contract, await contract.DEFAULT_ADMIN_ROLE(), admin);
  }

  const gatewayReceipt = await gateway.deploymentTransaction()?.wait();
  const identityReceipt = await identity.deploymentTransaction()?.wait();
  const collectiblesReceipt = await collectibles.deploymentTransaction()?.wait();
  const deployment = {
    network: network.name,
    chainId: Number(chain.chainId),
    deployedAt: new Date().toISOString(),
    deployer: deployer.address,
    admin,
    treasury,
    membershipFeeWei: fee.toString(),
    membershipLevelRanks: levelRanks,
    roles,
    compiler: "0.8.28",
    contracts: {
      FanoraMembershipGateway: {
        address: await gateway.getAddress(),
        transactionHash: gateway.deploymentTransaction()?.hash,
        startBlock: gatewayReceipt?.blockNumber,
      },
      FanoraMembershipIdentity: {
        address: await identity.getAddress(),
        transactionHash: identity.deploymentTransaction()?.hash,
        startBlock: identityReceipt?.blockNumber,
      },
      FanoraCollectibles: {
        address: await collectibles.getAddress(),
        transactionHash: collectibles.deploymentTransaction()?.hash,
        startBlock: collectiblesReceipt?.blockNumber,
      },
    },
  };

  const output = join(__dirname, `../deployments/${network.name}.json`);
  mkdirSync(join(__dirname, "../deployments"), { recursive: true });
  writeFileSync(output, `${JSON.stringify(deployment, null, 2)}\n`);
  console.log(`Deployment manifest written to ${output}`);
  console.log(JSON.stringify(deployment.contracts, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
