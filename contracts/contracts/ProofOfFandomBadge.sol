// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ERC1155} from "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";

/// @title Proof of Fandom Badge
/// @notice Non-transferable fan identity badges managed by authorized Fanora operators.
contract ProofOfFandomBadge is ERC1155, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant URI_MANAGER_ROLE = keccak256("URI_MANAGER_ROLE");

    error Soulbound();

    constructor(address admin, string memory initialUri) ERC1155(initialUri) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(URI_MANAGER_ROLE, admin);
    }

    function mint(address account, uint256 badgeId) external onlyRole(MINTER_ROLE) {
        _mint(account, badgeId, 1, "");
    }

    function upgrade(address account, uint256 currentBadgeId, uint256 nextBadgeId)
        external
        onlyRole(MINTER_ROLE)
    {
        _burn(account, currentBadgeId, 1);
        _mint(account, nextBadgeId, 1, "");
    }

    function setBaseUri(string calldata newUri) external onlyRole(URI_MANAGER_ROLE) {
        _setURI(newUri);
    }

    function _update(
        address from,
        address to,
        uint256[] memory ids,
        uint256[] memory values
    ) internal override {
        if (from != address(0) && to != address(0)) revert Soulbound();
        super._update(from, to, ids, values);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC1155, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}

