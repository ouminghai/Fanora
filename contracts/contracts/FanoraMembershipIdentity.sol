// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";

/// @title Fanora 会员身份凭证
/// @notice 为正式会员铸造不可转移的 ERC-721 身份凭证，并随会员等级更新链上身份展示。
/// @dev 每个钱包同时只能拥有一个有效身份。tokenId 在升级时保持不变，metadataUri 指向 Pinata/IPFS。
///      后端只使用平台运营钱包执行铸造和升级，用户不需要向平台提供私钥。
contract FanoraMembershipIdentity is ERC721, AccessControl, Pausable {
    /// @notice 可为已验证正式会员铸造身份的角色。
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    /// @notice 可同步会员等级变化的角色，支持升级和降级。
    bytes32 public constant LEVEL_MANAGER_ROLE = keccak256("LEVEL_MANAGER_ROLE");
    /// @notice 可在等级不变时更新 metadata URI 的角色。
    bytes32 public constant URI_MANAGER_ROLE = keccak256("URI_MANAGER_ROLE");
    /// @notice 可暂停或恢复身份合约写操作的角色。
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    /// @notice 链上会员等级配置。
    struct LevelConfig {
        /// @dev 等级排序值，用于前端和索引器理解等级高低。
        uint64 rank;
        /// @dev 是否允许新铸造或升级到此等级。
        bool active;
        /// @dev 用于区分“未配置”和“已配置但停用”。
        bool exists;
    }

    // 身份不可转移、参数无效、重复操作等业务错误。
    error Soulbound();
    error InvalidAccount();
    error InvalidMetadataUri();
    error InvalidLevel();
    error InvalidLevelRank();
    error IdentityAlreadyExists();
    error OperationAlreadyProcessed();
    error SameMembershipLevel();
    error EmptyReason();

    /// @notice 管理员创建或启停会员等级时触发。
    event MembershipLevelConfigured(uint256 indexed levelId, uint64 rank, bool active);
    /// @notice 新身份铸造完成时触发。
    event IdentityMinted(
        address indexed account,
        uint256 indexed tokenId,
        uint256 indexed levelId,
        bytes32 operationId,
        string metadataUri,
        uint256 metadataVersion
    );
    /// @notice 等级变更及 metadata 更新完成时触发。
    event MembershipLevelUpdated(
        address indexed account,
        uint256 indexed tokenId,
        uint256 indexed previousLevelId,
        uint256 nextLevelId,
        bytes32 operationId,
        string metadataUri,
        uint256 metadataVersion
    );
    /// @notice 等级不变、仅更新 metadata 时触发。
    event IdentityMetadataUpdated(
        address indexed account,
        uint256 indexed tokenId,
        bytes32 indexed operationId,
        string metadataUri,
        uint256 metadataVersion
    );
    /// @notice 管理员撤销并销毁身份时触发。
    event IdentityRevoked(
        address indexed account,
        uint256 indexed tokenId,
        bytes32 indexed operationId,
        string reason
    );

    /// @dev tokenId 从 1 开始递增，0 专门表示“没有身份”。
    uint256 private _nextTokenId = 1;
    /// @notice 钱包当前拥有的有效身份 tokenId。
    mapping(address account => uint256 tokenId) public identityTokenOf;
    /// @notice 每个身份 tokenId 当前对应的会员等级 ID。
    mapping(uint256 tokenId => uint256 levelId) public membershipLevelOf;
    /// @notice metadata 版本号，便于后端和索引器识别更新。
    mapping(uint256 tokenId => uint256 version) public metadataVersionOf;
    /// @dev tokenId 对应的 IPFS metadata URI。
    mapping(uint256 tokenId => string metadataUri) private _tokenUris;
    /// @notice levelId 对应的链上等级配置。
    mapping(uint256 levelId => LevelConfig config) public membershipLevels;
    /// @notice 已处理的后端操作 ID，用于保证链上写操作幂等。
    mapping(bytes32 operationId => bool processed) public processedOperationIds;

    /// @param admin 合约最高管理员，负责配置等级和分配各运营角色。
    constructor(address admin) ERC721("Fanora Membership Identity", "FANORA-ID") {
        if (admin == address(0)) revert InvalidAccount();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    /// @notice 创建、启用或停用一个会员等级。
    /// @dev 已存在等级的 rank 不允许修改，避免历史升级顺序发生变化。
    /// @param levelId 对应数据库 membership_levels 的等级 ID。
    /// @param rank 等级顺序，数值越大等级越高。
    /// @param active 是否允许铸造或升级到该等级。
    function configureMembershipLevel(uint256 levelId, uint64 rank, bool active)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        if (levelId == 0) revert InvalidLevel();
        if (rank == 0) revert InvalidLevelRank();
        LevelConfig storage current = membershipLevels[levelId];
        if (current.exists && current.rank != rank) revert InvalidLevelRank();
        membershipLevels[levelId] = LevelConfig({rank: rank, active: active, exists: true});
        emit MembershipLevelConfigured(levelId, rank, active);
    }

    /// @notice 为正式会员铸造唯一的不可转移身份。
    /// @param account 接收身份的钱包地址。
    /// @param levelId 初始会员等级 ID。
    /// @param metadataUri 后端通过 Pinata 生成的 ipfs:// metadata 地址。
    /// @param operationId 后端生成的唯一操作 ID，防止重试导致重复铸造。
    /// @return tokenId 新身份的 tokenId。
    function mintIdentity(address account, uint256 levelId, string calldata metadataUri, bytes32 operationId)
        external
        onlyRole(MINTER_ROLE)
        whenNotPaused
        returns (uint256 tokenId)
    {
        _validateOperation(operationId);
        if (account == address(0)) revert InvalidAccount();
        if (identityTokenOf[account] != 0) revert IdentityAlreadyExists();
        _validateActiveLevel(levelId);
        _validateMetadataUri(metadataUri);

        processedOperationIds[operationId] = true;
        tokenId = _nextTokenId++;
        identityTokenOf[account] = tokenId;
        membershipLevelOf[tokenId] = levelId;
        metadataVersionOf[tokenId] = 1;
        _tokenUris[tokenId] = metadataUri;
        _safeMint(account, tokenId);
        emit IdentityMinted(account, tokenId, levelId, operationId, metadataUri, 1);
    }

    /// @notice 将现有身份同步到新的会员等级，同时切换该等级对应的 metadata。
    /// @dev tokenId 不变，等级可升可降；等级由累计获得 FAN 决定，不受可消费 FAN 余额扣减影响。
    function updateMembershipLevel(
        uint256 tokenId,
        uint256 nextLevelId,
        string calldata metadataUri,
        bytes32 operationId
    ) external onlyRole(LEVEL_MANAGER_ROLE) whenNotPaused {
        _requireOwned(tokenId);
        _validateOperation(operationId);
        _validateActiveLevel(nextLevelId);
        _validateMetadataUri(metadataUri);

        uint256 previousLevelId = membershipLevelOf[tokenId];
        if (previousLevelId == nextLevelId) revert SameMembershipLevel();

        processedOperationIds[operationId] = true;
        membershipLevelOf[tokenId] = nextLevelId;
        uint256 version = ++metadataVersionOf[tokenId];
        _tokenUris[tokenId] = metadataUri;
        emit MembershipLevelUpdated(
            ownerOf(tokenId), tokenId, previousLevelId, nextLevelId, operationId, metadataUri, version
        );
    }

    /// @notice 在会员等级不变时更新身份 metadata，例如重绘可下载会员证或修复 Pinata 内容。
    function updateIdentityMetadata(uint256 tokenId, string calldata metadataUri, bytes32 operationId)
        external
        onlyRole(URI_MANAGER_ROLE)
        whenNotPaused
    {
        address account = _requireOwned(tokenId);
        _validateOperation(operationId);
        _validateMetadataUri(metadataUri);
        processedOperationIds[operationId] = true;
        uint256 version = ++metadataVersionOf[tokenId];
        _tokenUris[tokenId] = metadataUri;
        emit IdentityMetadataUpdated(account, tokenId, operationId, metadataUri, version);
    }

    /// @notice 撤销并销毁会员身份，同时允许该钱包未来重新铸造新身份。
    /// @param reason 非空的审计原因，会记录在事件中。
    function revokeIdentity(uint256 tokenId, bytes32 operationId, string calldata reason)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
        whenNotPaused
    {
        address account = _requireOwned(tokenId);
        _validateOperation(operationId);
        if (bytes(reason).length == 0) revert EmptyReason();
        processedOperationIds[operationId] = true;
        identityTokenOf[account] = 0;
        _burn(tokenId);
        emit IdentityRevoked(account, tokenId, operationId, reason);
    }

    /// @notice 暂停铸造、升级、metadata 更新和撤销操作。
    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    /// @notice 恢复身份写操作。
    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    /// @notice 返回身份 metadata 的 IPFS URI。
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        return _tokenUris[tokenId];
    }

    /// @dev SBT 不允许单个 token 授权转移。
    function approve(address, uint256) public pure override {
        revert Soulbound();
    }

    /// @dev SBT 不允许批量授权运营者转移。
    function setApprovalForAll(address, bool) public pure override {
        revert Soulbound();
    }

    /// @dev OpenZeppelin ERC-721 的统一状态更新入口；仅允许铸造和销毁，拒绝钱包间转移。
    function _update(address to, uint256 tokenId, address auth) internal override returns (address) {
        address from = _ownerOf(tokenId);
        if (from != address(0) && to != address(0)) revert Soulbound();
        return super._update(to, tokenId, auth);
    }

    /// @dev 校验操作 ID 非空且未处理，实现后端重试幂等。
    function _validateOperation(bytes32 operationId) private view {
        if (operationId == bytes32(0) || processedOperationIds[operationId]) revert OperationAlreadyProcessed();
    }

    /// @dev 校验目标等级已配置且处于启用状态。
    function _validateActiveLevel(uint256 levelId) private view {
        LevelConfig memory level = membershipLevels[levelId];
        if (!level.exists || !level.active) revert InvalidLevel();
    }

    /// @dev 只接受 ipfs:// URI，避免把可变 HTTP 地址写入身份凭证。
    function _validateMetadataUri(string calldata metadataUri) private pure {
        bytes memory value = bytes(metadataUri);
        if (
            value.length <= 7 || value[0] != "i" || value[1] != "p" || value[2] != "f" || value[3] != "s"
                || value[4] != ":" || value[5] != "/" || value[6] != "/"
        ) revert InvalidMetadataUri();
    }

    /// @notice 声明本合约支持 ERC-721、AccessControl 等接口。
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
