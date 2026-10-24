# Pinned compiler stack relief — supplied source-only guidance

Exact solc0.8.30 optimizer200 viaIR Cancun metadata-off compiles the correct120-image assembly. Runtime441398B, source hash and result pins in validation.json. Existing external ABI/storage layout are exact; old117 class bytes/order are exact. No originals were used.

Use baseline startMain/resumeMain/_commit/_encodeEnvelope, not accumulated failed rewrites. The only extra compiler refactor is _configRoot + internal ConfigRootEncoding struct. ABI of one dynamic struct adds a leading offset32; hash payload data AFTER that word to preserve the original13-field flat tuple commitment. Field order/types are exact.512 generated ABI vectors including empty/nonempty/NUL/UTF8 strings and signed-int32 extrema passed byte-for-byte flattening. This is compile/encoding evidence only, not guest/EVM acceptance; fresh codehash/coordinator/gates still required.

Before applying, preserve the current candidate and all failed versions. Never continue a wrong119-layout or other-code checkpoint. Keep compiler/bounds/budgets/ABI unchanged; generated1B30s first, actual finite shortages only.
