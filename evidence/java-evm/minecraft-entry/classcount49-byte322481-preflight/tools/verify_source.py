#!/usr/bin/env python3
"""Pin raw49/322481 to accepted equalsIgnoreCase sources only."""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
accepted = stage.parent / "parent-e73e45fce"
generated_parent = stage.parent / "string-equals-ignore-case-preflight"
D = "MC-RAW49-BYTE322481-P1"
OLD_D = "MC-STRING-EQUALS-IGNORE-CASE-P2"
ENGINE = "4d432d52415734392d4259544533323234383145"
OWNER = "4d432d52415734392d425954453332323438314f"
OLD_ENGINE = "4d432d5354522d45512d49434153452d50324500"
OLD_OWNER = "4d432d5354522d45512d49434153452d50324f00"
ENGINE_PIN = {"bytes": 391507, "initSHA256": "2b43ff9489869fcd7dc3d6cffa10e051f64c73361a79d5dc61dedf15296f5e26", "runtimeSHA256": "4bd4abf1432957891613758d21ef0122c701027e0f554ce4616cb1836baa8907", "runtimeKeccak256": "adf3f488d988d0b60b5555c8a8ac797f9f033cc07a7f57cd2e2853d8472b3789"}
COORDINATOR_PIN = {"bytes": 5394, "initSHA256": "c39885e525f0fe893e8f4ce150340d6b8dc94f79cf4902b451265521046dff13", "runtimeSHA256": "43df53af01c9b591a3dd9ed83d21f1476266964d54d29ad7101d86acbd99e9e3", "runtimeKeccak256": "50e3f2e1e6420d5648afbb101f68b53756986c5acfc89a2cbbdc28a52ca151ad"}
LIMITS = "93947741f6b7325cbba5392c215a8470ce288ae21f402d011a33ff74cc45a700"


def replace_exact(text, old, new, count=1):
    assert text.count(old) == count, (old[:96], text.count(old), count)
    return text.replace(old, new)


def stage_text(relative):
    return (stage / relative).read_text()


def accepted_text(relative):
    return (accepted / relative).read_text()


def generated_text(relative):
    return (generated_parent / relative).read_text()


# The accepted P2 parent is the sole semantic source.  Both engine layouts are
# mechanically P2 with only a fresh domain, raw capacity and committed tuple.
def engine_expected(text):
    text = replace_exact(text, OLD_D, D, 9)
    text = replace_exact(text, "MAX_RAW_CLASSES = 48;", "MAX_RAW_CLASSES = 49;")
    text = replace_exact(text, "MAX_RAW_BYTES = 314425;", "MAX_RAW_BYTES = 322481;")
    return replace_exact(text, "uint32(48), uint32(314425)", "uint32(49), uint32(322481)")

assert stage_text("engine/MCEntryInterpreter.sol") == engine_expected(
    accepted_text("artifacts/engine/MCEntryInterpreter.sol")
)
# The accepted archive records the canonical layout.  The checked-in generated
# P1 pre-layout has the identical pre-layout source except its old domain.
pre = generated_text("engine/pre-layout-MCEntryInterpreter.sol")
pre = replace_exact(pre, "MC-STRING-EQUALS-IGNORE-CASE-P1", D, 9)
pre = replace_exact(pre, "MAX_RAW_CLASSES = 48;", "MAX_RAW_CLASSES = 49;")
pre = replace_exact(pre, "MAX_RAW_BYTES = 314425;", "MAX_RAW_BYTES = 322481;")
pre = replace_exact(pre, "uint32(48), uint32(314425)", "uint32(49), uint32(322481)")
assert stage_text("engine/pre-layout-MCEntryInterpreter.sol") == pre

# Coordinator changes exactly its EVM binding, package domains, fixed arrays,
# count/byte guards and engine code identity; no constructor behavior changes.
coord = accepted_text("artifacts/coordinator/MCEntryCoordinator.sol")
coord = replace_exact(coord, OLD_D, D, 4)
coord = replace_exact(coord, 'hex"' + OLD_ENGINE + '"', 'hex"' + ENGINE + '"')
coord = replace_exact(coord, "5237c5ae685bd8d1c7c704f925bc5987700290bd1d334958f02328573c5d5c6a", ENGINE_PIN["runtimeKeccak256"])
coord = replace_exact(coord, "[48]", "[49]", 4)
coord = replace_exact(coord, "n > 48", "n > 49")
coord = replace_exact(coord, "314425", "322481", 2)
assert stage_text("coordinator/MCEntryCoordinator.sol") == coord

