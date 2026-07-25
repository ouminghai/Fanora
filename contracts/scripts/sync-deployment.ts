import "dotenv/config";
import { Wallet } from "ethers";
import { copyFileSync, existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";

type ContractDeployment = { address: string; startBlock: number };
type DeploymentManifest = {
  network: string;
  chainId: number;
  deployer: string;
  treasury: string;
  membershipFeeWei: string;
  roles: Record<string, string>;
  contracts: {
    FanoraMembershipGateway: ContractDeployment;
    FanoraMembershipIdentity: ContractDeployment;
    FanoraCollectibles: ContractDeployment;
  };
};

const contractsRoot = resolve(__dirname, "..");
const workspaceRoot = resolve(contractsRoot, "..");
const contractNames = ["FanoraMembershipGateway", "FanoraMembershipIdentity", "FanoraCollectibles"];

function updateEnvFile(path: string, updates: Record<string, string>) {
  if (!existsSync(path)) throw new Error(`Environment file does not exist: ${path}`);
  const lines = readFileSync(path, "utf8").split(/\r?\n/);
  const remaining = new Map(Object.entries(updates));
  const next = lines.map((line) => {
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*)=/);
    if (!match || !remaining.has(match[1])) return line;
    const value = remaining.get(match[1])!;
    remaining.delete(match[1]);
    return `${match[1]}=${value}`;
  });
  if (remaining.size) {
    if (next.at(-1) !== "") next.push("");
    next.push("# 由 contracts 发布脚本自动同步");
    for (const [key, value] of remaining) next.push(`${key}=${value}`);
  }
  const temporary = `${path}.fanora-sync`;
  writeFileSync(temporary, `${next.join("\n").replace(/\n+$/, "")}\n`, { mode: 0o600 });
  renameSync(temporary, path);
}

function privateKeyUpdates(manifest: DeploymentManifest): Record<string, string> {
  const privateKey = process.env.DEPLOYER_PRIVATE_KEY;
  if (!privateKey) throw new Error("DEPLOYER_PRIVATE_KEY is required for operator-key synchronization");
  const deployer = new Wallet(privateKey).address.toLowerCase();
  const mappings: Array<[string, string]> = [
    ["MEMBERSHIP_TREASURY_MANAGER_PRIVATE_KEY", "treasuryManager"],
    ["IDENTITY_MINTER_PRIVATE_KEY", "identityMinter"],
    ["IDENTITY_LEVEL_MANAGER_PRIVATE_KEY", "identityLevelManager"],
    ["IDENTITY_URI_MANAGER_PRIVATE_KEY", "identityUriManager"],
    ["COLLECTIBLE_TYPE_MANAGER_PRIVATE_KEY", "collectibleTypeManager"],
    ["COLLECTIBLE_MINTER_PRIVATE_KEY", "collectibleMinter"],
    ["COLLECTIBLE_URI_MANAGER_PRIVATE_KEY", "collectibleUriManager"],
  ];
  const updates: Record<string, string> = {};
  const separateRoles: string[] = [];
  for (const [backendKey, roleName] of mappings) {
    if (manifest.roles[roleName]?.toLowerCase() === deployer) updates[backendKey] = privateKey;
    else separateRoles.push(`${backendKey} (${roleName})`);
  }
  if (separateRoles.length) {
    console.warn(`These operator keys use separate wallets and must be configured manually: ${separateRoles.join(", ")}`);
  }
  return updates;
}

function main() {
  const networkName = process.argv[2] || "monadTestnet";
  const manifestPath = join(contractsRoot, "deployments", `${networkName}.json`);
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as DeploymentManifest;
  const gateway = manifest.contracts.FanoraMembershipGateway;
  const identity = manifest.contracts.FanoraMembershipIdentity;
  const collectibles = manifest.contracts.FanoraCollectibles;

  const backendEnv = join(workspaceRoot, "backend", ".env");
  updateEnvFile(backendEnv, {
    MONAD_CHAIN_ID: String(manifest.chainId),
    MEMBERSHIP_TREASURY_ADDRESS: manifest.treasury,
    MEMBERSHIP_FEE_WEI: manifest.membershipFeeWei,
    MEMBERSHIP_PAYMENT_CONTRACT_ADDRESS: gateway.address,
    MEMBERSHIP_IDENTITY_CONTRACT_ADDRESS: identity.address,
    COLLECTIBLES_CONTRACT_ADDRESS: collectibles.address,
    MEMBERSHIP_IDENTITY_START_BLOCK: String(identity.startBlock),
    COLLECTIBLES_START_BLOCK: String(collectibles.startBlock),
    ...privateKeyUpdates(manifest),
  });

  const frontendEnv = existsSync(join(workspaceRoot, "frontend", ".env.local"))
    ? join(workspaceRoot, "frontend", ".env.local")
    : join(workspaceRoot, "frontend", ".env");
  updateEnvFile(frontendEnv, {
    NEXT_PUBLIC_MEMBERSHIP_PAYMENT_CONTRACT_ADDRESS_MONAD_TESTNET: gateway.address,
    NEXT_PUBLIC_MEMBERSHIP_IDENTITY_CONTRACT_ADDRESS_MONAD_TESTNET: identity.address,
    NEXT_PUBLIC_COLLECTIBLES_CONTRACT_ADDRESS_MONAD_TESTNET: collectibles.address,
  });

  const sharedDirectory = join(workspaceRoot, "shared", "contracts");
  mkdirSync(sharedDirectory, { recursive: true });
  const sharedManifest = join(sharedDirectory, `${networkName}.deployment.json`);
  copyFileSync(manifestPath, sharedManifest);

  const backendContractsDirectory = join(workspaceRoot, "backend", "app", "contracts");
  mkdirSync(backendContractsDirectory, { recursive: true });
  for (const contractName of contractNames) {
    copyFileSync(
      join(sharedDirectory, `${contractName}.json`),
      join(backendContractsDirectory, `${contractName}.json`),
    );
  }

  console.log(`Backend configuration synchronized: ${basename(backendEnv)}`);
  console.log(`Frontend configuration synchronized: ${basename(frontendEnv)}`);
  console.log(`Public deployment manifest synchronized: ${sharedManifest}`);
  console.log(`Backend contract ABIs synchronized: ${backendContractsDirectory}`);
}

main();
