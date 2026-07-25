// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title Fanora 入会付款网关
/// @notice 接收用户通过 MetaMask 主动签名支付的固定会费，并为后端提供可审计的链上凭证。
/// @dev 合约不会接触用户私钥。用户调用 join 时，msg.sender 就是实际付款钱包。
///      会费先保存在本合约中，只有 TREASURY_MANAGER_ROLE 才能将资金提到 treasury。
contract FanoraMembershipGateway is AccessControl, Pausable, ReentrancyGuard {
    /// @notice 可更新收款地址并执行提现的平台运营角色。
    bytes32 public constant TREASURY_MANAGER_ROLE = keccak256("TREASURY_MANAGER_ROLE");
    /// @notice 可在异常情况下暂停或恢复入会功能的角色。
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    /// @notice 当前入会费用，单位 wei；可为 0，用于限时免费入会。
    uint256 public membershipFee = 1 ether;

    // 自定义错误比 revert 字符串更节省 Gas，名称直接描述失败原因。
    error InvalidAccount();
    error InvalidPaymentId();
    error IncorrectMembershipFee();
    error MembershipFeeNotFree();
    error PaymentAlreadyProcessed();
    error WalletAlreadyPaid();
    error TreasuryTransferFailed();
    error InvalidWithdrawalAmount();
    error DirectPaymentDisabled();

    /// @notice 用户成功入会后触发，后端仅认可该事件，不认可普通地址转账。
    event MembershipPaid(
        address indexed account,
        bytes32 indexed paymentId,
        address indexed treasury,
        uint256 amount
    );
    /// @notice 管理员变更最终资金接收地址时触发。
    event TreasuryUpdated(address indexed previousTreasury, address indexed nextTreasury);
    /// @notice 资金管理员修改入会费用时触发。
    event MembershipFeeUpdated(uint256 previousFee, uint256 nextFee);
    /// @notice 管理员从合约中提取会费时触发。
    event FundsWithdrawn(address indexed operator, address indexed treasury, uint256 amount);

    /// @notice 所有提现资金最终发送到该地址，可由管理员角色更新。
    address payable public treasury;
    /// @notice 防止同一个后端业务 paymentId 被重复使用。
    mapping(bytes32 paymentId => bool processed) public processedPaymentIds;
    /// @notice 防止同一个钱包重复缴纳入会费。
    mapping(address account => bool paid) public hasPaid;

    /// @param admin 合约最高管理员，部署时同时获得资金管理和暂停权限。
    /// @param initialTreasury 初始提现接收地址，不能为零地址。
    constructor(address admin, address payable initialTreasury) {
        if (admin == address(0) || initialTreasury == address(0)) revert InvalidAccount();
        treasury = initialTreasury;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(TREASURY_MANAGER_ROLE, admin);
        _grantRole(PAUSER_ROLE, admin);
    }

    /// @notice 用户缴纳当前设定的会费正式入会。
    /// @dev 必须由用户钱包直接调用并精确附带当前 membershipFee；paymentId 由后端生成后传给前端。
    /// @param paymentId 本次入会订单的 bytes32 唯一标识。
    function join(bytes32 paymentId) external payable whenNotPaused nonReentrant {
        if (msg.value != membershipFee) revert IncorrectMembershipFee();
        _recordMembership(msg.sender, paymentId, msg.value);
    }

    /// @notice 在会费为 0 时由平台运营账户为用户执行免钱包付款入会。
    /// @dev 用户不需要发起 payable 交易；调用者必须持有资金管理角色。
    function activateFreeMembership(address account, bytes32 paymentId)
        external
        onlyRole(TREASURY_MANAGER_ROLE)
        whenNotPaused
        nonReentrant
    {
        if (membershipFee != 0) revert MembershipFeeNotFree();
        _recordMembership(account, paymentId, 0);
    }

    function _recordMembership(address account, bytes32 paymentId, uint256 amount) private {
        if (account == address(0)) revert InvalidAccount();
        if (paymentId == bytes32(0)) revert InvalidPaymentId();
        if (processedPaymentIds[paymentId]) revert PaymentAlreadyProcessed();
        if (hasPaid[account]) revert WalletAlreadyPaid();

        processedPaymentIds[paymentId] = true;
        hasPaid[account] = true;
        emit MembershipPaid(account, paymentId, treasury, amount);
    }

    /// @notice 修改管理员提现时使用的最终收款地址。
    /// @param nextTreasury 新收款地址，不能为零地址。
    function setTreasury(address payable nextTreasury) external onlyRole(TREASURY_MANAGER_ROLE) {
        if (nextTreasury == address(0)) revert InvalidAccount();
        address previousTreasury = treasury;
        treasury = nextTreasury;
        emit TreasuryUpdated(previousTreasury, nextTreasury);
    }

    /// @notice 修改后续新用户需要支付的入会费用。
    /// @dev 已成功支付的历史记录不受影响；新金额可以为 0，表示限时免费入会。
    /// @param nextFee 新入会费用，单位 wei。
    function setMembershipFee(uint256 nextFee) external onlyRole(TREASURY_MANAGER_ROLE) {
        uint256 previousFee = membershipFee;
        membershipFee = nextFee;
        emit MembershipFeeUpdated(previousFee, nextFee);
    }

    /// @notice 从合约余额中提取指定数量的 MON 到 treasury。
    /// @param amount 提现金额，单位 wei，必须大于 0 且不超过合约余额。
    function withdraw(uint256 amount) external onlyRole(TREASURY_MANAGER_ROLE) nonReentrant {
        if (amount == 0 || amount > address(this).balance) revert InvalidWithdrawalAmount();
        address payable currentTreasury = treasury;
        (bool sent,) = currentTreasury.call{value: amount}("");
        if (!sent) revert TreasuryTransferFailed();
        emit FundsWithdrawn(msg.sender, currentTreasury, amount);
    }

    /// @notice 将合约中的全部 MON 余额提取到 treasury。
    function withdrawAll() external onlyRole(TREASURY_MANAGER_ROLE) nonReentrant {
        uint256 amount = address(this).balance;
        if (amount == 0) revert InvalidWithdrawalAmount();
        address payable currentTreasury = treasury;
        (bool sent,) = currentTreasury.call{value: amount}("");
        if (!sent) revert TreasuryTransferFailed();
        emit FundsWithdrawn(msg.sender, currentTreasury, amount);
    }

    /// @notice 暂停 join，已存入的资金仍可由管理员提现。
    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    /// @notice 恢复 join。
    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    /// @dev 禁止直接向合约地址转账，确保每笔会费都经过 join 并携带 paymentId。
    receive() external payable {
        revert DirectPaymentDisabled();
    }

    /// @dev 禁止通过未知函数或附带错误 calldata 转账。
    fallback() external payable {
        revert DirectPaymentDisabled();
    }
}
