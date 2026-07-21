import { expect } from "chai";
import { ethers } from "hardhat";

describe("FanoraMembershipIdentity", function () {
  async function fixture() {
    const [admin, minter, levelManager, uriManager, pauser, fan, anotherFan] = await ethers.getSigners();
    const identity = await ethers.deployContract("FanoraMembershipIdentity", [admin.address]);
    await identity.grantRole(await identity.MINTER_ROLE(), minter.address);
    await identity.grantRole(await identity.LEVEL_MANAGER_ROLE(), levelManager.address);
    await identity.grantRole(await identity.URI_MANAGER_ROLE(), uriManager.address);
    await identity.grantRole(await identity.PAUSER_ROLE(), pauser.address);
    await identity.configureMembershipLevel(1, 1, true);
    await identity.configureMembershipLevel(2, 2, true);
    return { identity, admin, minter, levelManager, uriManager, pauser, fan, anotherFan };
  }

  it("mints one identity per wallet and permanently rejects duplicate operations", async function () {
    const { identity, minter, fan, anotherFan } = await fixture();
    const operation = ethers.id("membership:user-1");
    await expect(identity.connect(minter).mintIdentity(fan.address, 1, "ipfs://identity-v1", operation))
      .to.emit(identity, "IdentityMinted")
      .withArgs(fan.address, 1, 1, operation, "ipfs://identity-v1", 1);
    expect(await identity.identityTokenOf(fan.address)).to.equal(1);
    expect(await identity.tokenURI(1)).to.equal("ipfs://identity-v1");
    await expect(
      identity.connect(minter).mintIdentity(fan.address, 1, "ipfs://identity-copy", ethers.id("other")),
    ).to.be.revertedWithCustomError(identity, "IdentityAlreadyExists");
    await expect(
      identity.connect(minter).mintIdentity(anotherFan.address, 1, "ipfs://identity-copy", operation),
    ).to.be.revertedWithCustomError(identity, "OperationAlreadyProcessed");
  });

  it("keeps the token id stable during upgrades and blocks downgrades", async function () {
    const { identity, minter, levelManager, fan } = await fixture();
    await identity.connect(minter).mintIdentity(fan.address, 1, "ipfs://identity-v1", ethers.id("mint"));
    await identity.connect(levelManager).updateMembershipLevel(1, 2, "ipfs://identity-v2", ethers.id("upgrade"));
    expect(await identity.ownerOf(1)).to.equal(fan.address);
    expect(await identity.membershipLevelOf(1)).to.equal(2);
    expect(await identity.metadataVersionOf(1)).to.equal(2);
    await expect(
      identity.connect(levelManager).updateMembershipLevel(1, 1, "ipfs://identity-v3", ethers.id("downgrade")),
    ).to.be.revertedWithCustomError(identity, "MembershipDowngradeNotAllowed");
  });

  it("blocks approvals and every user transfer entry point", async function () {
    const { identity, minter, fan, anotherFan } = await fixture();
    await identity.connect(minter).mintIdentity(fan.address, 1, "ipfs://identity", ethers.id("mint"));
    await expect(identity.connect(fan).approve(anotherFan.address, 1)).to.be.revertedWithCustomError(identity, "Soulbound");
    await expect(identity.connect(fan).setApprovalForAll(anotherFan.address, true)).to.be.revertedWithCustomError(identity, "Soulbound");
    await expect(identity.connect(fan).transferFrom(fan.address, anotherFan.address, 1)).to.be.revertedWithCustomError(identity, "Soulbound");
    await expect(identity.connect(fan)["safeTransferFrom(address,address,uint256)"](fan.address, anotherFan.address, 1)).to.be.revertedWithCustomError(identity, "Soulbound");
    await expect(identity.connect(fan)["safeTransferFrom(address,address,uint256,bytes)"](fan.address, anotherFan.address, 1, "0x")).to.be.revertedWithCustomError(identity, "Soulbound");
  });

  it("honors level deactivation and pause without breaking reads", async function () {
    const { identity, admin, minter, pauser, fan } = await fixture();
    await identity.connect(admin).configureMembershipLevel(1, 1, false);
    await expect(identity.connect(minter).mintIdentity(fan.address, 1, "ipfs://identity", ethers.id("mint")))
      .to.be.revertedWithCustomError(identity, "InvalidLevel");
    await identity.connect(admin).configureMembershipLevel(1, 1, true);
    await identity.connect(minter).mintIdentity(fan.address, 1, "ipfs://identity", ethers.id("mint-ok"));
    await identity.connect(pauser).pause();
    expect(await identity.ownerOf(1)).to.equal(fan.address);
    await expect(identity.connect(minter).mintIdentity(admin.address, 1, "ipfs://other", ethers.id("paused")))
      .to.be.revertedWithCustomError(identity, "EnforcedPause");
  });
});
