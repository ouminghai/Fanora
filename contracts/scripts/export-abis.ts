import { artifacts } from "hardhat";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

async function main() {
  const names = ["FanoraMembershipGateway", "FanoraMembershipIdentity", "FanoraCollectibles"];
  const outputDirectories = [
    join(__dirname, "../../shared/contracts"),
    join(__dirname, "../../backend/app/contracts"),
  ];
  for (const outputDirectory of outputDirectories) mkdirSync(outputDirectory, { recursive: true });

  for (const name of names) {
    const artifact = await artifacts.readArtifact(name);
    const content = `${JSON.stringify({ contractName: name, abi: artifact.abi }, null, 2)}\n`;
    for (const outputDirectory of outputDirectories) {
      writeFileSync(join(outputDirectory, `${name}.json`), content);
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
