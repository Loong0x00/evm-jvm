#!/usr/bin/env python3
"""Deterministically build Java-8-only capacity fixture ZIPs.

The ZIPs are opaque fixture inputs.  The separately compiled Oracle classes are
host-test-only and are deliberately excluded from every ZIP.
"""
from __future__ import print_function
import argparse
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
JDK = pathlib.Path("/usr/lib/jvm/java-8-openjdk/bin")
JAVAC, JAVA, JAVAP = (JDK / x for x in ("javac", "java", "javap"))
JAVAC_VERSION = "javac 1.8.0_504"
JAVA_VERSION_PREFIX = 'openjdk version "1.8.0_504"'
MODES = (0, 7, 19)
BIG_HASHES = {
    "BigCaller.class": "ec8a920a8d7871291e5aa14a79d6a93de3b773167ac62f980bfc728dac17f485",
    "BigEntry.class": "4ea3f9d001762cf5538a35003a8c88a12965fb9e5f954185c27bfe9c37886de1",
}
BIG_ZIP_HASH = "c5614296ec8c953cc96ff52de12a4c4e745c82e481fe30f58fbf540a6399ae43"
# Copies from evidence/java-evm/capacity-baseline/preflight/fixtures at 5ed777fd5.
# Do not silently turn these into a newly invented performance fixture.
EXACT_SOURCE_HASHES = {
    "Base0.java": "a54611eb3380b6c2900e2152f3248cfc382f70f7c0facce36a645e26e7fc4c48",
    "Base1.java": "5d03879ee69b6cc89954175c8c41fd822ca1d3dfb8dbf0a170306564abe0c245",
    "Base2.java": "0123063b336a70e06517c97df0024bd0b12f06b21a2702821eda7f0986e0d218",
    "Base3.java": "29c2ef74bb9f485af720bc97e4e7ac55dc410a5b048ec2cf370626de048eac10",
    "Cap0.java": "619255cff5052417a9d04d5605fc9e897354f4764e04f7e0647d20d12a0fa5e6",
    "Cap1.java": "11880d7640a050f7f8390d7462de974713bc43967052f51377edba7d6ead3c65",
    "Cap2.java": "55cfbee6fdbc94e9fa5a1d3dd5c00f7a67c10f0501008054a5446a0ac39564c1",
    "Cap3.java": "421fc9ce9c12eeeca3a3854ce55cd6cb59cd10656bb1239a99242ae103462010",
    "Cap4.java": "bb7a45cda44971bf5e131560ce945cee900bfb0ea6677d405192316b670bc6c0",
    "Cap5.java": "bf5d2290367ecfd334b1045bd79eeb0125c8da21f4b25bac20841dbf98a50099",
    "Cap6.java": "e6621a5135aa54e2f6ee25f3ac90dc35f9d9c1a77903b0594d885bff0a97807a",
    "Cap7.java": "7fcf65d237505e470fe28c27a1ed530d2753f71fef693ed167a36790325f3430",
    "BigCaller.java": "edae11e1c30b05b85c64fd308a65cdf99691f5937ae8f650d0eb90b8e52cbf06",
    "BigEntry.java": "cec4e607ff33bd0c13aa624db86a2bb327f0ad38fb10955ff9e46b3a97768048",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command_output(argv, stderr=subprocess.STDOUT):
    return subprocess.check_output([str(x) for x in argv], stderr=stderr, text=True)


def require_exact_sources():
    actual = {p.name: sha(p.read_bytes()) for p in sorted((ROOT / "sources" / "exact").glob("*.java"))}
    if actual != EXACT_SOURCE_HASHES:
        raise SystemExit("committed exact fixture source digest mismatch")


def require_jdk():
    for tool in (JAVAC, JAVA, JAVAP):
        if not tool.is_file():
            raise SystemExit("missing pinned Java 8 tool: " + str(tool))
    javac_version = command_output([JAVAC, "-version"]).strip()
    java_version = command_output([JAVA, "-version"]).splitlines()[0]
    if javac_version != JAVAC_VERSION or java_version != JAVA_VERSION_PREFIX:
        raise SystemExit("requires exact 8u504: javac=%r java=%r" % (javac_version, java_version))
    return {"javac": javac_version, "java": java_version,
            "javap": command_output([JAVAP, "-version"]).strip()}


def u2(data, offset):
    return struct.unpack_from(">H", data, offset)[0]


def u4(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def cp_end_and_utf8(data):
    """Return (end offset, utf8 by CP index); reject malformed class bytes."""
    if data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("not a class file")
    count = u2(data, 8)
    pos, index, utf8 = 10, 1, {}
    while index < count:
        tag = data[pos]
        if tag == 1:
            length = u2(data, pos + 1)
            raw = data[pos + 3:pos + 3 + length]
            if len(raw) != length:
                raise ValueError("truncated UTF8")
            utf8[index] = raw.decode("utf-8")
            pos += 3 + length
        elif tag in (3, 4): pos += 5
        elif tag in (5, 6): pos += 9; index += 1
        elif tag in (7, 8, 16, 19, 20): pos += 3
        elif tag in (9, 10, 11, 12, 18): pos += 5
        elif tag == 15: pos += 4
        else: raise ValueError("bad constant-pool tag %d" % tag)
        if pos > len(data): raise ValueError("truncated constant pool")
        index += 1
    return pos, utf8


def class_layout(data):
    """Strict enough parser to locate members and class attributes."""
    pos, utf8 = cp_end_and_utf8(data)
    pos += 6  # access, this, super
    interfaces = u2(data, pos); pos += 2 + 2 * interfaces
    def skip_members(pos):
        count = u2(data, pos); pos += 2
        for _ in range(count):
            pos += 6
            attrs = u2(data, pos); pos += 2
            for _ in range(attrs):
                pos += 2
                length = u4(data, pos); pos += 4 + length
                if pos > len(data): raise ValueError("truncated member attribute")
        return pos, count
    pos, fields = skip_members(pos)
    pos, methods = skip_members(pos)
    attribute_count_offset = pos
    attrs = u2(data, pos); pos += 2
    parsed = []
    for _ in range(attrs):
        name_index = u2(data, pos); length = u4(data, pos + 2); pos += 6
        value = data[pos:pos + length]
        if len(value) != length: raise ValueError("truncated class attribute")
        parsed.append((utf8.get(name_index, "<bad-index>"), value))
        pos += length
    if pos != len(data): raise ValueError("trailing or malformed class bytes")
    return {"cpEnd": cp_end_and_utf8(data)[0], "utf8": utf8, "fields": fields,
            "methods": methods, "attributeCountOffset": attribute_count_offset,
            "attributes": parsed}


def add_padding_attribute(data, target):
    """Append an explicitly unknown, JVM-ignored class attribute to exact size."""
    cp_end, _ = cp_end_and_utf8(data)
    old_count = u2(data, 8)
    name = b"CapacityPadding"
    cp_item = b"\x01" + struct.pack(">H", len(name)) + name
    rebuilt = data[:8] + struct.pack(">H", old_count + 1) + data[10:cp_end] + cp_item + data[cp_end:]
    layout = class_layout(rebuilt)
    minimum = len(rebuilt) + 6
    if target < minimum:
        raise ValueError("target %d smaller than valid padded class minimum %d" % (target, minimum))
    at = layout["attributeCountOffset"]
    old_attrs = u2(rebuilt, at)
    rebuilt = (rebuilt[:at] + struct.pack(">H", old_attrs + 1) + rebuilt[at + 2:] +
               struct.pack(">HI", old_count, target - minimum) + b"\x00" * (target - minimum))
    if len(rebuilt) != target: raise AssertionError("padding arithmetic")
    result = class_layout(rebuilt)
    found = [value for key, value in result["attributes"] if key == "CapacityPadding"]
    if found != [b"\x00" * (target - minimum)]:
        raise AssertionError("unknown padding attribute did not parse exactly")
    return rebuilt


def compile_sources(destination, sources, classpath=None):
    destination.mkdir(parents=True, exist_ok=True)
    cmd = [JAVAC, "-source", "8", "-target", "8", "-g:none", "-d", destination]
    if classpath: cmd += ["-cp", classpath]
    cmd += list(sources)
    subprocess.run([str(x) for x in cmd], check=True)


def write_zip(path, class_dir, names):
    with zipfile.ZipFile(str(path), "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in names:
            value = (class_dir / name).read_bytes()
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, value, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def chain_sources(name, count):
    result = {}
    for i in range(count):
        cls = "%s%d" % (name, i)
        next_call = ("return %s%d.run(x + s) + %d;" % (name, i + 1, i)
                     if i + 1 < count else "return x + s;")
        result[cls + ".java"] = ("public class %s { static int s = %d; static { s += %d; } "
                                  "public static int run(int x) { %s } }\n" %
                                  (cls, 10 + i, 100 + i, next_call))
    return result


def oracle_source(case):
    return ("public class Oracle { public static void main(String[] a) { int mode = Integer.parseInt(a[0]); "
            "System.out.println(\"case=%s mode=\" + mode + \" result=\" + %s.run(mode)); } }\n" %
            (case["name"], case["entryClass"]))


def run_oracle(out, case):
    oracle_source_dir = out / "oracle-src" / case["name"]
    oracle_class_dir = out / "oracle-classes" / case["name"]
    oracle_source_dir.mkdir(parents=True)
    source = oracle_source_dir / "Oracle.java"
    source.write_text(oracle_source(case), encoding="utf-8")
    class_dir = out / "classes" / case["name"]
    compile_sources(oracle_class_dir, [source], str(class_dir))
    raw = ""
    expected = []
    for mode in MODES:
        value = command_output([JAVA, "-cp", str(class_dir) + ":" + str(oracle_class_dir), "Oracle", str(mode)])
        raw += value
        prefix = "case=%s mode=%d result=" % (case["name"], mode)
        if not value.startswith(prefix) or not value.endswith("\n"):
            raise ValueError("bad oracle output %r" % value)
        expected.append({"argument": mode, "result": int(value[len(prefix):-1])})
    (out / "oracle" / (case["name"] + ".raw")).parent.mkdir(exist_ok=True)
    (out / "oracle" / (case["name"] + ".raw")).write_text(raw, encoding="utf-8")
    return expected


def record_case(out, case):
    class_dir = out / "classes" / case["name"]
    names = [x + ".class" for x in case["knownNames"]]
    zip_path = out / "zips" / (case["name"] + ".zip")
    zip_path.parent.mkdir(exist_ok=True)
    write_zip(zip_path, class_dir, names)
    entries = []
    for name in names:
        value = (class_dir / name).read_bytes()
        layout = class_layout(value)
        entries.append({"name": name, "bytes": len(value), "sha256": sha(value),
                        "constantPoolCount": u2(value, 8), "methodCount": layout["methods"]})
    case.update({"zip": {"name": zip_path.name, "bytes": zip_path.stat().st_size,
                          "sha256": sha(zip_path.read_bytes())},
                 "classes": entries, "selectedRawBytes": sum(x["bytes"] for x in entries),
                 "oracle": run_oracle(out, case)})
    return case


def write_chain(out, count):
    name = "chain%d" % count
    srcdir = out / "generated-sources" / name
    srcdir.mkdir(parents=True)
    sources = chain_sources("Chain%d_" % count, count)
    for filename, text in sorted(sources.items()): (srcdir / filename).write_text(text, encoding="utf-8")
    class_dir = out / "classes" / name
    compile_sources(class_dir, [srcdir / x for x in sorted(sources)])
    return {"name": name, "kind": "generated-transitive-static-init-call-chain",
            "entryClass": "Chain%d_0" % count, "entryMethod": "run(int)",
            "knownNames": ["Chain%d_%d" % (count, i) for i in range(count)],
            "allSelectedClassesParticipate": True,
            "participation": "run invokes every successor; each selected class initializes its static s"}


def write_exact(out, name, source_names, entry):
    class_dir = out / "classes" / name
    sources = [ROOT / "sources" / "exact" / x for x in source_names]
    compile_sources(class_dir, sources)
    return {"name": name, "kind": "committed-exact-source",
            "entryClass": entry, "entryMethod": "run(int)",
            "knownNames": [x[:-5] for x in source_names], "allSelectedClassesParticipate": True}


def write_boundary(out, total):
    name = "aggregate%d" % total
    class_dir = out / "classes" / name
    source_dir = ROOT / "sources" / "boundary"
    compile_sources(class_dir, [source_dir / "BoundaryEntry.java", source_dir / "BoundaryPad.java"])
    entry = (class_dir / "BoundaryEntry.class").read_bytes()
    pad = (class_dir / "BoundaryPad.class").read_bytes()
    # The useful entry deliberately crosses the 4096-byte DI0 page edge.  The
    # remainder is an independently legal class resource, never a malformed blob.
    entry = add_padding_attribute(entry, 4097)
    pad = add_padding_attribute(pad, total - len(entry))
    if len(pad) > 262144: raise AssertionError("individual DI0 legality violated")
    (class_dir / "BoundaryEntry.class").write_bytes(entry)
    (class_dir / "BoundaryPad.class").write_bytes(pad)
    return {"name": name, "kind": "valid-unknown-class-attribute-padding-control",
            "entryClass": "BoundaryEntry", "entryMethod": "run(int)",
            "knownNames": ["BoundaryEntry", "BoundaryPad"], "allSelectedClassesParticipate": True,
            "padding": {"attribute": "CapacityPadding", "entryBytes": len(entry), "padBytes": len(pad),
                        "aggregateBytes": total, "individualResourceMaximum": 262144,
                        "purpose": "boundary control, not method-rich performance"}}


def verify(out):
    require_exact_sources()
    metadata_path = out / "metadata.json"
    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    if meta["toolVersions"] != require_jdk(): raise AssertionError("tool version receipt mismatch")
    for case in meta["fixtures"]:
        class_dir = out / "classes" / case["name"]
        zipped = out / "zips" / case["zip"]["name"]
        if sha(zipped.read_bytes()) != case["zip"]["sha256"] or zipped.stat().st_size != case["zip"]["bytes"]:
            raise AssertionError("zip digest/size mismatch " + case["name"])
        with zipfile.ZipFile(str(zipped)) as z:
            if z.namelist() != [x["name"] for x in case["classes"]]: raise AssertionError("zip names mismatch")
            if any(name == "Oracle.class" for name in z.namelist()): raise AssertionError("oracle leaked into zip")
            for item in case["classes"]:
                value = z.read(item["name"])
                if value != (class_dir / item["name"]).read_bytes(): raise AssertionError("zip class mismatch")
                layout = class_layout(value)
                if len(value) != item["bytes"] or sha(value) != item["sha256"]:
                    raise AssertionError("class digest/size mismatch")
                if u2(value, 8) != item["constantPoolCount"] or layout["methods"] != item["methodCount"]:
                    raise AssertionError("class layout mismatch")
        if sum(x["bytes"] for x in case["classes"]) != case["selectedRawBytes"]:
            raise AssertionError("aggregate mismatch")
        if "padding" in case:
            if case["selectedRawBytes"] != case["padding"]["aggregateBytes"]: raise AssertionError("padding aggregate")
            if any(x["bytes"] > 262144 for x in case["classes"]): raise AssertionError("oversize resource")
            if case["padding"]["entryBytes"] != 4097: raise AssertionError("missing cross-page resource")
        raw = (out / "oracle" / (case["name"] + ".raw")).read_text(encoding="utf-8")
        rerun = ""
        for observation in case["oracle"]:
            mode = observation["argument"]
            actual = command_output([JAVA, "-cp", str(class_dir) + ":" + str(out / "oracle-classes" / case["name"]), "Oracle", str(mode)])
            rerun += actual
            if actual != "case=%s mode=%d result=%d\n" % (case["name"], mode, observation["result"]):
                raise AssertionError("oracle mismatch " + case["name"])
        if raw != rerun: raise AssertionError("raw oracle capture mismatch")
    big = next(x for x in meta["fixtures"] if x["name"] == "big-method-rich")
    actual = {x["name"]: x["sha256"] for x in big["classes"]}
    if actual != BIG_HASHES or big["zip"]["sha256"] != BIG_ZIP_HASH:
        raise AssertionError("recorded BigEntry/BigCaller digest mismatch")
    entry = next(x for x in big["classes"] if x["name"] == "BigEntry.class")
    if entry["bytes"] != 90874 or entry["constantPoolCount"] != 2565 or entry["methodCount"] != 2552:
        raise AssertionError("recorded method-rich shape mismatch")
    print("verified %d fixtures" % len(meta["fixtures"]))


def generate(out):
    if out.exists(): raise SystemExit("refusing existing output: " + str(out))
    require_exact_sources()
    versions = require_jdk()
    out.mkdir(parents=True)
    fixtures = []
    fixtures.append(record_case(out, write_exact(out, "baseline4-exact", ["Base0.java", "Base1.java", "Base2.java", "Base3.java"], "Base0")))
    fixtures.append(record_case(out, write_exact(out, "capacity8-exact", ["Cap0.java", "Cap1.java", "Cap2.java", "Cap3.java", "Cap4.java", "Cap5.java", "Cap6.java", "Cap7.java"], "Cap0")))
    fixtures.append(record_case(out, write_exact(out, "big-method-rich", ["BigCaller.java", "BigEntry.java"], "BigCaller")))
    for count in (4, 5, 6, 8, 9): fixtures.append(record_case(out, write_chain(out, count)))
    for total in (65536, 65537, 262144, 262145): fixtures.append(record_case(out, write_boundary(out, total)))
    source_hashes = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted((ROOT / "sources").rglob("*.java"))}
    metadata = {"schema": 1, "purpose": "TEST-only generated Java8 capacity fixture/oracle builder; ZIPs are opaque execution inputs",
                "toolVersions": versions, "modes": list(MODES), "sourceSHA256": source_hashes,
                "fixtures": fixtures,
                "limits": {"production": {"classes": 4, "aggregateRawBytes": 65536},
                           "prototypeUnderTestOnly": {"classes": 8, "aggregateRawBytes": 262144},
                           "individualResourceMaximum": 262144}}
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verify(out)
    print(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=pathlib.Path, help="fresh ignored output directory")
    parser.add_argument("--verify", action="store_true", help="strictly verify an existing generated output")
    args = parser.parse_args()
    if args.verify: verify(args.output.resolve())
    else: generate(args.output.resolve())

if __name__ == "__main__": main()
