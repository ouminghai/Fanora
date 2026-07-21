// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {IERC1155Receiver} from "@openzeppelin/contracts/token/ERC1155/IERC1155Receiver.sol";
import {IERC165} from "@openzeppelin/contracts/utils/introspection/IERC165.sol";

interface IFanoraCollectibles {
    /// @notice 测试所需的最小收藏品铸造接口。
    function mintCollectible(address account, uint256 tokenId, uint256 amount, bytes32 claimKey) external;
}

/// @title 恶意 ERC-1155 接收器测试合约
/// @notice 在收到收藏品的回调中尝试再次铸造，用来验证领取键和供应限制能阻止重入重复领取。
/// @dev 仅用于自动化测试，不应部署到生产环境，也不属于 Fanora 业务合约。
contract MaliciousCollectibleReceiver is IERC1155Receiver {
    /// @notice 被测试的 FanoraCollectibles 合约。
    IFanoraCollectibles public immutable collectibles;
    /// @notice 首次接收后尝试再次铸造的 tokenId。
    uint256 public immutable tokenId;
    /// @notice 重入尝试使用的领取键。
    bytes32 public immutable claimKey;

    /// @param collectiblesAddress 被测试的收藏品合约地址。
    /// @param collectibleTokenId 重入时尝试领取的 tokenId。
    /// @param reentryClaimKey 重入时使用的 claimKey。
    constructor(address collectiblesAddress, uint256 collectibleTokenId, bytes32 reentryClaimKey) {
        collectibles = IFanoraCollectibles(collectiblesAddress);
        tokenId = collectibleTokenId;
        claimKey = reentryClaimKey;
    }

    /// @notice 单个 ERC-1155 token 接收回调。
    /// @dev 回调中故意尝试再次铸造；预期失败会被 catch，随后返回标准接收选择器。
    function onERC1155Received(address, address, uint256, uint256, bytes calldata) external returns (bytes4) {
        try collectibles.mintCollectible(address(this), tokenId, 1, claimKey) {} catch {}
        return this.onERC1155Received.selector;
    }

    /// @notice 批量 ERC-1155 token 接收回调，直接确认接收。
    function onERC1155BatchReceived(address, address, uint256[] calldata, uint256[] calldata, bytes calldata)
        external
        pure
        returns (bytes4)
    {
        return this.onERC1155BatchReceived.selector;
    }

    /// @notice 声明支持 ERC-1155 Receiver 和 ERC-165 接口。
    function supportsInterface(bytes4 interfaceId) external pure returns (bool) {
        return interfaceId == type(IERC1155Receiver).interfaceId || interfaceId == type(IERC165).interfaceId;
    }
}
