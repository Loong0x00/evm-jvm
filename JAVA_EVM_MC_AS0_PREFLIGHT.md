# MC-AS0 immutable artifact-byte store preflight

Status: **measurement/proposal only at `bd128bced`; AS0 is not frozen or
accepted**. VFS0a `72aa13f15` remains the latest accepted LOCAL profile. This
work did not read or execute a Minecraft JAR, parse ZIP, inflate, load a class,
enter `main`, accept an EULA, open a listener, or produce `Done`.

## Measured prototype and proposed contract

The ignored standalone prototype is under
`build/java-diff-mc-as0-preflight/`. It uses unmodified Cancun EVM CREATE,
EXTCODEHASH and EXTCODECOPY. One `ArtifactStore` controller owns one artifact;
there is no deployed page implementation. `append` constructs a 13-byte init
program followed by runtime `STOP || raw`, and the controller itself executes
CREATE. The host only ABI-packs generated opaque bytes, calls EVM, and persists
StateDB/trie roots. It never installs a child page or supplies a ZIP/class
catalogue.

Proposed limits (still subject to parent freeze): length `1..33,554,432`, page
size 8192, at most 4096 pages, read length at most 4096, and a final page exactly
`declaredLength % 8192` (8192 when divisible). This is a separate immutable
store. It does not alter VFS0a's 320KiB LOCAL code allowance, 1MiB checkpoint,
64KiB mutable-file quotas, 100M/30s ordinary calls, or 1B/120s boundary calls.
The preflight stayed under the separate 20min/4GiB watchdog.

Exact proposed production API/state is:

```solidity
constructor(uint32 declaredLength)
append(uint32 expectedCursor, bytes raw, bytes32 expectedPageCommitment) // owner
seal(uint32 expectedCursor, bytes32 expectedChain)                       // owner
read(uint32 offset, uint32 length) view returns (bytes)                  // sealed only
pageCount() view; page(uint256) view returns (address,bytes32,bytes32)
owner, declaredLength, cursor, isSealed, chainCommitment, contentCommitment
```

`sha256Whole` and `StorageByteComparator` are measurement-only and excluded
from that proposal. State is the six scalar lifecycle fields plus ordered
`pages[]`, `codeHashes[]`, and `pageCommitments[]`. No overwrite, upgrade,
caller-selected page address, unsealed read, random append, or post-seal append
exists. Every read checks stored code hash against current EXTCODEHASH before
copying offset `1+pageOffset`; returned bytes therefore come from sealed,
controller-issued immutable code.

## Exact commitment proposal

All encodings below are Solidity `abi.encode` (not packed); integer widths are
shown. Domains are `keccak256` of the quoted ASCII strings.

```text
C0 = keccak256(encode(D("MC-AS0/chain/v1"), controller, owner,
                      uint32(declaredLength), uint32(8192)))
Pi = keccak256(encode(D("MC-AS0/page/v1"), controller, uint32(i),
                      uint32(raw.length), keccak256(raw)))
Hi = extcodehash(page) = keccak256(STOP || raw)
Ci = keccak256(encode(D("MC-AS0/ordered/v1"), Cprev, uint32(i),
                      uint32(raw.length), page, Hi, Pi))
root = keccak256(encode(D("MC-AS0/content/v1"), controller, owner,
                        uint32(declaredLength), uint32(pageCount),
                        uint32(8192), Cfinal))
```

The caller's `expectedPageCommitment` is only a checked transport assertion:
the EVM recomputes `Pi` from actual calldata after CREATE, and only that computed
value enters `Ci`. A mismatch reverts the child too. `seal` requires exact cursor
and computed chain. This root deliberately binds controller/owner/order/length,
issued addresses, code hashes and actual payload hashes. A later JVM profile
must bind controller code identity and this sealed root; future ZIP/resource/
class claims must be derived by EVM reads from these committed raw bytes.

## Reproducible build and artifact measurements

Pinned build: solc `0.8.30+commit.73712a01`, optimizer 200, viaIR, Cancun,
`appendCBOR=false`, `bytecodeHash=none`. Source is 5310B/SHA256
`971cf868854ed0e936c3115093f6806edd098e53372b920cefa766b9b054c9f8`.
Controller init is 3372B/SHA256
`4a599b090078ba6896306ae7b2f54ddc34c5749f42f3896694463668dcc69a0a`;
compiler runtime template is 3046B/SHA256
`396033bb452f3b37a44d0d666a82a8298782dd28055e242e9a61afac89f14dc8`.
The deployed 32MiB immutable-patched runtime is 3046B, SHA256
`af1409160243a2fcfb73dc5939f4fdfd2848b88ef696b01f61d3190556f77fd7`,
Keccak `34d561dec60506a68e7565ce68520e077431c9cc32543d47496b0509c910d66a`.
Ordinary controller CREATE used 632,654 gas. Compile replay took 0.942s and
266,424,320B peak process-group RSS.

