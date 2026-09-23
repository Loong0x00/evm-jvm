#!/usr/bin/env python3
"""Offline sizing/encoding oracle for generated-only float checkpoint controls.

This is deliberately a TEST-ONLY model. It neither reads nor writes EVM state.
"""
import argparse
import hashlib
import json
import pathlib
import struct
import sys

PACKED_FLOAT_FLAG = 1 << 30
SPARSE_PAIR_FLAG = 1 << 31
KNOWN_FLAGS = PACKED_FLOAT_FLAG | SPARSE_PAIR_FLAG
MIN_PACKED_LENGTH = 1024
EXPECTED_FIXTURES = {
    "float-16-small.u32be": (16, 8),
    "float-1024-sparse.u32be": (1024, 32),
    "float-1024-dense.u32be": (1024, 400),
    "float-65536-sparse.u32be": (65536, 128),
    "float-65536-dense.u32be": (65536, 30000),
}
SPECIALS = (0x80000000, 0x7FC00001, 0x7FC12345, 0xFFC54321, 0x7F800000, 0xFF800000)
EXPECTED_REFERENCES = ["alpha", None, "alpha", "guest", ""]
EXPECTED_LONGS = [
    0x0000000000000000,
    0x0000000000000001,
    0xFFFFFFFFFFFFFFFF,
    0x8000000000000000,
    0x7FFFFFFFFFFFFFFF,
    0x00000001FFFFFFFF,
    0x7FF8000000000042,
    0x8000000000000000,
]