# The EVM transport stays identical apart from the fresh binding/hash and its
# two product count guards.  Its pin lengths remain 391507 and 5394.
transport = accepted_text("canonical-driver.go.txt")
for old, new, count in (
    (OLD_D, D, 6), (OLD_OWNER, OWNER, 1), (OLD_ENGINE, ENGINE, 1),
    ("f6cb5672bca69c305c3eb4e19b1645e8c3de4b4c04a4f5d523f2d82cfe930983", ENGINE_PIN["runtimeSHA256"], 1),
    ("0x5237c5ae685bd8d1c7c704f925bc5987700290bd1d334958f02328573c5d5c6a", "0x" + ENGINE_PIN["runtimeKeccak256"], 1),
    ("0x043ae8b035e935dbde39d5130f87eacc2ad6cff07f24683bfb2810017088bb20", "0x" + COORDINATOR_PIN["runtimeKeccak256"], 1),
    ("len(m.Decoders) > 48", "len(m.Decoders) > 49", 1),
    ("len(parts) > 48", "len(parts) > 49", 1),
):
    transport = replace_exact(transport, old, new, count)
assert stage_text("tools/Go.txt") == transport

# Fixture construction is retained byte-for-byte except the capacity labels,
# exact count49/50 witness and exact aggregate-byte witness.
fixtures = generated_text("tools/generate_fixtures.py")
fixtures = replace_exact(fixtures, "java-diff-mc-string-equals-ignore-case-fixtures-", "java-diff-mc-classcount49-byte322481-fixtures-")
fixtures = replace_exact(fixtures, "# Exact raw48 and aggregate-byte boundaries exercise this measured cap lift.", "# Exact raw49 and aggregate-byte boundaries exercise this measured cap lift.")
fixtures = replace_exact(fixtures,
    "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49)",
    "(29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50)")
fixtures = replace_exact(fixtures, 'count_fixture("count-48-314425", 48, 314425)', 'count_fixture("count-49-322481", 49, 322481)')
fixtures = replace_exact(fixtures, 'count_fixture("count-48-314426", 48, 314426)', 'count_fixture("count-49-322482", 49, 322482)')
old_distribution = '''    def compile(main_pads=(), tail_pads=()):
        (src / "CountMain.java").write_text(count_source(count, main_pads))
        # The aggregate byte witness must remain below DI0's independent
        # per-class bound. Tail01 is otherwise an unchanged ordinary tail.
        (src / "Tail01.java").write_text(tail_source(1, tail_pads))
        shutil.rmtree(classes); classes.mkdir()
        subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes,
                        *map(str, sorted(src.glob("*.java")))], check=True)
        return sum(path.stat().st_size for path in classes.glob("*.class"))
    total = compile()
    main_pads = []; tail_pads = []
    if target is not None:
        assert total < target
        overhead = compile([""] * 5, [""])
        need = target - total - (overhead - total)
        assert 0 <= need <= 6 * 65000
        allocations = [need // 6 + (1 if i < need % 6 else 0) for i in range(6)]
        values = [(chr(65 + i) + "x" * (amount - 1)) if amount else "" for i, amount in enumerate(allocations)]
        main_pads, tail_pads = values[:5], values[5:]
        total = compile(main_pads, tail_pads)
        for _ in range(3):
            delta = target - total
            if delta == 0: break
            at = max(range(6), key=lambda i: len(main_pads[i]) if i < 5 else len(tail_pads[i - 5]))
            pads = main_pads if at < 5 else tail_pads; index = at if at < 5 else at - 5
            assert 0 <= len(pads[index]) + delta <= 65000
            pads[index] = pads[index][:len(pads[index]) + delta] if delta < 0 else pads[index] + "x" * delta
            total = compile(main_pads, tail_pads)
        assert total == target, (label, total, target)
        assert max(path.stat().st_size for path in classes.glob("*.class")) <= 262144
'''
new_distribution = '''    def compile(pads=()):
        # The aggregate-byte witness is distributed across CountMain and seven
        # ordinary tails, so every individual generated DI0 input stays below
        # its fixed 262144-byte per-class transport bound.
        (src / "CountMain.java").write_text(count_source(count, pads[:1]))
        for index in range(1, 8):
            (src / ("Tail%02d.java" % index)).write_text(tail_source(index, pads[index:index + 1]))
        shutil.rmtree(classes); classes.mkdir()
        subprocess.run([javac, "-source", "8", "-target", "8", "-g:none", "-d", classes,
                        *map(str, sorted(src.glob("*.java")))], check=True)
        return sum(path.stat().st_size for path in classes.glob("*.class"))
    total = compile()
    if target is not None:
        assert total < target
        overhead = compile([""] * 8)
        need = target - total - (overhead - total)
        assert 0 <= need <= 8 * 65000
        pads = [(chr(65 + index) + "x" * (amount - 1)) if amount else ""
                for index, amount in enumerate(need // 8 + (1 if index < need % 8 else 0) for index in range(8))]
        total = compile(pads)
        for _ in range(3):
            delta = target - total
            if delta == 0: break
            index = max(range(8), key=lambda item: len(pads[item]))
            assert 0 <= len(pads[index]) + delta <= 65000
            pads[index] = pads[index][:len(pads[index]) + delta] if delta < 0 else pads[index] + "x" * delta
            total = compile(pads)
        assert total == target, (label, total, target)
        assert max(path.stat().st_size for path in classes.glob("*.class")) <= 262144
'''
fixtures = replace_exact(fixtures, old_distribution, new_distribution)
assert stage_text("tools/generate_fixtures.py") == fixtures

