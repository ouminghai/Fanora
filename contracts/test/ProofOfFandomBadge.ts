import { expect } from "chai";
import { ethers } from "hardhat";

describe("ProofOfFandomBadge", function () {
  async function deployBadge() {
    const [admin, fan, anotherFan] = await ethers.getSigners();
    const badge = await ethers.deployContract("ProofOfFandomBadge", [
      admin.address,
      "ipfs://fanora/{id}.json",
    ]);
    return { badge, admin, fan, anotherFan };
  }

  it("allows an authorized operator to mint a badge", async function () {
    const { badge, fan } = await deployBadge();

    await badge.mint(fan.address, 1);

    expect(await badge.balanceOf(fan.address, 1)).to.equal(1);
  });

  it("prevents fans from transferring identity badges", async function () {
    const { badge, fan, anotherFan } = await deployBadge();
    await badge.mint(fan.address, 1);

    await expect(
      badge
        .connect(fan)
        .safeTransferFrom(fan.address, anotherFan.address, 1, 1, "0x"),
    ).to.be.revertedWithCustomError(badge, "Soulbound");
  });
});