class Refusal(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read_u32be(path):
    raw = path.read_bytes()
    require(len(raw) % 4 == 0, f"{path.name}: byte length is not a multiple of four")
    return [item[0] for item in struct.iter_unpack(">I", raw)]


def count_nonzero(cells):
    return sum(1 for cell in cells if cell != 0)


def sizes(length, nonzero):
    return {
        "oldSparseU32IndexU64Value": 4 + 12 * nonzero,
        "packedFloatU32": 4 * length,
        "denseU64": 8 * length,
    }


def old_format_choice(length, nonzero):
    size = sizes(length, nonzero)
    return "old-sparse-u32-index-u64-value" if size["oldSparseU32IndexU64Value"] < size["denseU64"] else "dense-u64"


def canonical_choice(length, cells):
    nonzero = count_nonzero(cells)
    size = sizes(length, nonzero)
    if length >= MIN_PACKED_LENGTH and size["packedFloatU32"] < size["oldSparseU32IndexU64Value"]:
        return "packed-float-u32"
    return old_format_choice(length, nonzero)


def pack_u32_cells(cells):
    out = bytearray()
    for cell in cells:
        if not isinstance(cell, int) or cell < 0 or cell > 0xFFFFFFFF:
            raise Refusal("float cell has bits outside u32")
        out.extend(struct.pack(">I", cell))
    return bytes(out)


def decode_packed(payload, length, kind, flags):
    if kind != "float":
        raise Refusal("packed flag is restricted to primitive float arrays")
    if flags != PACKED_FLOAT_FLAG or flags & ~KNOWN_FLAGS:
        raise Refusal("malformed or combined packed flags")
    if length < MIN_PACKED_LENGTH:
        raise Refusal("packed float array is below minimum length")
    if len(payload) != 4 * length:
        raise Refusal("packed payload length mismatch")
    cells = list(struct.unpack(">" + "I" * length, payload))
    if canonical_choice(length, cells) != "packed-float-u32":
        raise Refusal("packed encoding is not the strict canonical size winner")
    # Explicit u64 reconstruction check: every decoded cell is the original u32 value.
    reconstructed_u64 = [cell & 0xFFFFFFFF for cell in cells]
    if reconstructed_u64 != cells:
        raise Refusal("decoded float cell exceeds u32")
    return reconstructed_u64


def encode_old_sparse(cells):
    pairs = [(index, value) for index, value in enumerate(cells) if value != 0]
    out = bytearray(struct.pack(">I", len(pairs)))
    for index, value in pairs:
        if value < 0 or value > 0xFFFFFFFFFFFFFFFF:
            raise Refusal("old sparse value outside u64")
        out.extend(struct.pack(">IQ", index, value))
    return bytes(out)


def decode_old_sparse(payload, length, expected=None, require_canonical=False):
    if len(payload) < 4:
        raise Refusal("old sparse header truncated")
    count = struct.unpack_from(">I", payload, 0)[0]
    if count > length or len(payload) != 4 + 12 * count:
        raise Refusal("old sparse count/payload length mismatch")
    cells = [0] * length
    previous = -1
    offset = 4
    for _ in range(count):
        index, value = struct.unpack_from(">IQ", payload, offset)
        offset += 12
        if index >= length or index <= previous or value == 0:
            raise Refusal("old sparse indices/values are malformed")
        cells[index] = value
        previous = index
    if expected is not None and cells != expected:
        raise Refusal("old sparse contents mismatch expected raw cells")
    if require_canonical and canonical_choice(length, cells) != "old-sparse-u32-index-u64-value":
        raise Refusal("old sparse record is no longer canonical")
    return cells


def expect_refusal(label, fn):
    try:
        fn()
    except Refusal as exc:
        return {"case": label, "refused": True, "reason": str(exc)}
    raise AssertionError(f"refusal control unexpectedly accepted: {label}")


def crossover(length):
    # Strict inequality: 4*length < 4 + 12*n.
    threshold = ((4 * length - 4) // 12) + 1
    below = sizes(length, threshold - 1)
    at = sizes(length, threshold)
    require(below["packedFloatU32"] == below["oldSparseU32IndexU64Value"],
            f"length {length}: expected exact tie immediately below crossover")
    require(at["packedFloatU32"] < at["oldSparseU32IndexU64Value"],
            f"length {length}: expected packed strict win at crossover")
    require(canonical_choice(length, [0] * (length - threshold) + [1] * threshold) == "packed-float-u32",
            f"length {length}: packed must win at exact threshold")
    return {
        "length": length,
        "strictFirstPackedNonzeroCount": threshold,
        "tieAtCount": threshold - 1,
        "tieBytes": below["packedFloatU32"],
        "firstWinSparseBytes": at["oldSparseU32IndexU64Value"],
        "firstWinPackedBytes": at["packedFloatU32"],
    }


def verify_class_major(class_file):
    raw = class_file.read_bytes()
    require(len(raw) >= 8 and raw[:4] == b"\xca\xfe\xba\xbe", "generator class is not a JVM class file")
    major = struct.unpack_from(">H", raw, 6)[0]
    require(major == 52, f"generator bytecode major is {major}, expected Java 8 (52)")
    return major


def run(fixtures_dir, class_file):
    fixtures_dir = pathlib.Path(fixtures_dir)
    manifest_path = fixtures_dir / "oracle.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["schema"] == "generated-java8-float-bits-v1", "unexpected fixture schema")
    require(manifest["floatEncoding"] == "Float.floatToRawIntBits, big-endian u32", "unexpected float oracle encoding")
    entries = manifest["floatFixtures"]
    require([entry["file"] for entry in entries] == list(EXPECTED_FIXTURES), "float fixture inventory/order changed")

    fixture_reports = []
    raw_hashes = {}
    cells_by_file = {}
    for entry in entries:
        filename = entry["file"]
        path = fixtures_dir / filename
        raw = path.read_bytes()
        cells = read_u32be(path)
        expected_length, expected_nonzero = EXPECTED_FIXTURES[filename]
        require(len(cells) == expected_length == entry["length"], f"{filename}: length mismatch")
        nonzero = count_nonzero(cells)
        require(nonzero == expected_nonzero == entry["nonzeroRawBits"], f"{filename}: nonzero raw-bit count mismatch")
        require(cells[:len(SPECIALS)] == list(SPECIALS), f"{filename}: special raw IEEE-754 cells changed")
        require(any(cell == 0 for cell in cells), f"{filename}: missing +0.0 raw bits")
        require(any(cell == 0x80000000 for cell in cells), f"{filename}: missing -0.0 raw bits")
        require(any((cell & 0x7F800000) == 0x7F800000 and (cell & 0x007FFFFF) != 0 for cell in cells),
                f"{filename}: missing NaN payload")
        require(0x7F800000 in cells and 0xFF800000 in cells, f"{filename}: missing signed infinities")

        # Independent big-endian four-byte roundtrip for every raw float cell.
        packed = pack_u32_cells(cells)
        roundtrip = list(struct.unpack(">" + "I" * len(cells), packed))
        require(roundtrip == cells, f"{filename}: u32 packed roundtrip changed raw bits")
        require(len(packed) == 4 * len(cells), f"{filename}: packed byte count mismatch")

        size = sizes(len(cells), nonzero)
        legacy = old_format_choice(len(cells), nonzero)
        selected = canonical_choice(len(cells), cells)
        digest = hashlib.sha256(raw).hexdigest()
        raw_hashes[filename] = digest
        cells_by_file[filename] = cells
        fixture_reports.append({
            "file": filename,
            "length": len(cells),
            "nonzeroRawBits": nonzero,
            "sha256": digest,
            "sizesBytes": size,
            "oldCanonicalChoice": legacy,
            "proposedReferenceChoice": selected,
            "independentU32Roundtrip": "bit-exact",
        })

    references = json.loads((fixtures_dir / "reference-control.json").read_text(encoding="utf-8"))
    require(references == EXPECTED_REFERENCES, "reference-array control contents changed")
    require(manifest["referenceControl"] == {"file": "reference-control.json", "length": 5},
            "reference-array control metadata changed")

    long_path = fixtures_dir / "long-control.u64be"
    long_raw = long_path.read_bytes()
    require(len(long_raw) == 8 * len(EXPECTED_LONGS), "long control byte length mismatch")
    longs = [value[0] for value in struct.iter_unpack(">Q", long_raw)]
    require(longs == EXPECTED_LONGS, "long control raw contents changed")
    require(manifest["longControl"] == {"file": "long-control.u64be", "length": 8, "encoding": "big-endian u64"},
            "long control metadata changed")

    thresholds = [crossover(1024), crossover(65536)]
    require([item["strictFirstPackedNonzeroCount"] for item in thresholds] == [342, 21846],
            "strict size crossover changed")

    refusals = []
    dense_cells = cells_by_file["float-1024-dense.u32be"]
    dense_payload = pack_u32_cells(dense_cells)
    decoded = decode_packed(dense_payload, len(dense_cells), "float", PACKED_FLOAT_FLAG)
    require(decoded == dense_cells, "canonical 1024 packed decode changed raw cells")
    dense_long_cells = cells_by_file["float-65536-dense.u32be"]
    dense_long_payload = pack_u32_cells(dense_long_cells)
    decoded_long = decode_packed(dense_long_payload, len(dense_long_cells), "float", PACKED_FLOAT_FLAG)
    require(decoded_long == dense_long_cells, "canonical 65536 packed decode changed raw cells")

    refusals.append(expect_refusal("truncated packed payload", lambda: decode_packed(dense_payload[:-1], 1024, "float", PACKED_FLOAT_FLAG)))
    refusals.append(expect_refusal("extra packed payload byte", lambda: decode_packed(dense_payload + b"\x00", 1024, "float", PACKED_FLOAT_FLAG)))
    refusals.append(expect_refusal("wrong primitive kind", lambda: decode_packed(dense_payload, 1024, "reference", PACKED_FLOAT_FLAG)))
    refusals.append(expect_refusal("packed+sparse flag collision", lambda: decode_packed(dense_payload, 1024, "float", PACKED_FLOAT_FLAG | SPARSE_PAIR_FLAG)))
    refusals.append(expect_refusal("unknown packed flag", lambda: decode_packed(dense_payload, 1024, "float", PACKED_FLOAT_FLAG | (1 << 29))))
    small_payload = pack_u32_cells(cells_by_file["float-16-small.u32be"])
    refusals.append(expect_refusal("length below packed minimum", lambda: decode_packed(small_payload, 16, "float", PACKED_FLOAT_FLAG)))
    sparse_cells = cells_by_file["float-1024-sparse.u32be"]
    sparse_payload = pack_u32_cells(sparse_cells)
    refusals.append(expect_refusal("packed is not strict size winner", lambda: decode_packed(sparse_payload, 1024, "float", PACKED_FLOAT_FLAG)))
    refusals.append(expect_refusal("u64 float source has high bits", lambda: pack_u32_cells([0x100000000])))

    old_sparse = encode_old_sparse(sparse_cells)
    decoded_sparse = decode_old_sparse(old_sparse, 1024, expected=sparse_cells, require_canonical=True)
    require(decoded_sparse == sparse_cells, "old sparse reference roundtrip failed")
    bad_count = bytearray(old_sparse)
    struct.pack_into(">I", bad_count, 0, len(sparse_cells) - 1)
    refusals.append(expect_refusal("old sparse count/payload mismatch", lambda: decode_old_sparse(bytes(bad_count), 1024)))
    wrong_cells = list(sparse_cells)
    first_nonzero = next(i for i, cell in enumerate(wrong_cells) if cell)
    wrong_cells[first_nonzero] ^= 1
    refusals.append(expect_refusal("old sparse content mismatch", lambda: decode_old_sparse(old_sparse, 1024, expected=wrong_cells)))
    dense_old_sparse = encode_old_sparse(dense_long_cells)
    refusals.append(expect_refusal("old sparse is noncanonical after packed wins", lambda: decode_old_sparse(dense_old_sparse, 65536, require_canonical=True)))

    return {
        "classification": "TEST-ONLY NOT EVM ACCEPTANCE",
        "generatorClassMajorVersion": verify_class_major(pathlib.Path(class_file)),
        "sizingModel": {
            "oldSparse": "4-byte u32 count + 12 bytes per (u32 index,u64 value)",
            "packedFloat": "4 bytes per float cell",
            "dense": "8 bytes per cell",
            "strictPackedRule": "length >= 1024 and packedFloatBytes < oldSparseBytes",
            "oldChoiceRule": "sparse iff oldSparseBytes < denseBytes, else dense",
        },
        "strictCrossover": thresholds,
        "generatedFloatFixtures": fixture_reports,
        "hostOracleControls": {
            "referenceArray": references,
            "longArrayU64Hex": [f"{value:016x}" for value in longs],
            "referenceControlSha256": hashlib.sha256((fixtures_dir / "reference-control.json").read_bytes()).hexdigest(),
            "longControlSha256": hashlib.sha256(long_raw).hexdigest(),
            "oracleManifestSha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        },
        "rawU32RoundtripCases": len(fixture_reports),
        "canonicalPackedDecodeCases": 2,
        "roundtripCases": len(fixture_reports) + 3,
        "refusalControls": refusals,
        "oldSparsePositiveControl": {
            "bytes": len(old_sparse),
            "rawCellsRoundtrip": "bit-exact",
            "canonical": True,
        },
        "limits": "No original Minecraft inputs, source/bytecode injection, EVM execution, or checkpoint acceptance claim.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", required=True, help="generated fixture directory")
    parser.add_argument("--class-file", required=True, help="compiled Java generator class, used to assert Java 8 classfile version")
    parser.add_argument("--report", required=True, help="write deterministic JSON report")
    args = parser.parse_args()
    report = run(args.fixtures, args.class_file)
    pathlib.Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "classification": report["classification"],
        "thresholds": [(item["length"], item["strictFirstPackedNonzeroCount"]) for item in report["strictCrossover"]],
        "fixtures": len(report["generatedFloatFixtures"]),
        "roundtripCases": report["roundtripCases"],
        "refusals": len(report["refusalControls"]),
        "report": args.report,
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, Refusal, OSError, ValueError, KeyError) as exc:
        print(f"float-pack controls FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
