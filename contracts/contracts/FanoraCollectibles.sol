// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ERC1155} from "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

/// @title Fanora 粉丝收藏品
/// @notice 用 ERC-1155 管理演唱会纪念卡、用户定制徽章和任务限量徽章。
/// @dev 每个 Token 类型都可独立配置供应量、单钱包上限、铸造时间和可转移性。
///      后端使用平台运营钱包发放收藏品，用户不需要提供自己的私钥。
contract FanoraCollectibles is ERC1155, AccessControl, Pausable {
    /// @notice 钱包、市场和区块浏览器展示时读取的收藏品集合名称。
    string public constant name = "Fanora Collectibles";
    /// @notice 钱包、市场和区块浏览器展示时读取的收藏品集合符号。
    string public constant symbol = "FANORA";

    /// @notice 可创建、启用或停用收藏品类型的角色。
    bytes32 public constant TOKEN_TYPE_MANAGER_ROLE = keccak256("TOKEN_TYPE_MANAGER_ROLE");
    /// @notice 可向符合条件的用户铸造收藏品的角色。
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    /// @notice 可更新或冻结 metadata 的角色。
    bytes32 public constant URI_MANAGER_ROLE = keccak256("URI_MANAGER_ROLE");
    /// @notice 可暂停或恢复收藏品合约的角色。
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    /// @notice Fanora 支持的收藏品业务分类。
    enum TokenCategory {
        /// 演唱会纪念卡，可按创建时配置决定是否允许转移。
        CONCERT_CARD,
        /// 用户定制徽章，固定总量 1、单钱包 1 且不可转移。
        CUSTOM_BADGE,
        /// 任务限量徽章，每个钱包最多 1 枚且不可转移。
        TASK_LIMITED_BADGE,
        /// 粉丝发布的限量 NFT，可设置供应量、单钱包上限和转让策略。
        FAN_LIMITED_NFT
    }

    /// @notice 单个 ERC-1155 tokenId 的发行规则和当前状态。
    struct TokenType {
        TokenCategory category;
        uint256 maxSupply;
        uint256 mintedSupply;
        uint256 perWalletLimit;
        uint64 mintStart;
        uint64 mintEnd;
        bool transferable;
        bool metadataFrozen;
        bool active;
        bool exists;
    }

    // 参数、供应量、领取幂等和转移限制相关的业务错误。
    error InvalidAccount();
    error InvalidTokenId();
    error InvalidMetadataUri();
    error InvalidSupply();
    error InvalidMintWindow();
    error InvalidCategoryConfiguration();
    error TokenTypeAlreadyExists();
    error TokenTypeNotFound();
    error TokenTypeInactive();
    error MintWindowClosed();
    error MaxSupplyExceeded();
    error WalletLimitExceeded();
    error ClaimAlreadyProcessed();
    error MetadataAlreadyFrozen();
    error NonTransferable();

    /// @notice 新收藏品类型创建完成时触发。
    event TokenTypeCreated(
        uint256 indexed tokenId,
        TokenCategory indexed category,
        string metadataUri,
        uint256 maxSupply,
        uint256 perWalletLimit,
        uint64 mintStart,
        uint64 mintEnd,
        bool transferable
    );
    /// @notice 收藏品成功发放时触发。
    event CollectibleMinted(
        address indexed account,
        uint256 indexed tokenId,
        uint256 amount,
        bytes32 indexed claimKey,
        uint256 mintedSupply
    );
    /// @notice 收藏品 metadata URI 更新时触发。
    event TokenMetadataUpdated(uint256 indexed tokenId, string metadataUri);
    /// @notice metadata 永久冻结时触发，冻结后不能再次修改。
    event TokenMetadataFrozen(uint256 indexed tokenId);
    /// @notice 收藏品类型启用状态变化时触发。
    event TokenTypeStatusChanged(uint256 indexed tokenId, bool active);

    /// @notice tokenId 对应的完整发行配置。
    mapping(uint256 tokenId => TokenType config) public tokenTypes;
    /// @dev tokenId 对应的 IPFS metadata URI。
    mapping(uint256 tokenId => string metadataUri) private _tokenUris;
    /// @notice 已处理的领取键，防止同一业务奖励重复发放。
    mapping(bytes32 claimKey => bool processed) public processedClaimKeys;
    /// @notice 每个 tokenId 已向每个钱包铸造的数量。
    mapping(uint256 tokenId => mapping(address account => uint256 amount)) public mintedByWallet;

    /// @param admin 合约最高管理员，负责向不同运营钱包分配角色。
    constructor(address admin) ERC1155("") {
        if (admin == address(0)) revert InvalidAccount();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    /// @notice 创建一个新的收藏品类型。
    /// @dev CUSTOM_BADGE 和 TASK_LIMITED_BADGE 会强制执行产品定义的不可转移和数量限制。
    ///      FAN_LIMITED_NFT 用于粉丝直接发布的限量 NFT，供应量与单钱包上限由后端业务校验。
    function createTokenType(
        uint256 tokenId,
        TokenCategory category,
        string calldata metadataUri,
        uint256 maxSupply,
        uint256 perWalletLimit,
        uint64 mintStart,
        uint64 mintEnd,
        bool transferable
    ) external onlyRole(TOKEN_TYPE_MANAGER_ROLE) whenNotPaused {
        if (tokenId == 0) revert InvalidTokenId();
        if (tokenTypes[tokenId].exists) revert TokenTypeAlreadyExists();
        _validateMetadataUri(metadataUri);
        uint256 effectivePerWalletLimit =
            category == TokenCategory.FAN_LIMITED_NFT ? maxSupply : perWalletLimit;
        if (maxSupply == 0 || effectivePerWalletLimit == 0 || effectivePerWalletLimit > maxSupply) {
            revert InvalidSupply();
        }
        if (mintEnd <= mintStart) revert InvalidMintWindow();
        if (category == TokenCategory.CUSTOM_BADGE && (maxSupply != 1 || perWalletLimit != 1 || transferable)) {
            revert InvalidCategoryConfiguration();
        }
        if (category == TokenCategory.TASK_LIMITED_BADGE && (perWalletLimit != 1 || transferable)) {
            revert InvalidCategoryConfiguration();
        }

        tokenTypes[tokenId] = TokenType({
            category: category,
            maxSupply: maxSupply,
            mintedSupply: 0,
            perWalletLimit: effectivePerWalletLimit,
            mintStart: mintStart,
            mintEnd: mintEnd,
            transferable: transferable,
            metadataFrozen: false,
            active: true,
            exists: true
        });
        _tokenUris[tokenId] = metadataUri;
        emit TokenTypeCreated(
            tokenId, category, metadataUri, maxSupply, effectivePerWalletLimit, mintStart, mintEnd, transferable
        );
    }

    /// @notice 向指定钱包发放收藏品。
    /// @dev 同时校验领取键幂等、发行时间、总供应量和单钱包上限。
    /// @param claimKey 后端生成的唯一业务领取键，重复提交会回滚。
    function mintCollectible(address account, uint256 tokenId, uint256 amount, bytes32 claimKey)
        external
        onlyRole(MINTER_ROLE)
        whenNotPaused
    {
        if (account == address(0)) revert InvalidAccount();
        if (amount == 0) revert InvalidSupply();
        if (claimKey == bytes32(0) || processedClaimKeys[claimKey]) revert ClaimAlreadyProcessed();
        TokenType storage config = tokenTypes[tokenId];
        if (!config.exists) revert TokenTypeNotFound();
        if (!config.active) revert TokenTypeInactive();
        if (block.timestamp < config.mintStart || block.timestamp > config.mintEnd) revert MintWindowClosed();
        if (config.mintedSupply + amount > config.maxSupply) revert MaxSupplyExceeded();
        if (mintedByWallet[tokenId][account] + amount > config.perWalletLimit) revert WalletLimitExceeded();

        processedClaimKeys[claimKey] = true;
        config.mintedSupply += amount;
        mintedByWallet[tokenId][account] += amount;
        _mint(account, tokenId, amount, "");
        emit CollectibleMinted(account, tokenId, amount, claimKey, config.mintedSupply);
    }

    /// @notice 在 metadata 未冻结前更新 tokenId 的 IPFS URI。
    function updateTokenMetadata(uint256 tokenId, string calldata metadataUri)
        external
        onlyRole(URI_MANAGER_ROLE)
        whenNotPaused
    {
        TokenType storage config = tokenTypes[tokenId];
        if (!config.exists) revert TokenTypeNotFound();
        if (config.metadataFrozen) revert MetadataAlreadyFrozen();
        _validateMetadataUri(metadataUri);
        _tokenUris[tokenId] = metadataUri;
        emit TokenMetadataUpdated(tokenId, metadataUri);
    }

    /// @notice 永久冻结 tokenId 的 metadata，冻结后不可撤销。
    function freezeMetadata(uint256 tokenId) external onlyRole(URI_MANAGER_ROLE) whenNotPaused {
        TokenType storage config = tokenTypes[tokenId];
        if (!config.exists) revert TokenTypeNotFound();
        if (config.metadataFrozen) revert MetadataAlreadyFrozen();
        config.metadataFrozen = true;
        emit TokenMetadataFrozen(tokenId);
    }

    /// @notice 启用或停用某个收藏品类型；停用后不能继续铸造。
    function setTokenTypeActive(uint256 tokenId, bool active)
        external
        onlyRole(TOKEN_TYPE_MANAGER_ROLE)
        whenNotPaused
    {
        TokenType storage config = tokenTypes[tokenId];
        if (!config.exists) revert TokenTypeNotFound();
        config.active = active;
        emit TokenTypeStatusChanged(tokenId, active);
    }

    /// @notice 暂停所有铸造、配置、metadata 更新以及 token 转移。
    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    /// @notice 恢复合约操作。
    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    /// @notice 返回指定 tokenId 的 IPFS metadata URI。
    function uri(uint256 tokenId) public view override returns (string memory) {
        if (!tokenTypes[tokenId].exists) revert TokenTypeNotFound();
        return _tokenUris[tokenId];
    }

    /// @dev ERC-1155 统一状态更新入口；暂停时拒绝操作，不可转移类型只允许铸造和销毁。
    function _update(address from, address to, uint256[] memory ids, uint256[] memory values) internal override {
        if (paused()) revert EnforcedPause();
        if (from != address(0) && to != address(0)) {
            for (uint256 index = 0; index < ids.length; ++index) {
                if (!tokenTypes[ids[index]].transferable) revert NonTransferable();
            }
        }
        super._update(from, to, ids, values);
    }

    /// @dev 只接受 ipfs:// URI，避免把可变 HTTP 地址作为链上 metadata 来源。
    function _validateMetadataUri(string calldata metadataUri) private pure {
        bytes memory value = bytes(metadataUri);
        if (
            value.length <= 7 || value[0] != "i" || value[1] != "p" || value[2] != "f" || value[3] != "s"
                || value[4] != ":" || value[5] != "/" || value[6] != "/"
        ) revert InvalidMetadataUri();
    }

    /// @notice 声明本合约支持 ERC-1155、AccessControl 等接口。
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC1155, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
