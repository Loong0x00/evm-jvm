# Result: generated `System.identityHashCode(Object)`

- Added only exact public static native `System.identityHashCode(Object)I` and global binding17. Null is zero; every valid non-null guest reference returns its stable low-uint32 heap handle with no Object.hashCode dispatch, allocation, or state mutation.
- Rebuilt only bootstrap System: 1113 bytes, SHA-256 `6e29f00abed753017741ad667314982061178298cb3fca5baa0d92f2f9d57564`, leaf44 Keccak `1850d01a1f91f51d1e7e8e82de2f92ceb319a879d52b77f8892b237e5188eef3`. The independently folded bootstrap96 root is `6fbfed767949708bacc0aebb58173f63c46bfd0b84cb0c5ac3a15f461c8a4a77`.
- Preserved raw70/464925, diagnostic166, String-local12, all non-System bootstrap images (including String/Locale/Map.Entry/Integer), and System out/err setter isolation. Runtime is 380017/393216 bytes.
- Full generated q1/q7/direct/reopen plus retained/capacity gate passed in 190.03612493805122 seconds (limit 1200), with 2227 canonical receipts. Results and SHA256SUMS are durable under `results/` and this stage.

No original/JAR/resource/network/provider/world/EULA/Done input or claim. Parent genuine replay is deferred.