for relative in ("tools/checkpoint_diagnostic.py", "tools/checkpoint_frames.py"):
    assert stage_text(relative) == replace_exact(generated_text(relative), "classes<=141", "classes<=142"), relative

# The whole generated gate preserves every equalIgnoreCase fixture and retained
# control.  Only its source/build labels, pins, capacity witnesses, and honest
# exact-boundary labels move one step.
def gate_expected(text):
    text = replace_exact(text, "java-diff-mc-string-equals-ignore-case-build-", "java-diff-mc-classcount49-byte322481-build-")
    text = replace_exact(text, "java-diff-mc-string-equals-ignore-case-fixtures-", "java-diff-mc-classcount49-byte322481-fixtures-")
    text = replace_exact(text, "java-diff-mc-string-equals-ignore-case-gate-", "java-diff-mc-classcount49-byte322481-gate-")
    text = replace_exact(text, "[48, 314425]", "[49, 322481]")
    text = replace_exact(text, 'diagnosticClassBound"] == 141', 'diagnosticClassBound"] == 142')
    text = replace_exact(text, 'head["totalClassBytes"] <= 314425', 'head["totalClassBytes"] <= 322481')
    start = text.index("# Exact raw48 is the focused capacity witness:")
    end = text.index("# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.", start)
    b = text[start:end]
    def r(old, new, count=1):
        nonlocal b
        b = replace_exact(b, old, new, count)
    r("raw48", "__RAW48__", 2); r("raw49", "raw50", 13); r("__RAW48__", "raw49", 2)
    r("count-48-314425", "__BYTE_FIT__", 3); r("count-48-314426", "__BYTE_OVER__", 3)
    r("count-48", "__COUNT48__", 1); r("count-49", "count-50", 6); r("__COUNT48__", "count-49", 1)
    r("__BYTE_FIT__", "count-49-322481", 3); r("__BYTE_OVER__", "count-49-322482", 3)
    r('''assert source.count("len(m.Decoders) > 48") == 1 and source.count("len(parts) > 48") == 1
    source = (source.replace("len(m.Decoders) > 48", "len(m.Decoders) > 49")
                    .replace("len(parts) > 48", "len(parts) > 49"))''', '''assert source.count("len(m.Decoders) > 49") == 1 and source.count("len(parts) > 49") == 1
    source = (source.replace("len(m.Decoders) > 49", "len(m.Decoders) > 50")
                    .replace("len(parts) > 49", "len(parts) > 50"))''')
    r('''assert text.count("[48]") == 4 and text.count("n > 48") == 1
probe_source.write_text(text.replace("[48]", "[49]").replace("n > 48", "n > 49"))''', '''assert text.count("[49]") == 4 and text.count("n > 49") == 1
probe_source.write_text(text.replace("[49]", "[50]").replace("n > 49", "n > 50"))''')
    r('["1", "49"]', '["1", "50"]')
    r('bindingCount"] == 48', 'bindingCount"] == 49')
    r("314425", "__BYTES_OLD__", 5); r("314426", "322482", 5); r("__BYTES_OLD__", "322481", 5)
    b = replace_exact(b, "Raw49 is independently refused", "Raw50 is independently refused")
    text = text[:start] + b + text[end:]
    text = replace_exact(text, "MC-STRING-EQUALS-IGNORE-CASE-P1", D)
    old = "Only existing bootstrap String image26 changes: equalsIgnoreCase(String) compares UTF-16 units exactly, folds ASCII A-Z/a-z only, returns false for null, and has no general Unicode case-folding claim. Objects image93, bootstrap count93, diagnostic141, raw48/314425, native13, all limits and the runtime-derived ordered root remain pinned except for String's changed leaf. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns genuine replay."
    new = "Only selected raw-class capacity changes from accepted equalsIgnoreCase evidence: raw48/314425/diagnostic141 to raw49/322481/diagnostic142. All 93 ordered bootstrap images and bytes, including String.equalsIgnoreCase at root-leaf26 and Objects image93, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and the runtime-derived ordered root remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, provider construction, factory execution, world, or Done input or claim. Parent alone owns genuine ReflectionUtil append and class/factory execution or accelerated replay."
    return replace_exact(text, old, new)

