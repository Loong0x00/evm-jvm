# P45 Comparator interface append — recovery/status

## Completed in this recovery

- Preserved the interrupted seven-file uncommitted candidate, byte-for-byte, in `../comparator-interface-link-interrupted-draft-20261023T122852Z/` before editing the live candidate. The initially attempted nested archive copy failed because it targeted itself; the successful sibling archive is the durable one. Source-base integrity was checked against all nine manifest lengths and hashes before work.
- Rebased the fresh build on the authoritative P44 source snapshot, not cached build artifacts. Preserved P44's 107-image prefix and appended the Comparator image at bootstrap index 107; guarded the raw Comparator namespace.
- Changed the DBOOT profile domain and all coordinator P45 domains, and bound the coordinator to the freshly compiled P45 engine runtime hash. Coordinator ABI/storage are not intentionally changed.
- Fresh pinned-solc builds succeeded. Engine runtime: 422008 bytes, SHA-256 `848bcc58408b9eda44a2d76575d65e40d8aed38abdc85ff1c13bcb6b79dcd1ac`, Keccak `31e1a12737c20987b6e81a9d07026ea0c9419f07cc49ef4dd7405c02854ae979`. Coordinator runtime: 5411 bytes, SHA-256 `6239e5af71c6c1bc82df8271c717c095c70b83c82b2b5c686c302422e4afd33a`, Keccak `72187c45559fece2b443d476758313f3ba08987415ae14ed94c9d36c7ca6a4f9`.
- Computed 108 ordered bootstrap leaves and P45 root `144cde506d6586c46aed4a6c1279554835ae3029e8cbef342b995866138547a7`; Comparator leaf 107 is `918215e61bb2b2c5fbccc882fe545a6fd409b2eb94e445a972d130dcdf216670`.
- `javap` confirmed the retained 256-byte bootstrap image is major version 52, public abstract interface, generic Comparator, with abstract `compare(Object,Object):int` and `equals(Object):boolean`. A Java 8 source probe compiled, but its full classfile differs because it contains compiler/source attributes; it is retained separately as provenance, not substituted for the deliberately minimal bootstrap image.

## Not verified / not claimed

The fresh genuine geth-EVM gates remain UNRUN: custom implementation results and bridges; null/wrong-type typed exceptions; instanceof/checkcast/subinterface behavior; Comparator[] clone/high index 257 and metadata `0x201`; raw150+108 bounds; q1/q7/coarse exact machine/VFS/counters/heap-root equality; fresh-process reopen; and atomic refusal for omitted helpers or raw Comparator replacement. No original Minecraft replay was performed. Therefore this recovery is an implementation/build checkpoint, not P45 acceptance and not evidence that the original Minecraft replay advanced.

The fresh EVM gates must use these newly built artifacts and must audit source prefix/order, actual image bytes, ABI/storage widths, unchanged caps, and the P45 codehash relationship. Parent remains responsible for independent review and original replay.