A separate storage comparator is 751B runtime (777B init). Writing one random
8192B value to Solidity storage used 5,703,023 gas versus 1,845,181 for the
first data-code page and 1,765,581 steady-state: about 3.09x/3.23x more. Page
runtime is exactly 8193B and fits unchanged EIP-170/initcode bounds.

## Small/adversarial controls

The generated 16KiB control has transport SHA256
`2da1b956bacbe0cbea9ea2a6e8baad2d891b4a5a94491536f60d30dbc46b3dc7`.
A separate declared-8193 control proved a valid 8192+1 partial upload (gas
1,845,181 and 116,292), seal (31,137), and a three-byte cross-page read
(22,796). Zero declared length; zero, short, long and wrong-sized appends;
stale/future cursor; wrong owner; early/wrong-owner/wrong-chain seal; duplicate
seal; append after seal; unsealed, out-of-range and 4097-byte reads all reverted.

A 1,800,000-gas append exhausted gas and a deliberately wrong `Pi` failed only
after child CREATE (1,688,341 gas). For both, the EVM state root, chain root,
page index/count, controller nonce, child code and logs remained unchanged;
retry issued the same child address and exact `STOP || raw`. Thus failure cannot
be recovered from an OOG/revert trace as a published page. Small watchdog:
0.092s/144,871,424B group RSS, no limit hit.

## Full 32MiB result

The full trusted synthetic control is 33,554,432B/4096 pages, transport SHA256
`feb39150a2d007512e7e638b4278f5f007f5cb2db4348a1ecd4de8972e81975e`.
All 4096 ordinary append calls succeeded below 100M: min 1,765,581, max
1,845,181, mean 1,765,651 gas; cumulative (across calls) 7,232,109,376 gas.
Seal used 31,137. First/last page EXTCODEHASH values were
`376b1f743cf6da43678ac0ab9141a54dd6a3c1e0dcdb8699a2fe20df39feae30` and
`2346cfc6dc81adedb77c0c2ade650059fa944258313704abe6bfb169f6d94d5f`.
The ordered chain is
`4b50e19eba3a5a2c8d7ebe0c67a93ef44cd82b006479cab9399970b60bacd5f4`
and sealed root is
`006e3ee443de0bf7f1f9afe36ad821d847cb28a81e17e555a8ed62b26b295801`.
A 4096B read crossing the final page boundary used 24,837 gas and returned
SHA256 `86566f4ec4c1381db7873e21296632b4593f447be5ea8fc776cb7cc7bc5f0c61`.

The hash-scheme trie was committed/reloaded every 256 pages. Final state root is
`89350b704faa31738982052c28bf0fbb915b06fb951754b935954cde5a29f032`;
a clean LevelDB was 40,637,379B after close (1.211x raw bytes, including
controller/index/trie data). A separately launched process reopened that root,
found the 3046B controller and performed the same cross-page EVM read/root
check. Full watchdog replay took 0.707s and 203,202,560B peak group RSS; the
driver reported 0.681s/184,160,256B. No 32MiB capacity blocker was hit.

## SHA-256 scope and unresolved proof choice

Host SHA256 values above pin generated transport only. They are not EVM content
authority and are not the official Minecraft SHA256. AS0 exposes no supplied
SHA256 as authenticated evidence; its first authority is the EVM-computed
Keccak page/ordered root above.

Direct whole-input SHA256 precompile calls measured 5,415 gas for 8192B
(precompile formula alone 3,132) and 2,688,290 for 1MiB (formula 393,276). The
actual 32MiB call exhausted the unchanged 1B boundary gas; the precompile alone
would be only 12,582,972, but one-shot EVM memory expansion has a
2,150,629,376-gas lower component before copy/call overhead. Hashing each page
separately would not equal whole-artifact SHA256; 4096 page digests are not a
streaming SHA state. A future stage must separately choose and prove an EVM SHA
compression-state/continuation design if official whole-JAR verification is
required. This preflight neither invents one nor raises gas.

## Commands and evidence boundary

From repository root:

```sh
cd build/java-diff-mc-as0-preflight
npm install --ignore-scripts --no-audit --no-fund
node compile.js
go build -o as0-preflight .
python3 watch.py 1200 4294967296 small-watch.json bash -c \
 './as0-preflight -pages 2 -db state-small-final >run-small-final.log 2>&1'
python3 watch.py 1200 4294967296 full-final-watch.json bash -c \
 './as0-preflight -pages 4096 -db state-full-final >run-full-final.log 2>&1'
```

Exact reports are ignored `report-{2,4096}.json`; report SHA256 values are
`85d5a5865a7c359a631fbab34b8400b7f20da7827d7b71bc7bbca1dc07d6968d` and
`772674a424601cdabc4ca1313f5381cc806bba91ec38b7683b27fdbf915fffd9`.
Gas is unchanged EVM execution gas from `core/vm/runtime.Create/Call` and excludes
outer signed-transaction intrinsic gas. No production, peer/core, accepted
artifact, setting, or VFS file was changed. Parent replay/review is required
before any API, root, limits, or AS0 acceptance is frozen.