assert stage_text("tools/gate.py") == gate_expected(generated_text("tools/gate.py"))

build = generated_text("tools/build.py")
build = replace_exact(build, '"""Rebuild the pinned generated String.equalsIgnoreCase(String) evidence."""', '"""Rebuild the pinned generated raw49/byte322481 evidence."""')
build = replace_exact(build, "java-diff-mc-string-equals-ignore-case-build-", "java-diff-mc-classcount49-byte322481-build-")
assert stage_text("tools/build.py") == build
for relative in ("tools/strip_stackmap.py", "tools/verify_receipts.js"):
    assert stage_text(relative) == generated_text(relative), relative

# All root leaves are inherited; only DBOOT and the dynamically-derived ordered
# root receive the fresh domain.  No interpreter root is hard-coded.
record = json.loads(stage_text("root-commitment.json"))
old_record = json.loads(generated_text("root-commitment.json"))
assert record["order"] == old_record["order"] and record["keccak256"] == old_record["keccak256"]
node = root / "jvmevm/runtime/node_modules"
assert node.is_dir(), "refusing shared or network node dependencies"
env = {**os.environ, "NODE_PATH": str(node)}
root_script = "const {keccak256}=require('js-sha3');const h=process.argv[1].split(',');const d=keccak256(process.argv[2]);const w=x=>x.padStart(64,'0');console.log(JSON.stringify({d,r:keccak256(Buffer.from(w(d)+w('40')+w(h.length.toString(16))+h.map(w).join(''),'hex'))}));"
actual = json.loads(subprocess.check_output(["node", "-e", root_script, ",".join(record["keccak256"]), "JVMEVM:" + D + ":BOOTSTRAP:1"], cwd=root, env=env, text=True))
assert record == {**old_record, "domain": D, "dboot": actual["d"], "bootstrapRoot": actual["r"]}
limits = [49, 322481, 64, 32, 65536, 65536, 16, 64, 256, 4096, 1048576]
limits_script = "const {keccak256}=require('js-sha3');const w=x=>x.padStart(64,'0');console.log(keccak256(Buffer.from(JSON.parse(process.argv[1]).map(x=>w(x.toString(16))).join(''),'hex')));"
assert subprocess.check_output(["node", "-e", limits_script, json.dumps(limits)], cwd=root, env=env, text=True).strip() == LIMITS

parent_pins = json.loads(generated_text("build-pins.json"))
pins = json.loads(stage_text("build-pins.json"))
expected_pins = copy.deepcopy(parent_pins)
expected_pins.update({"basis": "e73e45fce", "parentEvidence": "parent-e73e45fce", "phase": "built", "domain": D,
                      "runtimeBaseline": 391507, "rawLimits": [49, 322481], "diagnosticClassBound": 142,
                      "address": "0x" + ENGINE, "owner": "0x" + OWNER, "limitsCommitment": LIMITS,
                      "engine": ENGINE_PIN, "coordinator": COORDINATOR_PIN})
assert pins == expected_pins
assert pins["bootstrapCount"] == 93 and pins["globalNativeBindings"] == 13
assert pins["stringLocalBinding"] == 10 and pins["exceptionKinds"] == 14
assert pins["maxFrames"] == 128 and pins["runtimeBaseline"] == pins["engine"]["bytes"] == 391507
assert pins["engine"]["bytes"] <= pins["runtimeCap"] == 393216
assert pins["externalLocalGas"] == 1_000_000_000 and pins["reserve"] == 25_000_000
assert pins["checkpointCap"] == 1_048_576 and pins["headCap"] == 32768
assert ENGINE_PIN["runtimeKeccak256"] in stage_text("coordinator/MCEntryCoordinator.sol")
assert ENGINE_PIN["runtimeSHA256"] in stage_text("tools/Go.txt")
assert COORDINATOR_PIN["runtimeKeccak256"] in stage_text("tools/Go.txt")
assert "raw49" in stage_text("README.md") and "raw50" in stage_text("README.md")
assert not any(p.suffix in {".jar", ".class", ".zip"} for p in stage.rglob("*"))
assert len(sys.argv) == 3 and sys.argv[1] == "--built" and Path(sys.argv[2]).resolve() == stage / "build-pins.json"
print(json.dumps({"phase": "built", "basis": "e73e45fce", "domain": D, "bootstrapImages": 93,
                  "bootstrapRoot": record["bootstrapRoot"], "rawLimits": pins["rawLimits"],
                  "diagnosticClassBound": 142, "runtimeBaseline": 391507,
                  "runtimeBytes": ENGINE_PIN["bytes"], "runtimeCap": 393216,
                  "coordinatorBytes": COORDINATOR_PIN["bytes"]}, indent=2))
