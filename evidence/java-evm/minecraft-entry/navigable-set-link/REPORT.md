# P45 NavigableSet hierarchy-link implementation (source-only candidate)

Base: branch `java-navigable-set-link`, accepted P45 source commit `8bdbf24d6ccf2cfc5ab30df8dc1733240994d51c`. The exact nine-file P45 source baseline manifest was checked before editing: all listed lengths and SHA-256 values matched. Its actual 108-image root independently recomputed to `7796c48c62a0f714f39b5dcb38b110dd84f98d01992806a7c92ddfb08f45a7dd`.

## Change

Appended two genuine minimal Java 8 generic interface images, produced by `/usr/lib/jvm/java-8-openjdk/bin/javac -source 8 -target 8 -g:none`:

* bootstrap 108 / internal class index 258 at raw count 150: `java/util/SortedSet<E> extends java/util/Set<E>` (175 bytes; SHA-256 `c20a858a01f5e059d77072f913e40885aa76af718dfe2837151149741318e6dd`; Keccak `d24cc68f2a382d825790319b450cd5990fe9f492b0e0b25bc5eb5cdff5200b9e`).
* bootstrap 109 / internal class index 259 at raw count 150: `java/util/NavigableSet<E> extends java/util/SortedSet<E>` (190 bytes; SHA-256 `2ca600cc6a8e669c9e1ee0bb92fe4b8a8515e2c46c9de0779b3d3b56f28bf907`; Keccak `752b50ac382ac1d2afb5460b547c0d4b45b17d82989c47309339cf2c2ecb9950`).

No collection or navigation methods are defined. Existing 108 image bytes/root leaves remain exactly unchanged; new root is `757e01b7866b698d05ccc88846659f750aae4bb0030dd678bab6761cc69de156`. Raw uploads with either reserved platform name are rejected. New actual EVM runtime is 423747 bytes, SHA-256 `19a612b28b26d5d9a3bf470318417cf01f980f7d014e1905aa27a4768d437200`, Keccak `74d9fe8f41f15b889fdbbe59abda76a8555e70d9e2cc5ba91893de063090c6d7`. The derivative coordinator authenticates that exact engine hash; its runtime is 5411 bytes, Keccak `222e90b020321a01c542614ea8a5c7a80ed6bf1485d14dcc6861ce177a687d1c`.

All stated ABI/storage widths and ceilings remain P45 values: raw class count 150 / raw bytes 1,063,930; checkpoint 2 MiB; 25M commit reserve; runtime 1 MiB; frames 128; q=65536; internal=4096; native binding 21 and String-local binding 12. At maximum raw count, bootstrap IDs 108/109 map to class indices 258/259 and array leaf metadata `0x202`/`0x203`; the next raw index 150 would map to internal index 260. No wire/index width or coordinator raw count was widened.

## Verification and limits

* Baseline source manifest file lengths/SHA-256: pass.
* Java 8 image compile, `javap -v` checks (`ACC_PUBLIC, ACC_INTERFACE, ACC_ABSTRACT`, exact generic extends signatures, no methods): pass. `-g:none` yields the exact embedded 175/190-byte images; source-to-image equality is checked by `reference/verify_source.py`.
* Exact root derivation and P45 108-leaf prefix equality: pass (`reference/verify_source.py`).
* Fresh pinned solc 0.8.30 `viaIR` builds for engine and coordinator: pass. Engine is intentionally a LOCAL oversized runtime, not standard deployment compatible.
* Genuine EVM behavior tests (instanceof/checkcast/dispatch/null/wrong-type/typed arrays+clone at 258/259, q1/q7/high-raw, and fresh-process checkpoint reopen) were not run in this worker. This remains an unaccepted implementation candidate pending parent-owned independent EVM gates and fresh original replay. No original Minecraft classes/JAR, worlds, receipts, or external payloads were used.

Reproduction: from repository root, `JAVA_HOME=/usr/lib/jvm/java-8-openjdk sh evidence/java-evm/minecraft-entry/navigable-set-link/java-src/build-images.sh`; then run `reference/verify_source.py` with `NODE_PATH=/home/user/evm-jvm/navigable-set-link/jvmevm/runtime/node_modules`, and run the two `build.js` scripts with the same `NODE_PATH`. Generated Solidity artifacts are reproducible intermediates and intentionally not part of the scoped source commit.
