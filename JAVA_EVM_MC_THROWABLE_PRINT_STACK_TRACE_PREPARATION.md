# Java-on-EVM Minecraft bounded Throwable.printStackTrace(PrintStream) preparation

Accepted `parent-2e155e0f6` runs unchanged original38 through PrintStream char sink to65279J/50I in26 successful LOCAL4.2B/q4096 blocks. Exact blocker is `SimpleLogger.logMessage` PC273 invoking `Throwable.printStackTrace(PrintStream)` on a non-null status throwable.

Replace only bootstrap image5 Throwable to add bounded message-only output: for non-null detailMessage call the measured PrintStream.println(String) sink; null detailMessage performs no write. Preserve constructors/getMessage/getCause, all other90 images/order/runtime-derived root with changed Throwable hash derived from exact bytes,raw38/285489,diagnostic129,native13,and all limits/toolchain/semantics. No class name, frames, causes, suppressed exceptions, or host output claim.

## Dynamic image5 layout and LOCAL2 gate

The direct char-sink parent plus the exact 657-byte Throwable image measured
**393608** runtime bytes in the unshared layout, above the fixed 393216-byte
cap. The selected source retains runtime-derived image5:
`h[5] = keccak256(_bootstrapThrowable())`. It does **not** add
`DBOOT_THROWABLE`. A private fixed-length unreachable recursion guard is placed
after materializing the exact image literal; its 657-byte length cannot equal
`uint256.max`, so it cannot execute, while avoiding duplicate private-literal
inlining. Existing inherited finite-loop layout is byte-identical.

The verifier rederives the image Keccak-256
`ad47871098a702ae866f30543bb5adf023c9be6abad8e0e6233a4ca652b2db9d`
from `bootstrap/java/lang/Throwable.class.hex`, parses its fields and method
Code, and rederives ordered root
`aa305076f7f9b82315960468bad942e1f425553ee31ca08b6d5729fa91bf7feb`.
It proves image5 is the sole changed leaf relative to the accepted PrintStream
char-sink parent: `h[0]` and every other inherited leaf remain runtime-derived.

Pinned solc rebuild: **389150 / 393216** runtime bytes (4066-byte headroom),
SHA-256 `e5b64de8b7fea6b62f6dc4f29a147c8325d7034ccffdd1e538a42376070b491a`,
Keccak-256 `809bbcb06332ac40cc774390022348257438f6e043228e2d810ee44c126edd57`.
The generated-only LOCAL2 gate passed in **629.098s** (<1200s), with **10412**
independently canonicalized receipts across focused nonnull/null sink,
q1/q7/direct/reopen, and retained controls. It uses no original artifact,
provider factory, world, or Done input or claim; parent owns accelerated
unchanged-original replay.
