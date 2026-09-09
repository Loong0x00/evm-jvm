# Stock S2b-L runtime

This directory is the production runtime write set for the frozen S2b-L
registration/link slice. It contains only:

- `S2bAnalyzeModule`: EVM-side Java 52 class parsing, immutable Phase-A method
  envelopes, body predecode/link/flow analysis, and schema-4 literal/call caches.
  Definite-local flow uses a code-length FIFO ring plus a 256-bit in-queue set,
  so stricter joins can re-enqueue without an unbounded linear queue.
- `S2bClassLinker`: append-only issuance, canonical bounded analyzer-return
  decoding, real-count idempotence, and the pinned S2a registry reparse adapter.
- `S2bMetadataPage`: constructor-only `STOP || payload` metadata pages.

There is no executor, frame store, continuation coordinator, Java call execution,
or host-derived metadata path in this slice. A call record is registration/link
evidence only. Body failure of a Phase-A-usable target does not invalidate a
symbolic caller cache; only an unusable declaration envelope does.

## Reproducible build

The build is closed over the four Solidity files in this directory. It uses the
pinned lock file and requires exactly solc
`0.8.30+commit.73712a01.Emscripten.clang`, optimizer 200, via-IR, Cancun, with
compiler metadata disabled.

```sh
cd jvmevm/stock/s2b/runtime
npm ci
npm run build
npm run check
```

Generated artifacts contain ABI, creation bytecode, runtime template bytecode,
immutable references, compiler settings, and SHA-256 hashes for every source.
No classfile or test catalogue is a compiler input.

Pinned artifact measurements:

| Contract | init bytes | max encoded init bytes | runtime bytes | init SHA-256 | runtime-template SHA-256 |
|---|---:|---:|---:|---|---|
| S2bMetadataPage | 339 | 8595 | 3 | `34ab89bdbd1080a108b1629ea26c8beb2605adff7dbc028b129ff91a8455aa9f` | `0668b20e4ee135e7cac4091998933a5123658a8e777994fdb4b4ee2d553e6438` |
| S2bAnalyzeModule | 18568 | 18568 | 18542 | `07af409d91be94fed59e2f54fbd7b52790d50f4f0b9aa8fc28dbed4322192c2a` | `9ed5907864695906252b2fce0831d8e07ee6bc4fda6dfaef40d20617cd61181f` |
| S2bClassLinker | 4911 | 5007 | 4588 | `dbf0e6394e85efefbb6fe5fbff99ebc8e416a9876d85a030d34888bca83574ed` | `ff89456d81f1b1c5c9bb18a6b48372f17a8f8b2170fee64b7d4511d25fd7ed7c` |

The analyzer runtime Keccak-256 is
`7dd80390b865891ff1c5f8fe9e067131231252dfd1a45939182c25a844133d45`;
this actual `EXTCODEHASH` is written to schema-4 H6. The linker artifact runtime
is a template: its deployed code and code hash depend on the three constructor
immutables and must be reconstructed using `immutableReferences`. Metadata-page
artifact runtime is likewise only the unreachable constructor template; an
issued runtime is exactly `STOP || schema4Payload`.

Limits enforced by the build are analyzer runtime <=20 KiB, linker/page template
runtime <=12 KiB, and each maximum encoded initcode <=24 KiB. The analyzer and
linker also enforce raw page <=4097 runtime bytes, metadata page <=7937 runtime
bytes, and canonical analyzer returndata <=8096 bytes.

## Local bounded evidence

The implementation was checked in an ignored diagnostic directory against the
read-only parser-preflight corpus. Ordinary signed transaction application on
chain 1337 registered all 14 classes and preserved 51 call records
(14/16/21 in the three M3a classes). The unchanged cap class had SHA-256
`0e3e962a3de46d9c019c8e8e3e846b304622fc969144713f9ad6922c33946f33`,
3574 raw bytes, 32 methods, 256 literals, 32 calls, and 7936 metadata bytes.
First direct registration used 7,668,234 gas at an 8,000,000 transaction limit;
first S2a-adapter registration used 7,680,072 gas at the same limit. Adapter and
direct retry returned the same six fields and real counts; retry used 42,310 gas.

These measurements do not execute any Java call and are not evidence for frames,
the 268-row execution catalogue, arbitrary Java, or Minecraft startup.
