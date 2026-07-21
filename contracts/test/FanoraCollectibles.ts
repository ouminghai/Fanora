import { expect } from "chai";
import { ethers } from "hardhat";
import { time } from "@nomicfoundation/hardhat-network-helpers";

describe("FanoraCollectibles", function () {
  async function fixture() {
    const [admin, manager, minter, uriManager, pauser, fan, anotherFan] = await ethers.getSigners();
    const collectibles = await ethers.deployContract("FanoraCollectibles", [admin.address]);
    await collectibles.grantRole(await collectibles.TOKEN_TYPE_MANAGER_ROLE(), manager.address);
    await collectibles.grantRole(await collectibles.MINTER_ROLE(), minter.address);
    await collectibles.grantRole(await collectibles.URI_MANAGER_ROLE(), uriManager.address);
    await collectibles.grantRole(await collectibles.PAUSER_ROLE(), pauser.address);
    const now = await time.latest();
    return { collectibles, admin, manager, minter, uriManager, pauser, fan, anotherFan, now };
  }

  it("enforces supply, cumulative wallet limits, time windows, and claim keys", async function () {
    const { collectibles, manager, minter, fan, now } = await fixture();
    await collectibles.connect(manager).createTokenType(1, 0, "ipfs://concert", 3, 2, now, now + 3600, true);
    await collectibles.connect(minter).mintCollectible(fan.address, 1, 1, ethers.id("claim-1"));
    await collectibles.connect(minter).mintCollectible(fan.address, 1, 1, ethers.id("claim-2"));
    await expect(collectibles.connect(minter).mintCollectible(fan.address, 1, 1, ethers.id("claim-3")))
      .to.be.revertedWithCustomError(collectibles, "WalletLimitExceeded");
    await expect(collectibles.connect(minter).mintCollectible(fan.address, 1, 1, ethers.id("claim-1")))
      .to.be.revertedWithCustomError(collectibles, "ClaimAlreadyProcessed");
    expect(await collectibles.mintedByWallet(1, fan.address)).to.equal(2);
  });

  it("validates category-specific immutable issue constraints", async function () {
    const { collectibles, manager, now } = await fixture();
    await expect(collectibles.connect(manager).createTokenType(2, 1, "ipfs://custom", 2, 1, now, now + 3600, false))
      .to.be.revertedWithCustomError(collectibles, "InvalidCategoryConfiguration");
    await expect(collectibles.connect(manager).createTokenType(3, 2, "ipfs://task", 10, 2, now, now + 3600, false))
      .to.be.revertedWithCustomError(collectibles, "InvalidCategoryConfiguration");
  });

  it("blocks non-transferable single and batch transfers while allowing concert cards", async function () {
    const { collectibles, manager, minter, fan, anotherFan, now } = await fixture();
    await collectibles.connect(manager).createTokenType(1, 0, "ipfs://concert", 10, 2, now, now + 3600, true);
    await collectibles.connect(manager).createTokenType(2, 2, "ipfs://task", 10, 1, now, now + 3600, false);
    await collectibles.connect(minter).mintCollectible(fan.address, 1, 1, ethers.id("concert"));
    await collectibles.connect(minter).mintCollectible(fan.address, 2, 1, ethers.id("task"));
    await collectibles.connect(fan).safeTransferFrom(fan.address, anotherFan.address, 1, 1, "0x");
    await expect(collectibles.connect(fan).safeTransferFrom(fan.address, anotherFan.address, 2, 1, "0x"))
      .to.be.revertedWithCustomError(collectibles, "NonTransferable");
    await expect(collectibles.connect(fan).safeBatchTransferFrom(fan.address, anotherFan.address, [1, 2], [1, 1], "0x"))
      .to.be.reverted;
  });

  it("freezes metadata permanently and blocks writes and transfers while paused", async function () {
    const { collectibles, manager, minter, uriManager, pauser, fan, anotherFan, now } = await fixture();
    await collectibles.connect(manager).createTokenType(1, 0, "ipfs://concert-v1", 10, 2, now, now + 3600, true);
    await collectibles.connect(uriManager).updateTokenMetadata(1, "ipfs://concert-v2");
    await collectibles.connect(uriManager).freezeMetadata(1);
    await expect(collectibles.connect(uriManager).updateTokenMetadata(1, "ipfs://concert-v3"))
      .to.be.revertedWithCustomError(collectibles, "MetadataAlreadyFrozen");
    await collectibles.connect(minter).mintCollectible(fan.address, 1, 1, ethers.id("claim"));
    await collectibles.connect(pauser).pause();
    expect(await collectibles.uri(1)).to.equal("ipfs://concert-v2");
    await expect(collectibles.connect(fan).safeTransferFrom(fan.address, anotherFan.address, 1, 1, "0x"))
      .to.be.revertedWithCustomError(collectibles, "EnforcedPause");
  });

  it("updates limits before receiver callbacks so reentry cannot exceed them", async function () {
    const { collectibles, manager, minter, now } = await fixture();
    await collectibles.connect(manager).createTokenType(1, 2, "ipfs://task", 1, 1, now, now + 3600, false);
    const receiver = await ethers.deployContract("MaliciousCollectibleReceiver", [
      await collectibles.getAddress(), 1, ethers.id("reentry"),
    ]);
    await collectibles.grantRole(await collectibles.MINTER_ROLE(), await receiver.getAddress());
    await collectibles.connect(minter).mintCollectible(await receiver.getAddress(), 1, 1, ethers.id("outer"));
    expect(await collectibles.balanceOf(await receiver.getAddress(), 1)).to.equal(1);
    expect((await collectibles.tokenTypes(1)).mintedSupply).to.equal(1);
    expect(await collectibles.processedClaimKeys(ethers.id("reentry"))).to.equal(false);
  });
});
