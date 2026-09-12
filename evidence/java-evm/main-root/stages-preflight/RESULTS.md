# MR0 stages COPY functional run

Run date: 2026-09-12. Base: `752e9d56d`; scoped COPY commit: `9b7ea38e8`.

Fresh command:

```sh
python3 evidence/java-evm/main-root/stages-preflight/reproduce.py \
  build/java-diff-mc-main-root-stages-final
```

Exit 0 in 1.240653386s. The fresh ignored output recorded source SHA-256
`8e265b06f258656ef2dc9032e9954ee25691a845e919fce892d53ef3fafb37fe` and opaque
fixture SHA-256 `b9cea32d8f72f007c329eb1eccded4a2a420153039be963c735c14a980d64a0e`.

The owned `manifest-before-create` initial-factory fault returned nonzero and
left no `durable-head.json`. Eight separate binary invocations then observed:

| operation | durable phase | root |
|---|---|---|
| factory-initial | input-open | `0x712630a465ebdadd79f2be6ec25be4ec69df4f2326ee11125c927a3aa7a6f00c` |
| as0-input | as0-final | `0xcdb5b46be475976f27bfed56166dfde8cd79ad0277062f6b164cbbecba6973ca` |
| index-scan | index-final | `0xbfe1d8ca166efe9d31e21920e0c43751546732e35f07f0fbe86c854aeaacc43a` |
| di0-live | di0-live | `0x98cb4541b64db6e3d43e78051948e4f90c4c996473a4794c5b8c710ad6bcdf17` |
| di0-final | resources-final | `0x3c059d029d3f77d3810d649cb111ff35bead11aa350326812d9d73c25d5661ea` |
| package-ready | coordinator-ready | `0x95113625644147f43d599020b3fd73c6ebe75fb350eabd63cff63999b131b15d` |
| start-ready | java-running epoch1 | `0xfbbf8616cefa49b20dc3dac7500322628fa7db91ff8b0a93a7913918198a2473` |

The first Head has the exact pinned LOCAL engine at nonce zero and AS0 at
ordinary owner nonce zero's CREATE address; `verify-initial` is a distinct
reopen. Follow-up `finish`, `verify`, and `go vet .` completed on the same fresh
binary: terminal epoch319, lifecycle2, phase `java-terminal`.

This is a functional COPY preflight. It is not a parent independent rebuild,
whole-group resource gate, atomicity-fault rerun, full Session acceptance, or a
claim that the incomplete phase validation listed in the preflight is complete.
