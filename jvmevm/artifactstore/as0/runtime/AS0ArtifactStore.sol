// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

error AS0Error(uint256 code);

/// One immutable, sequentially-issued artifact backed by EVM-created data code.
/// Child runtime code is exactly STOP || raw page bytes.
contract AS0ArtifactStore {
    uint32 public constant PAGE_SIZE = 8192;
    uint32 public constant MAX_PAGES = 4096;
    uint32 public constant MAX_LENGTH = 33554432;

    bytes32 private constant INIT_DOMAIN = keccak256("MC-AS0/chain/v1");
    bytes32 private constant PAGE_DOMAIN = keccak256("MC-AS0/page/v1");
    bytes32 private constant CHAIN_DOMAIN = keccak256("MC-AS0/ordered/v1");
    bytes32 private constant FINAL_DOMAIN = keccak256("MC-AS0/content/v1");

    // These instance bindings deliberately remain constructor-written storage.
    // They are not Solidity immutables, so every instance has identical runtime code.
    address public owner;
    uint32 public declaredLength;

    uint32 public cursor;
    bool public isSealed;
    bytes32 public chainCommitment;
    bytes32 public contentCommitment;

    address[] private pages;
    bytes32[] private codeHashes;
    bytes32[] private pageCommitments;

    event PageIssued(
        uint32 indexed index,
        address indexed page,
        uint32 length,
        bytes32 codeHash,
        bytes32 pageCommitment,
        bytes32 chainCommitment
    );
    event Sealed(uint32 length, uint32 pages, bytes32 contentCommitment);

    constructor(uint32 length) {
        if (length == 0 || length > MAX_LENGTH) revert AS0Error(1);
        if (msg.sender == address(0)) revert AS0Error(2);

        owner = msg.sender;
        declaredLength = length;
        chainCommitment = keccak256(
            abi.encode(INIT_DOMAIN, address(this), msg.sender, length, PAGE_SIZE)
        );
    }

    function pageCount() external view returns (uint256) {
        return pages.length;
    }

    function page(uint256 index) external view returns (address, bytes32, bytes32) {
        if (index >= pages.length) revert AS0Error(11);
        return (pages[index], codeHashes[index], pageCommitments[index]);
    }

    /// expectedPageCommitment is a transport assertion. The EVM computes the
    /// authoritative page commitment from the actual calldata.
    function append(
        uint32 expectedCursor,
        bytes calldata raw,
        bytes32 expectedPageCommitment
    ) external {
        if (msg.sender != owner) revert AS0Error(2);
        if (isSealed) revert AS0Error(3);
        if (expectedCursor != cursor) revert AS0Error(4);

        uint256 remaining = uint256(declaredLength) - cursor;
        uint256 wanted = remaining < PAGE_SIZE ? remaining : PAGE_SIZE;
        // Reject at-full empty appends before CREATE. Otherwise a STOP-only child
        // could change the controller nonce/page chain without advancing cursor.
        if (
            remaining == 0 ||
            raw.length == 0 ||
            raw.length != wanted ||
            pages.length >= MAX_PAGES
        ) revert AS0Error(5);

        uint32 index = uint32(pages.length);
        bytes32 pageCommitment = keccak256(
            abi.encode(
                PAGE_DOMAIN,
                address(this),
                index,
                uint32(raw.length),
                keccak256(raw)
            )
        );

        // PUSH2 size; PUSH2 0x000d; PUSH0; CODECOPY;
        // PUSH2 size; PUSH0; RETURN; STOP; raw.
        bytes memory init = bytes.concat(
            hex"61",
            bytes2(uint16(raw.length + 1)),
            hex"61000d5f3961",
            bytes2(uint16(raw.length + 1)),
            hex"5ff300",
            raw
        );
        address child;
        assembly ("memory-safe") {
            child := create(0, add(init, 0x20), mload(init))
        }
        if (child == address(0)) revert AS0Error(6);

        bytes32 codeHash;
        assembly ("memory-safe") {
            codeHash := extcodehash(child)
        }
        if (codeHash != keccak256(bytes.concat(hex"00", raw))) {
            revert AS0Error(7);
        }

        // Deliberately after CREATE: a failed caller assertion proves outer-call
        // rollback also removes the newly created child, nonce, storage and log.
        if (pageCommitment != expectedPageCommitment) revert AS0Error(8);

        bytes32 nextChain = keccak256(
            abi.encode(
                CHAIN_DOMAIN,
                chainCommitment,
                index,
                uint32(raw.length),
                child,
                codeHash,
                pageCommitment
            )
        );
        pages.push(child);
        codeHashes.push(codeHash);
        pageCommitments.push(pageCommitment);
        cursor += uint32(raw.length);
        chainCommitment = nextChain;

        emit PageIssued(
            index,
            child,
            uint32(raw.length),
            codeHash,
            pageCommitment,
            nextChain
        );
    }

    function seal(uint32 expectedCursor, bytes32 expectedChain) external {
        if (msg.sender != owner) revert AS0Error(2);
        if (isSealed) revert AS0Error(3);

        uint256 exactPages = (uint256(declaredLength) + PAGE_SIZE - 1) / PAGE_SIZE;
        if (
            expectedCursor != declaredLength ||
            cursor != declaredLength ||
            pages.length != exactPages
        ) revert AS0Error(9);
        if (expectedChain != chainCommitment) revert AS0Error(10);

        isSealed = true;
        contentCommitment = keccak256(
            abi.encode(
                FINAL_DOMAIN,
                address(this),
                owner,
                declaredLength,
                uint32(pages.length),
                PAGE_SIZE,
                chainCommitment
            )
        );
        emit Sealed(declaredLength, uint32(pages.length), contentCommitment);
    }

    function read(uint32 offset, uint32 length) external view returns (bytes memory out) {
        if (!isSealed) revert AS0Error(12);
        if (length > 4096 || uint256(offset) + length > declaredLength) {
            revert AS0Error(13);
        }

        out = new bytes(length);
        uint256 done;
        while (done < length) {
            uint256 absolute = uint256(offset) + done;
            uint256 pageIndex = absolute / PAGE_SIZE;
            uint256 pageOffset = absolute % PAGE_SIZE;
            uint256 take = PAGE_SIZE - pageOffset;
            if (take > length - done) take = length - done;

            address child = pages[pageIndex];
            bytes32 actualCodeHash;
            assembly ("memory-safe") {
                actualCodeHash := extcodehash(child)
            }
            if (actualCodeHash != codeHashes[pageIndex]) revert AS0Error(14);
            assembly ("memory-safe") {
                extcodecopy(
                    child,
                    add(add(out, 0x20), done),
                    add(pageOffset, 1),
                    take
                )
            }
            done += take;
        }
    }
}
