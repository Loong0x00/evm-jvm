#!/usr/bin/env python3
"""One generated-only deterministic System.currentTimeMillis long-zero and retained acceptance gate.

It consumes only the build output and fixtures made by sibling stage scripts. It
never names, opens, indexes, or resumes an original Minecraft artifact/world.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

here = Path(__file__).resolve().parent
stage = here.parent
root = here.parents[4]
build = Path(sys.argv[1]).resolve()
fixtures = Path(sys.argv[2]).resolve()
out = Path(sys.argv[3]).resolve()
assert build.parent == root / "build" and fixtures.parent == root / "build" and out.parent == root / "build"
assert build.name.startswith("java-diff-mc-system-current-time-millis-build-")
assert fixtures.name.startswith("java-diff-mc-system-current-time-millis-fixtures-")
assert out.name.startswith("java-diff-mc-system-current-time-millis-gate-") and not out.exists()
node_modules = root / "jvmevm/runtime/node_modules"
assert node_modules.is_dir(), "refusing shared or network node dependencies"
pins = json.loads((build / "pins.json").read_text())
assert pins["bootstrapCount"] == 91 and pins["rawLimits"] == [38, 285489]
assert pins["diagnosticClassBound"] == 129 and pins["engine"]["bytes"] <= 393216
assert pins["globalNativeBindings"] == 13 and pins["exceptionKinds"] == 14
assert pins["bootstrapSHA256"]["System"] == "d10707987a9b7935e1c87a6a5fc5f574ffbc42f3cd82a629d20291dffa0487bf"
assert pins["bootstrapSHA256"]["Collection"] == "a7e0e47540fc39afc022acea939c81d9a2143ef53e59f3227e2dd0ffda16487c"
assert pins["bootstrapSHA256"]["Iterable"] == "d144cca13fbb5ae0bf97773e84efb4308acbf3fe31cd9b4b0488c8a8e447a17f"
assert pins["bootstrapSHA256"]["StringBuilder"] == "22ca3088c0cebccc5714beefd40cf187dbaebe5930477559e20ab8709249ffa4"
assert pins["bootstrapSHA256"]["ThreadLocal"] == "041db70026c508194d1b13ccdc988e82fb07316a4900c3955b2d5aa3e0664d9b"
assert pins["bootstrapSHA256"]["Math"] == "e51d3e61920e9f33267ac3cb4dc2c70289d1c5fd43eb0bf6efdbbb1721c21356"
out.mkdir(); (out / "logs").mkdir(); (out / "tmp").mkdir()
started = time.monotonic()
commands = []

def fixture(label):
    return json.loads((fixtures / (label + ".json")).read_text())

def bindings(label):
    return ",".join(fixture(label)["entries"])

def report(world):
    return world.parent / "reports" / world.name

def failure(world, name):
    return json.loads((report(world) / name).read_text())

def words(value):
    return list(map(str, value["uint256Words"]))

def run(label, args, fixture_label=None, expect=0):
    env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
    if fixture_label is not None:
        spec = fixture(fixture_label)
        env["MC_ENTRY_BINDINGS"] = bindings(fixture_label)
        selected = spec.get("selectedResource")
        if selected is not None: env["MC_ENTRY_SELECTED_RESOURCE"] = selected
        else: env.pop("MC_ENTRY_SELECTED_RESOURCE", None)
    log = out / "logs" / (label + ".log")
    before = time.monotonic()
    with log.open("w") as stream:
        proc = subprocess.run(list(map(str, args)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
    row = {"label": label, "command": list(map(str, args)), "exit": proc.returncode, "elapsedSeconds": time.monotonic() - before}
    commands.append(row)
    (out / "logs" / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
    assert proc.returncode == expect, (label, proc.returncode, log)

spec = importlib.util.spec_from_file_location("checkpoint_diagnostic", here / "checkpoint_diagnostic.py")
diagnostic = importlib.util.module_from_spec(spec); spec.loader.exec_module(diagnostic)
driver = build / "driver"
coordinator = build / "coordinator/MCEntryCoordinator.json"
engine = build / "engine/MCEntryInterpreter.json"
rows = {}
canonical_labels = []

def terminal(world, raw_count, bootstrap_count=91):
    head = json.loads((world / "durable-head.json").read_text())
    assert head["lifecycle"] == head["outcome"] == 2 and head["result"] == 0
    assert len(head["decoders"]) == raw_count and head["totalClassBytes"] <= 285489
    assert head.get("selectedResourceSize", 0) <= 4096
    checkpoint = (world / "checkpoints" / (head["checkpointSHA256"] + ".bin")).read_bytes()
    assert hashlib.sha256(checkpoint).hexdigest() == head["checkpointSHA256"]
    decoded = diagnostic.inspect(checkpoint)
    assert decoded["classCount"] == raw_count + bootstrap_count
    return head, checkpoint, decoded

def finish(label, fixture_label, quantum, inspect_fn=None):
    world = out / ("world-" + label + "-q" + str(quantum))
    archive = fixtures / (fixture_label + ".zip")
    args = [world, coordinator, engine, archive, str(quantum)]
    run(label + "-q%d-start" % quantum, [driver, "setup-chain", *args], fixture_label)
    run(label + "-q%d-finish" % quantum, [driver, "finish", *args], fixture_label)
    run(label + "-q%d-reopen" % quantum, [driver, "verify", *args], fixture_label)
    spec = fixture(fixture_label)
    head, checkpoint, decoded = terminal(world, spec["bindingCount"], spec["bootstrapCount"])
    if inspect_fn is not None: inspect_fn(decoded)
    canonical_labels.append(world.name)
    return {"world": world.name, "epoch": head["epoch"], "jvmSteps": head["jvmSteps"],
            "internalSteps": head["internalSteps"], "machineRoot": head["machineRoot"],
            "opaquePayloadSHA256": hashlib.sha256(checkpoint[280:]).hexdigest()}

def q_equivalent(label, fixture_label, inspect_fn=None):
    baseline = None
    row = {}
    for quantum in (1, 7, 4096):
        value = finish(label, fixture_label, quantum, inspect_fn)
        row["direct" if quantum == 4096 else "q" + str(quantum)] = value
        if baseline is None: baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps"):
                assert value[key] == baseline[key], (label, key, value, baseline)
    rows[label] = row

def q7_direct(label, fixture_label, inspect_fn=None):
    baseline = None
    row = {}
    for quantum in (7, 4096):
        value = finish(label, fixture_label, quantum, inspect_fn)
        row["direct" if quantum == 4096 else "q7"] = value
        if baseline is None: baseline = value
        else:
            for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps"):
                assert value[key] == baseline[key], (label, key, value, baseline)
    rows[label] = row

def retained(label, fixture_label, inspect_fn=None):
    # Accepted-parent controls are rerun direct/reopen. Repeating every inherited
    # q1 corpus would exceed the fixed 20-minute whole-gate limit; only the newly
    # measured Properties path retains its complete q1/q7/direct equivalence.
    rows[label] = {"direct": finish(label, fixture_label, 4096, inspect_fn)}

# Object.getClass binding13 resolves through Object but returns the receiver's
# dynamic subclass mirror. The guest check proves literal/repeated/two-instance
# identity, and q1/q7/direct/reopen prove its canonical checkpoint encoding.
def object_getclass_initialized(decoded):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[2]["state"] == 2  # raw Child is initialized by real new.
retained("object-getclass", "object-getclass", object_getclass_initialized)

# The mirror target in this test is Dormant raw class index1. Its literal and
# Object.getClass result are legal without active use; a failing <clinit> must
# remain absent after every complete/reopened chain.
def object_getclass_noinit(decoded):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert 1 not in states, states
retained("object-getclass-noinit", "object-getclass-noinit", object_getclass_noinit)

# Null is raised by the ordinary invokevirtual receiver check before native code.
retained("object-getclass-null", "object-getclass-null")

# A raw Object remains ordinary user Code, rather than acquiring binding13 from
# its name/descriptor. This control returns its authored null under all quanta.
retained("raw-object-getclass", "raw-object-getclass")

# The shared mirror allocator preserves its pre-allocation quota check: OOM is
# catchable with no partial loader/name/mirror state. The retained general OOM
# gate keeps its full q1/q7/direct sweep; this 1023-object allocator boundary is
# exercised direct/reopen so its checkpoint corpus stays finite.
rows["object-getclass-oom"] = finish("object-getclass-oom", "object-getclass-oom", 4096)

# The single generated deflated ZIP resource is read by AS0/ZI0/DI0 into the
# initial readonly VFS before Java starts. The guest then creates the canonical
# raw mirror/loader needed by the pre-existing enumeration surface, obtains its
# URL, uses ordinary URL.openStream -> File -> FileInputStream, reads exact bytes
# and EOF, verifies close, and proves a FileOutputStream cannot mutate /ro.
def url_openstream_seed(decoded):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    # URL (raw+62), FileInputStream (raw+36), and FileOutputStream (raw+37)
    # were all genuinely initialized by the guest path.
    assert states[63]["state"] == 2 and states[37]["state"] == 2 and states[38]["state"] == 2

def url_openstream_finish(label, fixture_label, quantum):
    value = finish(label, fixture_label, quantum, url_openstream_seed)
    world = out / value["world"]
    head = json.loads((world / "durable-head.json").read_text())
    spec = fixture(fixture_label)
    assert head["selectedResourceName"] == __import__("base64").b64encode(spec["selectedResource"].encode()).decode()
    assert head["selectedResourceSize"] == spec["selectedResourceBytes"]
    assert head["selectedResourceRoot"] != "0x" + "00" * 32
    start = json.loads((report(world) / "start.json").read_text())
    selected = start["selectedResource"]
    assert selected["name"] == spec["selectedResource"] and selected["size"] == spec["selectedResourceBytes"]
    seed_address = selected["decoder"].lower()
    hashes = {key.lower(): value for key, value in start["resourceReadHashes"].items()}
    assert hashes[seed_address] == spec["selectedResourceSHA256"]
    return value

base = None
url_row = {}
for quantum in (4096,):
    value = url_openstream_finish("url-openstream", "url-openstream", quantum)
    url_row["direct" if quantum == 4096 else "q" + str(quantum)] = value
    if base is None: base = value
    else:
        for key in ("machineRoot", "opaquePayloadSHA256", "jvmSteps", "internalSteps"):
            assert value[key] == base[key], ("url-openstream", key, value, base)
rows["url-openstream"] = url_row

# Absent lookup remains empty through the real ZI0-backed enumeration and a
# direct URL cannot fabricate content: FileInputStream raises guest FNF.
retained("url-openstream-absent", "url-openstream-absent")

# Properties.load is an accepted parent control. Retain its complete direct/
# reopen path and its actual guest initialization, but reserve q1/q7/direct
# equivalence in this bounded whole gate for the newly added startsWith surface.
def properties_load_initialized(decoded):
    raw = fixture("properties-load")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 47]["state"] == 2  # Properties
    assert states[raw + 62]["state"] == 2  # URL
    assert states[raw + 36]["state"] == 2  # FileInputStream
retained("properties-load", "properties-load", properties_load_initialized)

# Parent null/escape controls remain direct/reopen; no parser behavior changes.
retained("properties-load-null", "properties-load-null")
retained("properties-load-escape", "properties-load-escape")

# Exactly4096 property units fit the parser and selected-resource caps. A custom
# generated InputStream separately proves the first 4097th unit raises guest
# IOException; these long loop boundaries use q4096/reopen only.
line4096 = finish("properties-load-line-4096", "properties-load-line-4096", 4096)
rows["properties-load-line-4096"] = line4096
line4097 = finish("properties-load-line-4097", "properties-load-line-4097", 4096)
rows["properties-load-line-4097"] = line4097

# The scalar constructor resource slot accepts exactly one 4096-byte decoder
# output. 4097 is decoded by DI0 but rejected atomically by coordinator policy.
resource4096 = finish("url-resource-4096", "url-resource-4096", 4096)
world = out / resource4096["world"]
head = json.loads((world / "durable-head.json").read_text())
assert head["selectedResourceSize"] == 4096
rows["url-resource-4096"] = resource4096
world = out / "world-url-resource-4097"
run("url-resource-4097-boundary", [driver, "boundary-create", world, coordinator, engine,
    fixtures / "url-resource-4097.zip", "4096"], "url-resource-4097")
refusal = failure(world, "boundary-refusal.json")
assert refusal["rootUnchanged"] and words(refusal) == ["27"], refusal
rows["url-resource-4097"] = refusal

# The explicit generated fixture interface refuses two names before any world,
# and coordinator constructor checks both a wrong committed resource root and a
# wrong decoder address after EVM AS0/ZI0/DI0 preparation without publishing a Head.
world = out / "world-url-resource-count2"
args = [driver, "setup-chain", world, coordinator, engine, fixtures / "url-openstream.zip", "4096"]
env = dict(os.environ, MC_ENTRY_BINDINGS=bindings("url-openstream"), MC_ENTRY_SELECTED_RESOURCE="generated/url.bin,generated/other.bin", TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
log = out / "logs/url-resource-count2.log"
with log.open("w") as stream:
    proc = subprocess.run(list(map(str, args)), cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1200)
commands.append({"label": "url-resource-count2", "command": list(map(str, args)), "exit": proc.returncode})
assert proc.returncode == 2 and not world.exists()
rows["url-resource-count2"] = {"worldExists": False}
for mode, expected in (("resource-root-tamper", ["26"]), ("resource-address-tamper", ["25"])):
    world = out / ("world-url-" + mode)
    run("url-" + mode, [driver, mode, world, coordinator, engine,
        fixtures / "url-openstream.zip", "4096"], "url-openstream")
    refusal = failure(world, "resource-tamper-refusal.json")
    assert refusal["rootUnchanged"] and words(refusal) == expected, refusal
    rows[mode] = refusal

# Arrays, primitive literals and forged Class objects remain narrow hard
# refusals. They publish no Head and cannot fabricate a generic reflection path.
for label, expected_selector, expected_code in (
    ("object-getclass-array", "0xd631c3a4", "4"),
    ("object-getclass-primitive", None, None),
    ("object-getclass-forged-mirror", None, None),
):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["rootUnchanged"], refusal
    if expected_selector is not None:
        assert refusal["selector"] == expected_selector and words(refusal)[0] == expected_code, refusal
    rows[label] = refusal

# The focused ordinary Java-8 interface signature dispatches to the replaced
# ReentrantLock image. Three successful acquisitions and matching unlocks run
# entirely as guest field mutation; no interrupt state, blocking, or scheduler
# behavior is asserted.
def lock_interruptibly_initialized(decoded):
    raw = fixture("lock-interruptibly")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 77]["state"] == 2
retained("lock-interruptibly", "lock-interruptibly", lock_interruptibly_initialized)

# A null Lock receiver reaches the existing catchable NPE path even though the
# Java declaration carries InterruptedException.
retained("lock-interruptibly-null", "lock-interruptibly-null")

# Neither replacement is initialized by a root that contains no lock symbol.
lock_noinit = finish("lock-interruptibly-uninitialized", "lock-interruptibly-uninitialized", 4096)
world = out / lock_noinit["world"]
_, _, decoded = terminal(world, fixture("lock-interruptibly-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
raw = fixture("lock-interruptibly-uninitialized")["bindingCount"]
assert raw + 75 not in states and raw + 77 not in states
rows["lock-interruptibly-uninitialized"] = lock_noinit

# StringBuilder is a real guest class: non-null chained append must preserve
# receiver identity/order, while toString creates independent guest String copies.
def stringbuilder_initialized(decoded):
    raw = fixture("stringbuilder")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 84]["state"] == 2
retained("stringbuilder", "stringbuilder", stringbuilder_initialized)

# The documented null bound is a catchable guest NPE before append allocates.
retained("stringbuilder-null", "stringbuilder-null")

# Image84 retains its narrow zero reset, then adds only the String-backed
# CharSequence range signature. Valid empty/middle/full ranges and every
# documented IAE rejection execute in ordinary guest bytecode under q1/q7/direct
# plus reopen, while all prior StringBuilder controls remain retained.
def stringbuilder_charsequence_initialized(decoded):
    raw = decoded["classCount"] - 91
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 84]["state"] == 2
q_equivalent("stringbuilder-setlength-zero", "stringbuilder-setlength-zero", stringbuilder_charsequence_initialized)
q_equivalent("stringbuilder-setlength-nonzero", "stringbuilder-setlength-nonzero", stringbuilder_charsequence_initialized)
q_equivalent("stringbuilder-charsequence-range", "stringbuilder-charsequence-range", stringbuilder_charsequence_initialized)
q_equivalent("stringbuilder-charsequence-refusal", "stringbuilder-charsequence-refusal", stringbuilder_charsequence_initialized)

# Accepted lastIndexOf witnesses remain direct/reopen parent controls. They
# demonstrate that replacing slot26 did not drop or reorder the prior method.
for label in (
    "last-index-suffix", "last-index-middle", "last-index-prefix", "last-index-overlap",
    "last-index-repeated", "last-index-absent", "last-index-empty-target",
    "last-index-empty-receiver", "last-index-longer-target", "last-index-utf16",
    "last-index-surrogate", "last-index-null",
):
    retained(label, label)

# The focused new Java-8 offset-zero startsWith(String) cases each require q1,
# q7, direct, reopen, canonical terminal state and exact UTF-16 code-unit
# comparison. No offset overload, native binding, or host comparison is used.
for label in (
    "starts-empty-prefix", "starts-longer-prefix", "starts-exact", "starts-prefix",
    "starts-absent", "starts-empty-receiver", "starts-empty-receiver-nonempty",
    "starts-utf16", "starts-surrogate-pair", "starts-high-surrogate", "starts-null",
):
    q_equivalent(label, label)

# A String[] main signature alone must not initialize the String bootstrap.
string_uninitialized = finish("string-uninitialized", "string-uninitialized", 4096)
world = out / string_uninitialized["world"]
_, _, decoded = terminal(world, fixture("string-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("string-uninitialized")["bindingCount"] + 26 not in states
rows["string-uninitialized"] = string_uninitialized

# A no-use root must leave the appended bootstrap uninitialized.
stringbuilder_uninitialized = finish("stringbuilder-uninitialized", "stringbuilder-uninitialized", 4096)
world = out / stringbuilder_uninitialized["world"]
_, _, decoded = terminal(world, fixture("stringbuilder-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("stringbuilder-uninitialized")["bindingCount"] + 84 not in states
rows["stringbuilder-uninitialized"] = stringbuilder_uninitialized

# TreeMap is an ordinary guest Object subclass with a public no-arg constructor.
# The generated Java program checks two distinct non-null allocations and a
# stable alias, without using any ordering or map operation.
def treemap_initialized(decoded):
    raw = fixture("treemap")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 85]["state"] == 2
a = retained("treemap", "treemap", treemap_initialized)
assert a is None

# A no-use root leaves the appended constructor-only image uninitialized.
treemap_uninitialized = finish("treemap-uninitialized", "treemap-uninitialized", 4096)
world = out / treemap_uninitialized["world"]
_, _, decoded = terminal(world, fixture("treemap-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("treemap-uninitialized")["bindingCount"] + 85 not in states
rows["treemap-uninitialized"] = treemap_uninitialized

# The generated quota witness allocates two 65536-char guest arrays before its
# second append reaches array-element OOM. Those live arrays cannot fit the fixed
# 1MiB checkpoint, so the pinned engine must refuse publication honestly and
# atomically rather than fabricate a catchable terminal result. The retained
# small field-arena OOM below continues to prove catchable guest OOM semantics.
world = out / "world-stringbuilder-oom-infeasible"
run("stringbuilder-oom-infeasible", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "stringbuilder-oom.zip", "4096"], "stringbuilder-oom")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x71540d20" and words(refusal) == ["1", "0"] and refusal["rootUnchanged"]
rows["stringbuilder-oom-infeasible"] = refusal

# Image84 retains the ordinary no-argument constructor, append(String), and
# toString. Its new (I)V constructor uses the accepted exact-content model:
# 0, 1, and 255 all start logically empty, then append from index0. A negative
# argument takes ordinary guest newarray and is caught as NegativeArraySizeException.
def stringbuilder_capacity_initialized(decoded):
    raw = fixture("stringbuilder-capacity-0")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 84]["state"] == 2
for label in ("stringbuilder-capacity-0", "stringbuilder-capacity-1", "stringbuilder-capacity-255",
              "stringbuilder-capacity-negative"):
    q_equivalent(label, label, stringbuilder_capacity_initialized)

# No capacity inspection/growth, general resizing, or primitive append is
# fabricated. Each omitted member form resolves before any Head exists.
for label in ("stringbuilder-capacity-omitted", "stringbuilder-ensurecapacity-omitted",
              "stringbuilder-append-int-omitted", "stringbuilder-append-charsequence-omitted"):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"], refusal
    rows[label] = refusal

# System.err: raw field resolution triggers real System <clinit>; the generated
# constructor handoff checks type assignment and identity without output APIs.
def system_initialized(decoded):
    raw = fixture("system-err")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    system = states[raw + 44]; stream = states[raw + 83]
    assert system["state"] == stream["state"] == 2
    fields = {entry["fieldIndex"]: int(entry["packedValue"], 16) for entry in system["staticValues"]}
    assert fields[2] != 0, fields  # System fields: security, properties, err.
retained("system-err", "system-err", system_initialized)

# currentTimeMillis is ordinary Java 8 bytecode in image44: its static active
# use initializes the pre-existing System/PrintStream state, then lconst_0 /
# lreturn supply a stable LOCAL replay epoch. No host, block, or wall-clock
# input is available to this fixture.
def system_current_time_millis_initialized(decoded):
    raw = fixture("system-current-time-millis")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 44]["state"] == states[raw + 83]["state"] == 2
q_equivalent("system-current-time-millis", "system-current-time-millis", system_current_time_millis_initialized)

# A separate no-use root proves neither image is fabricated/preinitialized.
noinit = finish("system-uninitialized", "system-uninitialized", 4096)
world = out / noinit["world"]
_, _, decoded = terminal(world, fixture("system-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
raw = fixture("system-uninitialized")["bindingCount"]
assert raw + 44 not in states and raw + 83 not in states
rows["system-uninitialized"] = noinit

# Retain catchable generic failed-initialization behavior while System remains
# untouched; inducing a failing System initializer would broaden the profile.
def failed_control(decoded):
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[1]["state"] == 3
    assert 46 not in states and 85 not in states
retained("failed-init", "failed-init", failed_control)

# Both owned images reject raw replacement before any guest instruction executes.
for label in ("raw-string", "raw-system", "raw-printstream", "raw-stringbuilder", "raw-treemap", "raw-lock-interruptibly-lock", "raw-lock-interruptibly-reentrant"):
    world = out / ("world-" + label)
    run(label + "-replacement", [driver, "setup-chain", world, coordinator, engine, fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
    rows[label] = refusal

# TreeMap is not a Map or SortedMap implementation. Both generated controls run
# a real TreeMap constructor first, then must stop through an EVM refusal; no
# fabricated mutation result, interface assignment, or Java terminal is allowed.
def omitted_refusal(label, expected_selector, expected_words=None, expected_missing=None):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == expected_selector and refusal["rootUnchanged"], refusal
    if expected_words is not None:
        assert words(refusal) == expected_words, refusal
    if expected_missing is not None:
        assert refusal["diagnostic"]["name"] == expected_missing, refusal
    rows[label] = refusal

# The virtual put member is absent from the constructor-only image: CallError
# code3 at the source invocation PC13 is retained as an EVM refusal, not a Map
# result or a synthetic Java exception.
omitted_refusal("treemap-mutation-omitted", "0xd631c3a4", ["3", "13"])
# The interface-call form resolves its explicit SortedMap owner and reports a
# canonical missing-class diagnostic rather than silently accepting assignment.
omitted_refusal("treemap-sortedmap-omitted", "0x555db429", expected_missing="java/util/SortedMap")

# The new ordinary Java-8 valueOf(int) surface calls the preserved public
# constructor. q1/q7/direct each reopen a canonical terminal checkpoint; the
# guest fixture covers -1, zero, min, max, equality/value/hash and distinct
# allocations without a cache identity claim.
def integer_valueof_initialized(decoded):
    raw = fixture("integer-valueof")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 70]["state"] == 2
q_equivalent("integer-valueof", "integer-valueof", integer_valueof_initialized)

# A no-use root must not initialize the replacement bootstrap.
integer_valueof_noinit = finish("integer-valueof-uninitialized", "integer-valueof-uninitialized", 4096)
world = out / integer_valueof_noinit["world"]
_, _, decoded = terminal(world, fixture("integer-valueof-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("integer-valueof-uninitialized")["bindingCount"] + 70 not in states
rows["integer-valueof-uninitialized"] = integer_valueof_noinit

# A raw java/lang/Integer cannot replace the fixed bootstrap image.
world = out / "world-raw-integer-valueof"
run("raw-integer-valueof-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-integer-valueof.zip", "4096"], "raw-integer-valueof")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-integer-valueof"] = refusal

# The one-argument String overload is ordinary Java-8 guest Code: it invokes
# the preserved decimal parseInt, then the public int constructor. Every valid,
# invalid, null, and overflow witness runs q1/q7/direct/reopen and must retain
# one canonical terminal machine/checkpoint payload across quanta.
def integer_valueof_string_initialized(decoded):
    raw = fixture("integer-valueof-string-valid")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 70]["state"] == 2
for label in (
    "integer-valueof-string-valid", "integer-valueof-string-invalid",
    "integer-valueof-string-null", "integer-valueof-string-overflow",
):
    q_equivalent(label, label, integer_valueof_string_initialized)

# Java 8's two-argument radix overload remains absent. It must be an atomic
# EVM member-resolution refusal, not a host radix parser or cache fallback.
world = out / "world-integer-valueof-string-radix-omitted"
run("integer-valueof-string-radix-omitted", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "integer-valueof-string-radix-omitted.zip", "4096"], "integer-valueof-string-radix-omitted")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"]
rows["integer-valueof-string-radix-omitted"] = refusal

# The appended Java-8 direct Object subclass has only its constructor and get.
# q1/q7/direct/reopen prove strong referent identity and null retention through
# the ordinary guest field load/store path; no GC clearing is modeled.
def weak_reference_initialized(decoded):
    raw = fixture("weak-reference")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 86]["state"] == 2
q_equivalent("weak-reference", "weak-reference", weak_reference_initialized)

# A root with no WeakReference symbol must leave image87 uninitialized.
weak_reference_noinit = finish("weak-reference-uninitialized", "weak-reference-uninitialized", 4096)
world = out / weak_reference_noinit["world"]
_, _, decoded = terminal(world, fixture("weak-reference-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("weak-reference-uninitialized")["bindingCount"] + 86 not in states
rows["weak-reference-uninitialized"] = weak_reference_noinit

# A raw java/lang/ref/WeakReference cannot replace the owned appended image.
world = out / "world-raw-weak-reference"
run("raw-weak-reference-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-weak-reference.zip", "4096"], "raw-weak-reference")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-weak-reference"] = refusal

# The bounded image intentionally omits clear and every Reference API beyond get.
world = out / "world-weak-reference-clear-omitted"
run("weak-reference-clear-omitted", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "weak-reference-clear-omitted.zip", "4096"], "weak-reference-clear-omitted")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"]
rows["weak-reference-clear-omitted"] = refusal

# The only new linkage surface is Collection extends Iterable. The focused
# generated root exercises return assignment, identity, and iterator dispatch;
# q1/q7/direct/reopen must share every terminal machine/opaque payload field.
def iterable_link_initialized(decoded):
    raw = fixture("iterable-link")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 57]["state"] == 2  # HashSet uses its existing iterator.
q_equivalent("iterable-link", "iterable-link", iterable_link_initialized)
q_equivalent("iterable-null", "iterable-null")

# An unrelated root cannot initialize the append-only Iterable image merely by
# having the image present in the canonical bootstrap tail.
iterable_noinit = finish("iterable-uninitialized", "iterable-uninitialized", 4096)
world = out / iterable_noinit["world"]
_, _, decoded = terminal(world, fixture("iterable-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("iterable-uninitialized")["bindingCount"] + 87 not in states
rows["iterable-uninitialized"] = iterable_noinit

# The append and replaced hierarchy names remain bootstrap-owned. A raw image
# cannot change Collection's new edge or substitute a different Iterable API.
for label in ("raw-iterable", "raw-collection"):
    world = out / ("world-" + label)
    run(label + "-replacement", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
    rows[label] = refusal

# forEach and spliterator are deliberately absent. Each Java-8 call site must
# refuse before a Head exists; the source verifier separately proves neither
# default method nor its Consumer/Spliterator type is in either added image.
for label in ("iterable-foreach-omitted", "iterable-spliterator-omitted"):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["rootUnchanged"], refusal
    rows[label] = refusal

# The final image supports only directly-created ThreadLocal instances. Its one
# Object field provides the bounded single-guest-thread value semantics; all
# focused set/default-null/replace/null/identity observations must survive q1,
# q7, direct, and reopened execution with identical terminal checkpoints.
def threadlocal_set_initialized(decoded):
    raw = fixture("threadlocal-set")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 88]["state"] == 2
q_equivalent("threadlocal-set", "threadlocal-set", threadlocal_set_initialized)

# Retain allocation/identity coverage under the single field image.
q_equivalent("threadlocal-constructor", "threadlocal-constructor", threadlocal_set_initialized)

# Presence of image89 does not actively initialize it before a real new.
threadlocal_noinit = finish("threadlocal-uninitialized", "threadlocal-uninitialized", 4096)
world = out / threadlocal_noinit["world"]
_, _, decoded = terminal(world, fixture("threadlocal-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("threadlocal-uninitialized")["bindingCount"] + 88 not in states
rows["threadlocal-uninitialized"] = threadlocal_noinit

# A raw java/lang/ThreadLocal cannot replace the owned image89.
world = out / "world-raw-threadlocal"
run("raw-threadlocal-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-threadlocal.zip", "4096"], "raw-threadlocal")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-threadlocal"] = refusal

# remove/withInitial and a second guest thread remain absent paths. Each must
# refuse atomically before a Head exists; no map, default factory, or thread
# scheduler is fabricated.
for label in ("threadlocal-remove-omitted", "threadlocal-withinitial-omitted", "threadlocal-multithread-omitted"):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"], refusal
    rows[label] = refusal

# A final owned image refuses subclass initialValue declarations/overrides during
# normal hierarchy validation, independently of the field's null sentinel.
for label in ("threadlocal-initialvalue-omitted", "threadlocal-overridden-initialvalue-omitted"):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0xa52e829f" and words(refusal) == ["3", "1"] and refusal["rootUnchanged"], refusal
    rows[label] = refusal

# The new image is Java 8 Math with only ordinary static (II)I min/max.
# q1/q7/direct/reopen must agree at equal, sign-crossing, and int32 extremes;
# class initialization is real active use even though the utility has no <clinit>.
def math_initialized(decoded):
    raw = fixture("math-int-min-max")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 89]["state"] == 2
q_equivalent("math-int-min-max", "math-int-min-max", math_initialized)

# An unrelated root leaves the append-only Math class absent from initialization.
math_noinit = finish("math-uninitialized", "math-uninitialized", 4096)
world = out / math_noinit["world"]
_, _, decoded = terminal(world, fixture("math-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
assert fixture("math-uninitialized")["bindingCount"] + 89 not in states
rows["math-uninitialized"] = math_noinit

# A raw Math cannot replace the owned bootstrap before any checkpoint exists.
world = out / "world-raw-math"
run("raw-math-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-math.zip", "4096"], "raw-math")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-math"] = refusal

# abs(int) and addExact(int,int) have supported operand descriptors but no
# appended members, so both remain atomic resolution refusals.
for label in ("math-abs-omitted", "math-addexact-omitted"):
    world = out / ("world-" + label)
    run(label + "-refusal", [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"], refusal
    rows[label] = refusal

# Thread.getStackTrace returns a fresh, non-null guest array with exactly zero
# entries.  Thread itself initializes through currentThread; array allocation
# resolves the canonical StackTraceElement leaf without initializing it.
def thread_empty_stack_trace_initialized(decoded):
    raw = fixture("thread-empty-stack-trace")["bindingCount"]
    states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
    assert states[raw + 50]["state"] == 2
    assert raw + 90 not in states
q_equivalent("thread-empty-stack-trace", "thread-empty-stack-trace", thread_empty_stack_trace_initialized)

# A no-use root preserves accepted Thread and the new leaf as dormant classes.
thread_empty_noinit = finish("thread-empty-stack-trace-uninitialized", "thread-empty-stack-trace-uninitialized", 4096)
world = out / thread_empty_noinit["world"]
_, _, decoded = terminal(world, fixture("thread-empty-stack-trace-uninitialized")["bindingCount"])
states = {entry["classIndex"]: entry for entry in decoded["initialization"]}
raw = fixture("thread-empty-stack-trace-uninitialized")["bindingCount"]
assert raw + 50 not in states and raw + 90 not in states
rows["thread-empty-stack-trace-uninitialized"] = thread_empty_noinit

# The new leaf is bootstrap-owned and all StackTraceElement APIs remain absent.
world = out / "world-raw-stacktraceelement"
run("raw-stacktraceelement-replacement", [driver, "setup-chain", world, coordinator, engine,
    fixtures / "raw-stacktraceelement.zip", "4096"], "raw-stacktraceelement")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x6a23ad80" and words(refusal) == ["1", "1"] and refusal["rootUnchanged"]
rows["raw-stacktraceelement"] = refusal
for label in ("stacktraceelement-constructor-omitted", "stacktraceelement-method-omitted"):
    world = out / ("world-" + label)
    run(label, [driver, "setup-chain", world, coordinator, engine,
        fixtures / (label + ".zip"), "4096"], label)
    refusal = failure(world, "start-refusal.json")
    assert refusal["selector"] == "0xd631c3a4" and words(refusal)[0] == "3" and refusal["rootUnchanged"]
    rows[label] = refusal

# Exact raw38 is the focused capacity witness: all q1/q7/direct/reopen
# chains agree. Raw39 is independently refused before mutation by the product
# driver, coordinator, and engine. Disposable widenings affect only the one
# preceding layer.
q_equivalent("raw38", "count-38")
world = out / "world-raw39-driver"
run("raw39-driver", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-39.zip", "4096"], "count-39", expect=2)
assert not world.exists(); rows["raw39-driver"] = {"worldExists": False}

def disposable_driver(label, coordinator_keccak, coordinator_bytes):
    source = (build / "main.go").read_text()
    assert source.count("len(m.Decoders) > 38") == 1 and source.count("len(parts) > 38") == 1
    source = (source.replace("len(m.Decoders) > 38", "len(m.Decoders) > 39")
                    .replace("len(parts) > 38", "len(parts) > 39"))
    old = "0x" + pins["coordinator"]["runtimeKeccak256"]
    assert source.count(old) == 1
    source = source.replace(old, "0x" + coordinator_keccak)
    old_size = "len(coordRun) != %d" % pins["coordinator"]["bytes"]
    assert source.count(old_size) == 1
    source = source.replace(old_size, "len(coordRun) != %d" % coordinator_bytes)
    path = out / (label + ".go"); exe = out / label; path.write_text(source)
    for suffix, command in (("gofmt", ["gofmt", "-w", path]), ("build", ["go", "build", "-trimpath", "-o", exe, path])):
        with (out / "logs" / (label + "-" + suffix + ".log")).open("w") as stream:
            subprocess.run(list(map(str, command)), cwd=root, stdout=stream, stderr=subprocess.STDOUT, check=True)
    return exe

coordinator_driver = disposable_driver("raw39-coordinator-driver", pins["coordinator"]["runtimeKeccak256"], pins["coordinator"]["bytes"])
world = out / "world-raw39-coordinator"
run("raw39-coordinator", [coordinator_driver, "boundary-create", world, coordinator, engine, fixtures / "count-39.zip", "4096"], "count-39")
refusal = failure(world, "boundary-refusal.json")
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["2"] and refusal["rootUnchanged"]
rows["raw39-coordinator"] = refusal

probe = out / "raw39-engine-coordinator"
shutil.copytree(build / "coordinator", probe)
probe_source = probe / "MCEntryCoordinator.sol"
text = probe_source.read_text()
assert text.count("[38]") == 4 and text.count("n > 38") == 1
probe_source.write_text(text.replace("[38]", "[39]").replace("n > 38", "n > 39"))
env = dict(os.environ, TMPDIR=str(out / "tmp"), NODE_PATH=str(node_modules), PYTHONDONTWRITEBYTECODE="1")
with (out / "logs/raw39-engine-coordinator-build.log").open("w") as stream:
    subprocess.run(["node", probe / "build.js"], cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
probe_artifact = probe / "MCEntryCoordinator.json"
probe_keccak = json.loads(probe_artifact.read_text())["codeHashes"]["runtimeKeccak256"]
engine_driver = disposable_driver("raw39-engine-driver", probe_keccak, len(json.loads(probe_artifact.read_text())["deployedBytecode"]) // 2)
world = out / "world-raw39-engine"
run("raw39-engine", [engine_driver, "setup-chain", world, probe_artifact, engine, fixtures / "count-39.zip", "4096"], "count-39")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x427cfac5" and words(refusal) == ["1", "39"] and refusal["rootUnchanged"]
rows["raw39-engine"] = refusal

# Both aggregate witnesses remain legal individual DI0 inputs; the test reaches
# the raw-package guard rather than an unrelated per-class transport refusal.
for label, total in (("count-38-285489", 285489), ("count-38-285490", 285490)):
    spec = fixture(label)
    assert spec["bindingCount"] == 38 and spec["totalClassBytes"] == total
    assert max(spec["classBytes"].values()) <= 262144

# Exactly 285489 raw bytes is admitted by the coordinator and reaches the
# engine's ordinary parser. The retained engine-side gas/reserve refusal proves
# only that this giant generated package cannot finish this bounded call; it is
# not a coordinator byte-limit refusal. 285490 is rejected atomically there.
world = out / "world-byte-285489"
run("byte-285489", [driver, "setup-chain", world, coordinator, engine, fixtures / "count-38-285489.zip", "4096"], "count-38-285489")
refusal = failure(world, "start-refusal.json")
assert refusal["selector"] == "0x71540d20" and words(refusal) == ["1", "0"] and refusal["rootUnchanged"]
rows["byte-285489"] = {"coordinatorAccepted": True, "engineRefusal": refusal}
world = out / "world-byte-285490"
run("byte-285490", [driver, "boundary-create", world, coordinator, engine, fixtures / "count-38-285490.zip", "4096"], "count-38-285490")
refusal = failure(world, "boundary-refusal.json")
assert refusal["selector"] == "0xab23ed08" and words(refusal) == ["12"] and refusal["rootUnchanged"]
rows["byte-285490"] = refusal

# Retained EnumSet, ACC_ENUM, queue, and field-arena OOM controls.
assert fixture("enumset")["focusLevelAccessFlags"] & 0x4000
for label in ("enumset", "enumset-errors", "enumset-failed"):
    retained(label, label)
world = out / "world-enumset-uninitialized"
run("enumset-uninitialized", [driver, "setup-chain", world, coordinator, engine, fixtures / "enumset-uninitialized.zip", "4096"], "enumset-uninitialized")
refusal = failure(world, "start-refusal.json")
assert refusal["rootUnchanged"]
rows["enumset-uninitialized"] = refusal
finish("queue", "queue", 4096)
rows["queue"] = {"retained": True}
retained("oom", "oom")

# Canonically re-encode every successful EVM public receipt (including reopen
# chains); this independent Node verifier has no Java or artifact authority.
run("canonical-receipts", ["node", here / "verify_receipts.js", build, out, "1", *canonical_labels])
canonical = json.loads((out / "logs/canonical-receipts.log").read_text())
whole_gate_seconds = time.monotonic() - started
assert whole_gate_seconds <= 1200, whole_gate_seconds
summary = {"profile": "MC-SYSTEM-TIME-MILLIS1", "generatedOnly": True, "results": rows,
           "canonicalReceipts": canonical, "commands": commands, "wholeGateSeconds": whole_gate_seconds,
           "limitations": "Only bootstrap image44 java/lang/System changes: currentTimeMillis()J is ordinary Java 8 lconst_0/lreturn and returns deterministic long zero. Existing System initialization/APIs, the 91-image order, runtime-derived root, raw38/285489, diagnostic129, native13, selected-resource count1/4096, CP/Code/frames/checkpoint/Head/toolchain and every other fixed limit remain pinned. This generated-only gate uses no original artifact, JAR, class, resource, StatusData, formatted status, Provider construction, factory, world, or Done input or claim. Parent alone owns accelerated unchanged-original replay."}
(out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
