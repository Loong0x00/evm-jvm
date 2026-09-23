# MC `java.util.Random` image97 preflight

This generated-only stage appends Java 8 `java/util/Random` as bootstrap image97. The class is deliberately limited to the public no-argument constructor: it has no fields, seed/state, RNG methods, host-time behavior, or other Random API semantics. The previous 96 bootstrap images, including the `Math.sqrt` image, are retained byte-for-byte.

`results/` contains the successful final generated gate and canonical receipt summary. `tools/verify_source.py` checks the Java 8 image, exact one-image append, unchanged prior leaves, ordered bootstrap root, source edits, and build pins. `tools/verify_results.py` checks the archived fixture/gate summaries, retained controls, refusal cases, receipts, and result-file hashes. The receipt checker covers canonical ABI/events/checkpoint and counter data; it is not full Session acceptance.

- Gate: 182 commands, 2,930 verified canonical receipts, 241.277286598 seconds (1,200-second limit).
- Engine image: 383,245 bytes (393,216-byte local cap).
- Bootstrap root: `7e17be3151d9b2aa8b0fd0686069824995e772be6a4a6b41876ee4918812e887`.
- Random class SHA-256: `8d2a1e974c79f6a2a0344a5c776f5feb7b7f09eb7431bd02d54d75518bf76bf3`.

No original class, JAR, resource, network input, provider, world, or EULA data was opened or executed. This is not a Minecraft replay or readiness claim; parent independent rebuild/gate and genuine replay remain separate.
