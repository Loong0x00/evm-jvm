#!/usr/bin/env python3
"""Independent P37-source-only proof for the bounded String.replaceAll P38 delta."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
ROOT = STAGE.parents[3]
BASE = ROOT / "evidence/java-evm/minecraft-entry/string-replaceall-source-base-p37"
PINS = json.loads((HERE / "pins.json").read_text())
JDK = Path("/usr/lib/jvm/java-8-openjdk")
JAVAC = JDK / "bin/javac"
JAVA = JDK / "bin/java"
RTJAR = JDK / "jre/lib/rt.jar"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def keccak(data: bytes) -> str:
    env = dict(os.environ, NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"))
    return subprocess.check_output(
        ["node", "-e", "const{keccak256}=require('js-sha3');const fs=require('fs');process.stdout.write(keccak256(Buffer.from(fs.readFileSync(0,'utf8').trim(),'hex')));"],
        cwd=ROOT, env=env, input=data.hex(), text=True,
    ).strip()


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    assert count == 1, (count, old[:160])
    return text.replace(old, new, 1)


def materializer(source: str, name: str) -> bytes:
    match = re.search(
        rf'function _bootstrap{name}\(\) private pure returns \(bytes memory\) \{{\s*return hex"([0-9a-f]+)";\s*\}}',
        source,
    )
    assert match, f"missing exact _bootstrap{name} materializer"
    return bytes.fromhex(match.group(1))


def function_blocks(source: str) -> dict[tuple[str, int], str]:
    matches = list(re.finditer(r"^    function\s+([A-Za-z0-9_]+)\s*\(", source, re.M))
    out: dict[tuple[str, int], str] = {}
    counts: dict[str, int] = {}
    for i, match in enumerate(matches):
        name = match.group(1)
        ordinal = counts.get(name, 0)
        counts[name] = ordinal + 1
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        out[(name, ordinal)] = source[match.start():end]
    return out


def constants(source: str) -> dict[str, str]:
    return {name: value.strip() for name, value in re.findall(
        r"^\s*[^\n;]*?\bconstant\s+([A-Za-z0-9_]+)\s*=\s*([^;]+);", source, re.M
    )}


def root_record(source: str) -> dict:
    helper = HERE / "root_helper.py"
    spec = importlib.util.spec_from_file_location("p38_root_helper", helper)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    env = dict(os.environ, NODE_PATH=str(ROOT / "jvmevm/runtime/node_modules"))
    return module.root_record(source, "JVMEVM:MC-PATTERN-COMPILE-P36-PARENT:BOOTSTRAP:1", ROOT, env)


def compiled_images(out: Path) -> tuple[dict[str, bytes], dict[str, bytes]]:
    assert JAVAC.is_file() and JAVA.is_file() and RTJAR.is_file(), "pinned Java 8 toolchain is unavailable"
    src = STAGE / "bootstrap/string-replaceall-bounded/java"
    prior_string = HERE / "String.java.p37"
    prior_pattern = STAGE / "bootstrap/java/util/regex/Pattern.java"
    prior_pse = STAGE / "bootstrap/java/util/regex/PatternSyntaxException.java"

    # Independently recompile both pristine P37 String and P36 Pattern sources
    # before the candidate sources. These builds are compiler/source checks only.
    original_dir = out / "source-original"
    original_dir.mkdir()
    prior_string_java = original_dir / "String.java"
    prior_string_java.write_bytes(prior_string.read_bytes())
    subprocess.run([str(JAVAC), "-source", "8", "-target", "8", "-g:none", "-d", str(original_dir), str(prior_string_java)],
                   cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    rt_pattern = out / "rt-without-pattern.jar"
    shutil.copyfile(RTJAR, rt_pattern)
    subprocess.run(["zip", "-q", "-d", str(rt_pattern), "java/util/regex/Pattern.class",
                    "java/util/regex/PatternSyntaxException.class"],
                   cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    prior_pattern_dir = out / "source-pattern-p37"
    prior_pattern_dir.mkdir()
    subprocess.run([str(JAVAC), "-source", "8", "-target", "8", "-g:none", "-bootclasspath", str(rt_pattern),
                    "-d", str(prior_pattern_dir), str(prior_pattern), str(prior_pse)],
                   cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    originals = {
        "String": (original_dir / "java/lang/String.class").read_bytes(),
        "Pattern": (prior_pattern_dir / "java/util/regex/Pattern.class").read_bytes(),
        "PatternSyntaxException": (prior_pattern_dir / "java/util/regex/PatternSyntaxException.class").read_bytes(),
    }

    rt_candidate = out / "rt-without-p38-images.jar"
    shutil.copyfile(RTJAR, rt_candidate)
    subprocess.run(["zip", "-q", "-d", str(rt_candidate), "java/lang/String.class",
                    "java/util/regex/Pattern.class", "java/util/regex/PatternSyntaxException.class",
                    "java/util/regex/Matcher.class"],
                   cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    candidate_dir = out / "source-p38"
    candidate_dir.mkdir()
    sources = [
        src / "lang/String.java",
        src / "util/regex/Pattern.java",
        src / "util/regex/PatternSyntaxException.java",
        src / "util/regex/Matcher.java",
    ]
    subprocess.run([str(JAVAC), "-source", "8", "-target", "8", "-g:none", "-bootclasspath", str(rt_candidate),
                    "-d", str(candidate_dir), *map(str, sources)],
                   cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    candidates = {
        "String": (candidate_dir / "java/lang/String.class").read_bytes(),
        "Pattern": (candidate_dir / "java/util/regex/Pattern.class").read_bytes(),
        "PatternSyntaxException": (candidate_dir / "java/util/regex/PatternSyntaxException.class").read_bytes(),
        "Matcher": (candidate_dir / "java/util/regex/Matcher.class").read_bytes(),
    }
    return originals, candidates


def main() -> None:
    if len(sys.argv) not in (3, 4) or sys.argv[1] != "--artifacts":
        raise SystemExit("usage: verify_source.py --artifacts BUILT_ARTIFACT_DIR [OUTPUT_JSON]")
    artifacts = Path(sys.argv[2]).resolve()
    output = Path(sys.argv[3]).resolve() if len(sys.argv) == 4 else None
    assert artifacts.is_dir()

    manifest_bytes = (BASE / "SOURCE_MANIFEST.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    assert sha(manifest_bytes) == PINS["sourceBase"]["sourceManifestSHA256"]
    assert manifest["sourceOnly"] is True
    assert manifest["noOriginalJarClassesResourcesWorldsCheckpointsReceiptsOrBindingLists"] is True
    assert manifest["acceptedSourceCommit"] == PINS["sourceBase"]["acceptedSourceCommit"]
    assert manifest["profile"] == PINS["sourceBase"]["profile"]
    verified_base = []
    for row in manifest["files"]:
        path = BASE / row["path"]
        data = path.read_bytes()
        assert len(data) == row["bytes"] and sha(data) == row["sha256"], row["path"]
        verified_base.append(row["path"])
    base_pins = json.loads((BASE / "pins.json").read_text())
    assert base_pins["profile"] == "MC-ARRAY-CLONE-INTRINSIC-P37"
    assert base_pins["bootstrapCount"] == 103
    assert base_pins["bootstrapRoot"] == PINS["sourceBase"]["bootstrapRoot"]

    base_engine_path = BASE / "engine/MCEntryInterpreter.sol"
    base_coord_path = BASE / "coordinator/MCEntryCoordinator.sol"
    base_engine = base_engine_path.read_text()
    base_coord = base_coord_path.read_text()
    current_engine_path = HERE / "engine/MCEntryInterpreter.sol"
    current_coord_path = HERE / "coordinator/MCEntryCoordinator.sol"
    current_engine = current_engine_path.read_text()
    current_coord = current_coord_path.read_text()
    assert sha(base_engine_path.read_bytes()) == PINS["sourceBase"]["engineSourceSHA256"]
    assert sha(base_coord_path.read_bytes()) == PINS["sourceBase"]["coordinatorSourceSHA256"]
    for role in ("engine", "coordinator"):
        assert sha((BASE / role / "build.js").read_bytes()) == sha((HERE / role / "build.js").read_bytes())

    # Source chain provenance: the pristine String source is the non-parent
    # Java-8 bootstrap source that rebuilds P37 slot26 exactly.
    original_string_source = (HERE / "String.java.p37").read_bytes()
    assert sha(original_string_source) == PINS["stringP37SourceSHA256"]
    expected_string = original_string_source.decode()
    expected_string = replace_once(expected_string, "import java.util.Locale;\n",
                                   "import java.util.Locale;\nimport java.util.regex.Pattern;\n")
    expected_string = replace_once(
        expected_string,
        "  public native String[] split(String regex);\n  public int indexOf(int ch) {",
        "  public native String[] split(String regex);\n"
        "  /** Replaces all non-overlapping matches in the supported compiled Pattern profile. */\n"
        "  public String replaceAll(String regex, String replacement) {\n"
        "    return Pattern.compile(regex).matcher(this).replaceAll(replacement);\n"
        "  }\n"
        "  public int indexOf(int ch) {",
    )
    current_string_source = (STAGE / "bootstrap/string-replaceall-bounded/java/lang/String.java").read_text()
    assert current_string_source == expected_string, "String changed beyond the exact appended wrapper/import"

    # The accepted P36 Pattern source is the only older regex source. P38 adds
    # matcher construction and a private-token matcher helper; all compiler and
    # syntax-failure methods below the insertion remain byte-for-byte source-equal.
    prior_pattern_source = (STAGE / "bootstrap/java/util/regex/Pattern.java").read_text()
    current_pattern_source = (STAGE / "bootstrap/string-replaceall-bounded/java/util/regex/Pattern.java").read_text()
    assert sha((STAGE / "bootstrap/java/util/regex/PatternSyntaxException.java").read_bytes()) == PINS["patternSyntaxExceptionSourceSHA256"]
    assert (STAGE / "bootstrap/string-replaceall-bounded/java/util/regex/PatternSyntaxException.java").read_bytes() == (STAGE / "bootstrap/java/util/regex/PatternSyntaxException.java").read_bytes()
    assert sha((STAGE / "bootstrap/string-replaceall-bounded/java/util/regex/Pattern.java").read_bytes()) == PINS["patternSourceSHA256"]
    assert sha((STAGE / "bootstrap/string-replaceall-bounded/java/util/regex/Matcher.java").read_bytes()) == PINS["matcherSourceSHA256"]
    assert "public Matcher matcher(CharSequence input)" in current_pattern_source
    assert "int matchAt(CharSequence input, int start, int inputLength)" in current_pattern_source
    assert "private final int[] compiled;" in current_pattern_source
    assert current_pattern_source.count("private static native void unsupportedBranch();") == 1
    assert "find(" not in (STAGE / "bootstrap/string-replaceall-bounded/java/util/regex/Matcher.java").read_text()
    assert "public String replaceAll(String replacement)" in (STAGE / "bootstrap/string-replaceall-bounded/java/util/regex/Matcher.java").read_text()

    with tempfile.TemporaryDirectory(prefix="mc-p38-source-proof-", dir=ROOT / "build") as name:
        compile_root = Path(name)
        originals, images = compiled_images(compile_root)
        assert sha(originals["String"]) == "259bed03edf8602dca9ad26e639cb7668b8da38d62422b80788d8339020017fe"
        assert sha(originals["Pattern"]) == "329e8d775f14abeab2432726a199226aee2f79d3b1dbae7638e74221ead04947"
        assert sha(originals["PatternSyntaxException"]) == "2b8e5e3ee19502fa88c3dfe06948777500ad71a77708f9b1f2685b396ee067d7"
        base_images = {
            "String": materializer(base_engine, "String"),
            "Pattern": materializer(base_engine, "Pattern"),
            "PatternSyntaxException": materializer(base_engine, "PatternSyntaxException"),
        }
        assert originals == base_images, "P37 source chain does not rebuild its exact current String/Pattern images"
        assert images["PatternSyntaxException"] == base_images["PatternSyntaxException"]
        for image_name in ("String", "Pattern", "Matcher"):
            assert materializer(current_engine, image_name) == images[image_name], f"{image_name} materializer differs from fresh Java 8 source"
        # Regenerate the expected engine from the exact P37 snapshot and freshly
        # compiled bytes; a source diff outside the frozen append is rejected.
        generated_engine = compile_root / "expected-MCEntryInterpreter.sol"
        subprocess.run([sys.executable, str(STAGE / "tools/string-replaceall-bounded/generate_engine_source.py"),
                        str(compile_root / "source-p38"), str(generated_engine)],
                       cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert generated_engine.read_bytes() == current_engine_path.read_bytes(), "engine differs beyond generated P37->P38 source/materializer delta"

    base_root = root_record(base_engine)
    candidate_root = root_record(current_engine)
    assert base_root["root"] == PINS["sourceBase"]["bootstrapRoot"]
    assert len(base_root["leaves"]) == 103
    assert candidate_root["root"] == PINS["bootstrap"]["root"]
    assert len(candidate_root["leaves"]) == 104
    for i in range(103):
        if i not in (26, 101):
            assert base_root["leaves"][i] == candidate_root["leaves"][i], f"prior image/order changed at slot {i}"
    assert candidate_root["leaves"][103] == keccak(materializer(current_engine, "Matcher"))
    assert materializer(current_engine, "PatternSyntaxException") == materializer(base_engine, "PatternSyntaxException")

    old_functions = function_blocks(base_engine)
    new_functions = function_blocks(current_engine)
    assert set(new_functions) - set(old_functions) == {("_bootstrapMatcher", 0)}
    assert set(old_functions) - set(new_functions) == set()
    # PatternSyntaxException's text block becomes non-final when the append is
    # added, so compare its materialized bytes separately. All other function
    # blocks must be the precisely generated P38 delta.
    allowed_functions = {
        ("_appendTailBootstraps", 0), ("_bootstrapPattern", 0),
        ("_bootstrapPatternSyntaxException", 0), ("_bootstrapRoot", 0),
        ("_bootstrapString", 0), ("_isReservedRegexClass", 0), ("_prepare", 0),
    }
    changed_functions = {key for key in old_functions if old_functions[key] != new_functions[key]}
    assert changed_functions == allowed_functions, sorted(changed_functions)
    old_constants, new_constants = constants(base_engine), constants(current_engine)
    assert old_constants.keys() == new_constants.keys()
    changed_constants = sorted(k for k in old_constants if old_constants[k] != new_constants[k])
    expected_changed_constants = sorted(["EMPTY_ARGS_COMMITMENT", "DROOT", "DART", "DCFG", "DMACH", "DSEED", "DVFS", "DFILE"])
    assert changed_constants == expected_changed_constants, changed_constants
    assert old_constants["DBOOT"] == new_constants["DBOOT"]
    assert "MC-ARRAY-CLONE-INTRINSIC-P37" not in current_engine
    for name in ("_nativeBinding", "_stringNativeBinding", "_vfsNativeBinding"):
        assert [x for x in function_blocks(base_engine).items() if x[0][0] == name] == [
            x for x in function_blocks(current_engine).items() if x[0][0] == name
        ], f"native binding logic changed: {name}"

    base_coord_functions = function_blocks(base_coord)
    new_coord_functions = function_blocks(current_coord)
    assert base_coord_functions == new_coord_functions, "coordinator function semantics changed"
    old_coord_constants, new_coord_constants = constants(base_coord), constants(current_coord)
    assert old_coord_constants.keys() == new_coord_constants.keys()
    changed_coord_constants = sorted(k for k in old_coord_constants if old_coord_constants[k] != new_coord_constants[k])
    assert changed_coord_constants == ["CLASS_DOMAIN", "ENGINE_CODEHASH", "PACKAGE_DOMAIN", "SEED_DOMAIN", "VM_DOMAIN"]

    engine_artifact = json.loads((artifacts / "engine/MCEntryInterpreter.json").read_text())
    coordinator_artifact = json.loads((artifacts / "coordinator/MCEntryCoordinator.json").read_text())
    base_engine_artifact = json.loads((BASE / "engine/MCEntryInterpreter.json").read_text())
    base_coordinator_artifact = json.loads((BASE / "coordinator/MCEntryCoordinator.json").read_text())
    assert engine_artifact["abi"] == base_engine_artifact["abi"]
    assert engine_artifact["storageLayout"] == base_engine_artifact["storageLayout"]
    assert coordinator_artifact["abi"] == base_coordinator_artifact["abi"]
    assert coordinator_artifact["storageLayout"] == base_coordinator_artifact["storageLayout"]
    engine_runtime = bytes.fromhex(engine_artifact["deployedBytecode"].removeprefix("0x"))
    engine_init = bytes.fromhex(engine_artifact["bytecode"].removeprefix("0x"))
    coordinator_runtime = bytes.fromhex(coordinator_artifact["deployedBytecode"].removeprefix("0x"))
    coordinator_init = bytes.fromhex(coordinator_artifact["bytecode"].removeprefix("0x"))
    assert len(engine_runtime) == PINS["engineRuntimeBytes"] <= PINS["runtimeCapBytes"]
    assert sha(engine_runtime) == PINS["engineRuntimeSHA256"]
    assert keccak(engine_runtime) == PINS["engineRuntimeKeccak256"]
    assert len(engine_init) == PINS["engineInitBytes"] and sha(engine_init) == PINS["engineInitSHA256"]
    assert sha(current_engine_path.read_bytes()) == PINS["engineSourceSHA256"]
    assert len(coordinator_runtime) == PINS["coordinatorRuntimeBytes"]
    assert sha(coordinator_runtime) == PINS["coordinatorRuntimeSHA256"]
    assert keccak(coordinator_runtime) == PINS["coordinatorRuntimeKeccak256"]
    assert len(coordinator_init) == PINS["coordinatorInitBytes"] and sha(coordinator_init) == PINS["coordinatorInitSHA256"]
    assert sha(current_coord_path.read_bytes()) == PINS["coordinatorSourceSHA256"]
    assert engine_artifact["compiler"]["version"] == "0.8.30+commit.73712a01.Emscripten.clang"
    assert coordinator_artifact["compiler"]["version"] == "0.8.30+commit.73712a01.Emscripten.clang"
    assert engine_artifact["codeHashes"]["runtimeKeccak256"].removeprefix("0x") in current_coord

    rows = []
    for name, image in (("String", materializer(current_engine, "String")),
                        ("Pattern", materializer(current_engine, "Pattern")),
                        ("PatternSyntaxException", materializer(current_engine, "PatternSyntaxException")),
                        ("Matcher", materializer(current_engine, "Matcher"))):
        row = {"name": name, "bytes": len(image), "sha256": sha(image), "keccak256": keccak(image)}
        rows.append(row)
        if name == "Matcher":
            assert row["bytes"] == PINS["bootstrap"]["newImages"][0]["bytes"]
            assert row["sha256"] == PINS["bootstrap"]["newImages"][0]["sha256"]
            assert row["keccak256"] == PINS["bootstrap"]["newImages"][0]["keccak256"]
    assert len(materializer(current_engine, "String")) == 2198
    assert len(materializer(current_engine, "Pattern")) == 4834

    proof = {
        "status": "PASS",
        "profile": PINS["profile"],
        "sourceOnly": True,
        "sourceBase": "exact P37 source-only snapshot; original JAR/class/resource/world/checkpoint/receipt/binding list not read",
        "sourceBaseManifestSHA256": sha(manifest_bytes),
        "sourceBaseFilesVerified": verified_base,
        "sourceBaseCommit": manifest["acceptedSourceCommit"],
        "baseBootstrapRoot": base_root["root"],
        "candidateBootstrapRoot": candidate_root["root"],
        "bootstrapCount": len(candidate_root["leaves"]),
        "unchangedPriorLeaves": 101,
        "changedPriorSlots": [26, 101],
        "newImages": rows,
        "engineChangedFunctions": sorted(f"{name}#{ordinal}" for name, ordinal in changed_functions),
        "newEngineFunction": "_bootstrapMatcher",
        "engineChangedConstants": changed_constants,
        "coordinatorChangedConstants": changed_coord_constants,
        "engineABIAndStorageUnchanged": True,
        "coordinatorABIAndStorageUnchanged": True,
        "globalNativeBindingsBeforeAfter": [21, 21],
        "stringLocalBindingsBeforeAfter": [12, 12],
        "newOperationalNativeBindings": 0,
        "engine": {"sourceSHA256": sha(current_engine_path.read_bytes()), "initBytes": len(engine_init),
                   "runtimeBytes": len(engine_runtime), "runtimeSHA256": sha(engine_runtime),
                   "runtimeKeccak256": keccak(engine_runtime)},
        "coordinator": {"sourceSHA256": sha(current_coord_path.read_bytes()), "initBytes": len(coordinator_init),
                        "runtimeBytes": len(coordinator_runtime), "runtimeSHA256": sha(coordinator_runtime),
                        "runtimeKeccak256": keccak(coordinator_runtime)},
        "runtimeCapBytes": PINS["runtimeCapBytes"],
        "checkpointCapBytes": PINS["checkpointCapBytes"],
        "executionBoundary": "local preinstalled-code runtime.Call only; no EIP170/CREATE claim for engine",
        "hostOriginalExecution": False,
        "originalMinecraftInputsRead": False,
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps(proof, sort_keys=True))


if __name__ == "__main__":
    main()
