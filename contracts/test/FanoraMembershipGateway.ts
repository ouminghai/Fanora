import { expect } from "chai";
import { ethers } from "hardhat";

describe("FanoraMembershipGateway", function () {
  async function fixture() {
    const [admin, treasury, pauser, fan, anotherFan] = await ethers.getSigners();
    const gateway = await ethers.deployContract("FanoraMembershipGateway", [admin.address, treasury.address]);
    await gateway.grantRole(await gateway.PAUSER_ROLE(), pauser.address);
    await gateway.grantRole(await gateway.TREASURY_MANAGER_ROLE(), admin.address);
    return { gateway, admin, treasury, pauser, fan, anotherFan };
  }

  it("accepts exactly 1 MON, holds it, and emits an auditable payment", async function () {
    const { gateway, treasury, fan } = await fixture();
    const paymentId = ethers.id("membership:user-1");
    await gateway.connect(fan).join(paymentId, { value: ethers.parseEther("1") });
    expect(await ethers.provider.getBalance(await gateway.getAddress())).to.equal(ethers.parseEther("1"));
    expect(await ethers.provider.getBalance(treasury.address)).to.be.greaterThan(0);
    await expect(gateway.connect(fan).join(ethers.id("second"), { value: ethers.parseEther("1") }))
      .to.be.revertedWithCustomError(gateway, "WalletAlreadyPaid");
    expect(await gateway.processedPaymentIds(paymentId)).to.equal(true);
    expect(await gateway.hasPaid(fan.address)).to.equal(true);
  });

  it("rejects incorrect amounts and duplicate payment ids", async function () {
    const { gateway, fan, anotherFan } = await fixture();
    const paymentId = ethers.id("membership:shared");
    await expect(gateway.connect(fan).join(paymentId, { value: ethers.parseEther("0.99") }))
      .to.be.revertedWithCustomError(gateway, "IncorrectMembershipFee");
    await gateway.connect(fan).join(paymentId, { value: ethers.parseEther("1") });
    await expect(gateway.connect(anotherFan).join(paymentId, { value: ethers.parseEther("1") }))
      .to.be.revertedWithCustomError(gateway, "PaymentAlreadyProcessed");
  });

  it("rejects direct transfers and payments while paused", async function () {
    const { gateway, pauser, fan } = await fixture();
    await expect(fan.sendTransaction({ to: await gateway.getAddress(), value: 1 }))
      .to.be.revertedWithCustomError(gateway, "DirectPaymentDisabled");
    await gateway.connect(pauser).pause();
    await expect(gateway.connect(fan).join(ethers.id("paused"), { value: ethers.parseEther("1") }))
      .to.be.revertedWithCustomError(gateway, "EnforcedPause");
  });

  it("allows only the treasury manager to change the recipient", async function () {
    const { gateway, admin, fan, anotherFan } = await fixture();
    await expect(gateway.connect(fan).setTreasury(anotherFan.address)).to.be.reverted;
    await gateway.connect(admin).setTreasury(anotherFan.address);
    expect(await gateway.treasury()).to.equal(anotherFan.address);
  });

  it("allows only the treasury manager to change the membership fee", async function () {
    const { gateway, admin, fan } = await fixture();
    const nextFee = ethers.parseEther("2.5");
    await expect(gateway.connect(fan).setMembershipFee(nextFee)).to.be.reverted;
    await expect(gateway.connect(admin).setMembershipFee(0))
      .to.be.revertedWithCustomError(gateway, "InvalidMembershipFee");
    await expect(gateway.connect(admin).setMembershipFee(nextFee))
      .to.emit(gateway, "MembershipFeeUpdated")
      .withArgs(ethers.parseEther("1"), nextFee);
    expect(await gateway.membershipFee()).to.equal(nextFee);
    await expect(gateway.connect(fan).join(ethers.id("old-fee"), { value: ethers.parseEther("1") }))
      .to.be.revertedWithCustomError(gateway, "IncorrectMembershipFee");
    await gateway.connect(fan).join(ethers.id("new-fee"), { value: nextFee });
  });

  it("allows the treasury manager to withdraw held fees", async function () {
    const { gateway, admin, treasury, fan } = await fixture();
    await gateway.connect(fan).join(ethers.id("withdrawable"), { value: ethers.parseEther("1") });
    await expect(() => gateway.connect(admin).withdraw(ethers.parseEther("0.4")))
      .to.changeEtherBalance(treasury, ethers.parseEther("0.4"));
    expect(await ethers.provider.getBalance(await gateway.getAddress())).to.equal(ethers.parseEther("0.6"));
    await expect(() => gateway.connect(admin).withdrawAll()).to.changeEtherBalance(treasury, ethers.parseEther("0.6"));
    expect(await ethers.provider.getBalance(await gateway.getAddress())).to.equal(0);
  });

  it("blocks withdrawals from accounts without treasury permission", async function () {
    const { gateway, fan } = await fixture();
    await gateway.connect(fan).join(ethers.id("protected"), { value: ethers.parseEther("1") });
    await expect(gateway.connect(fan).withdrawAll()).to.be.reverted;
  });
});
