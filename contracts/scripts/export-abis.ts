import { artifacts } from "hardhat";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

async function main() {
  const names = ["FanoraMembershipGateway", "FanoraMembershipIdentity", "FanoraCollectibles"];
  const outputDirectory = join(__dirname, "../../shared/contracts");
  mkdirSync(outputDirectory, { recursive: true });
  for (const name of names) {
    const artifact = await artifacts.readArtifact(name);
    writeFileSync(
      join(outputDirectory, `${name}.json`),
      `${JSON.stringify({ contractName: name, abi: artifact.abi }, null, 2)}\n`,
    );
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
