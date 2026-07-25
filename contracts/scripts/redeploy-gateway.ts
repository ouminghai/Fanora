import { ethers, network } from "hardhat";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

type ContractDeployment = {
  address: string;
  transactionHash?: string;
  startBlock?: number;
};

type DeploymentManifest = {
  network: string;
  chainId: number;
  deployedAt: string;
  deployer: string;
  admin: string;
  treasury: string;
  membershipFeeWei: string;
  membershipLevelRanks: number[];
  roles: Record<string, string>;
  compiler: string;
  contracts: {
    FanoraMembershipGateway: ContractDeployment;
    FanoraMembershipIdentity: ContractDeployment;
    FanoraCollectibles: ContractDeployment;
  };
};

function requiredAddress(name: string, fallback?: string): string {
  const value = process.env[name] || fallback;
  if (!value || !ethers.isAddress(value)) throw new Error(`${name} must be a valid EVM address`);
  return ethers.getAddress(value);
}

function nonNegativeFee(): bigint {
  const value = BigInt(process.env.MEMBERSHIP_FEE_WEI || "0");
  if (value < 0n) throw new Error("MEMBERSHIP_FEE_WEI must be zero or greater");
  return value;
}

async function grantRoleIfNeeded(contract: any, role: string, account: string) {
  if (!(await contract.hasRole(role, account))) await (await contract.grantRole(role, account)).wait();
}

async function main() {
  const manifestPath = join(__dirname, `../deployments/${network.name}.json`);
  const previous = JSON.parse(readFileSync(manifestPath, "utf8")) as DeploymentManifest;
  const [deployer] = await ethers.getSigners();
  if (!deployer) throw new Error("DEPLOYER_PRIVATE_KEY is not configured");

  const chain = await ethers.provider.getNetwork();
  const expectedChainId = Number(process.env.MONAD_CHAIN_ID || previous.chainId);
  if (Number(chain.chainId) !== expectedChainId) {
    throw new Error(`Connected chain ${chain.chainId} does not match MONAD_CHAIN_ID ${expectedChainId}`);
  }
  if ((await ethers.provider.getBalance(deployer.address)) === 0n) {
    throw new Error("The deployer wallet has no MON for contract deployment gas");
  }

  const admin = requiredAddress("CONTRACT_ADMIN_ADDRESS", previous.admin || deployer.address);
  const treasury = requiredAddress("MEMBERSHIP_TREASURY_ADDRESS", previous.treasury);
  const treasuryManager = requiredAddress(
    "TREASURY_MANAGER_ADDRESS",
    previous.roles.treasuryManager || admin,
  );
  const gatewayPauser = requiredAddress("GATEWAY_PAUSER_ADDRESS", previous.roles.gatewayPauser || admin);
  const fee = nonNegativeFee();

  const gateway = await ethers.deployContract("FanoraMembershipGateway", [deployer.address, treasury]);
  await gateway.waitForDeployment();
  if ((await gateway.membershipFee()) !== fee) await (await gateway.setMembershipFee(fee)).wait();
  await grantRoleIfNeeded(gateway, await gateway.TREASURY_MANAGER_ROLE(), treasuryManager);
  await grantRoleIfNeeded(gateway, await gateway.PAUSER_ROLE(), gatewayPauser);
  await grantRoleIfNeeded(gateway, await gateway.DEFAULT_ADMIN_ROLE(), admin);

  const receipt = await gateway.deploymentTransaction()?.wait();
  const next: DeploymentManifest = {
    ...previous,
    network: network.name,
    chainId: Number(chain.chainId),
    deployedAt: new Date().toISOString(),
    deployer: deployer.address,
    admin,
    treasury,
    membershipFeeWei: fee.toString(),
    roles: { ...previous.roles, treasuryManager, gatewayPauser },
    contracts: {
      ...previous.contracts,
      FanoraMembershipGateway: {
        address: await gateway.getAddress(),
        transactionHash: gateway.deploymentTransaction()?.hash,
        startBlock: receipt?.blockNumber,
      },
    },
  };
  writeFileSync(manifestPath, `${JSON.stringify(next, null, 2)}\n`);
  console.log(`FanoraMembershipGateway deployed: ${next.contracts.FanoraMembershipGateway.address}`);
  console.log(`Membership fee: ${next.membershipFeeWei} wei`);
  console.log(`Deployment manifest updated: ${manifestPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
