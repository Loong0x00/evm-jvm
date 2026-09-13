#!/usr/bin/env python3
"""Source-build the fixed 66-image Boolean bootstrap in a fresh ignored tree."""
from pathlib import Path
import hashlib, json, os, re, shutil, subprocess, sys

here = Path(__file__).resolve().parent
root = here.parents[3]
out = Path(sys.argv[1]).resolve()
assert out.parent == root / 'build' and out.name.startswith('java-diff-mc-boolean-') and not out.exists()
out.mkdir(); (out / 'tmp').mkdir(); (out / 'bootstrap-classes').mkdir()
node_path = os.environ.get('NODE_PATH', '')
assert node_path and os.path.isabs(node_path), 'set absolute NODE_PATH to pinned solc'
env = dict(os.environ, TMPDIR=str(out / 'tmp'), NODE_PATH=node_path, PYTHONDONTWRITEBYTECODE='1')
def run(label, args):
    with (out / (label + '.log')).open('w') as f:
        p = subprocess.run(list(map(str, args)), cwd=root, env=env, stdout=f, stderr=subprocess.STDOUT)
    assert p.returncode == 0, (label, p.returncode)

# Compile the owned Java-8 wrappers against a platform image from which every
# replaced class has been removed. This makes the appended bytes source-derived.
api = out / 'rt-without-owned-wrappers.jar'
shutil.copyfile('/usr/lib/jvm/java-8-openjdk/jre/lib/rt.jar', api)
run('strip-platform', ['zip', '-q', '-d', api, 'java/lang/System.class', 'java/lang/System$*.class', 'java/lang/IllegalArgumentException.class', 'java/lang/Boolean.class'])
run('java8-build', ['/usr/lib/jvm/java-8-openjdk/bin/javac', '-source', '8', '-target', '8', '-g:none', '-bootclasspath', api, '-d', out / 'bootstrap-classes', here / 'System.java', here / 'IllegalArgumentException.java', here / 'Boolean.java'])
run('javap', ['/usr/lib/jvm/java-8-openjdk/bin/javap', '-bootclasspath', str(out / 'bootstrap-classes') + ':' + str(api), '-c', '-p', 'java.lang.Boolean', 'java.lang.System', 'java.lang.IllegalArgumentException'])
boolean = (out / 'bootstrap-classes/java/lang/Boolean.class').read_bytes()
system = (out / 'bootstrap-classes/java/lang/System.class').read_bytes()
iae = (out / 'bootstrap-classes/java/lang/IllegalArgumentException.class').read_bytes()
assert boolean.startswith(bytes.fromhex('cafebabe')) and len(boolean) < 2048
assert len(system) == 704 and len(iae) == 159

base = (here / 'engine/MCEntryInterpreter.sol').read_text()
assert base.count('MC-SYSTEM-PROPERTY-PARENT1') == 9
# Prior 65 images stay byte-for-byte and position-for-position unchanged.
text = base.replace('bytes32[] memory h = new bytes32[](65);', 'bytes32[] memory h = new bytes32[](66);')
old = '        h[64] = keccak256(_bootstrapIllegalArgumentException());\n        return keccak256(abi.encode(DBOOT, h));'
new = '        h[64] = keccak256(_bootstrapIllegalArgumentException());\n        h[65] = keccak256(_bootstrapBoolean());\n        return keccak256(abi.encode(DBOOT, h));'
assert text.count(old) == 1; text = text.replace(old, new)
assert text.count('uint256 count = inputCount + 59 +') == 1
text = text.replace('uint256 count = inputCount + 59 +', 'uint256 count = inputCount + 60 +')
old = '        p.classes[classSlot + 25].data = _bootstrapIllegalArgumentException();'
new = old + '\n        // Boolean is a strict tail append at bootstrap index65.\n        p.classes[classSlot + 26].data = _bootstrapBoolean();'
assert text.count(old) == 1; text = text.replace(old, new)
old = '            || _isNamedClass(c, bytes("java/lang/IllegalArgumentException"));'
new = old[:-1] + '\n            || _isNamedClass(c, bytes("java/lang/Boolean"));'
assert text.count(old) == 1; text = text.replace(old, new)
anchor = '    function _bootstrapIllegalArgumentException() private pure returns (bytes memory) {'
assert text.count(anchor) == 1
text = text.replace(anchor, '    function _bootstrapBoolean() private pure returns (bytes memory) { return hex"' + boolean.hex() + '"; }\n\n' + anchor)
text = text.replace('MC-SYSTEM-PROPERTY-PARENT1', 'MC-BOOLEAN-PREFLIGHT1')
assert text.count('MC-BOOLEAN-PREFLIGHT1') == 9
eng = out / 'engine'; shutil.copytree(here / 'engine', eng); (eng / 'MCEntryInterpreter.sol').write_text(text)
run('engine-build', ['node', eng / 'build.js'])
ea = json.loads((eng / 'MCEntryInterpreter.json').read_text())
size = len(ea['deployedBytecode']) // 2
assert 348423 < size <= 384 * 1024

co = out / 'coordinator'; shutil.copytree(here / 'coordinator', co)
cp = co / 'MCEntryCoordinator.sol'; c = cp.read_text()
assert c.count('MC-SYSTEM-PROPERTY-PARENT1') == 3
c = c.replace('MC-SYSTEM-PROPERTY-PARENT1', 'MC-BOOLEAN-PREFLIGHT1')
engine_address = '0x4d432d424f4f4c45414e2d505245464c49474854'
assert len(bytes.fromhex(engine_address[2:])) == 20
c, n = re.subn(r'address private constant ENGINE = .*?;', 'address private constant ENGINE = address(bytes20(hex"' + engine_address[2:] + '"));', c); assert n == 1
c, n = re.subn(r'bytes32 private constant ENGINE_CODEHASH = hex"[0-9a-f]{64}";', 'bytes32 private constant ENGINE_CODEHASH = hex"' + ea['codeHashes']['runtimeKeccak256'] + '";', c); assert n == 1
cp.write_text(c); run('coordinator-build', ['node', co / 'build.js'])
ca = json.loads((co / 'MCEntryCoordinator.json').read_text())

# The Go transport is an evidence-only ordinary-CREATE/public-EVM driver. All
# replacement values are independently pinned and no prior domain is reused.
d = (here / 'tools/driver.go.txt').read_text()
replacements = {
 'MC-SYSTEM-PROPERTY-PARENT1': 'MC-BOOLEAN-PREFLIGHT1',
 '03914b83a8c060ac78a97417f1fbee5ee173538c694e374678e32aa6bc9683fb': ea['codeHashes']['runtimeSHA256'],
 '0x0d7f266fba7395a3c251125826d6eee3a76ae740dddddc0e163929b6cbdfbe82': '0x' + ea['codeHashes']['runtimeKeccak256'],
 '0x9f5a910a69e1cb90b17cd1be876c4f1edc00bc50a3dcb175ab5184977cd5c1f2': '0x' + ca['codeHashes']['runtimeKeccak256'],
 '348423': str(size),
 '4146': str(len(ca['deployedBytecode']) // 2),
 '0x4d432d53595350524f502d504152454e54000001': engine_address,
 '0x4d432d53595350524f502d4f574e455200000002': '0x4d432d424f4f4c45414e2d4f574e455200000002',
 '0x4d432d53595350524f502d4f5448455200000003': '0x4d432d424f4f4c45414e2d4f5448455200000003',
}
for a, b in replacements.items():
    assert a in d, a
    d = d.replace(a, b)
assert 'MC-SYSTEM-PROPERTY-PARENT1' not in d
(out / 'main.go').write_text(d)
run('gofmt', ['gofmt', '-w', out / 'main.go'])
run('go-build', ['go', 'build', '-trimpath', '-o', out / 'driver', out / 'main.go'])
run('go-vet', ['go', 'vet', out / 'main.go'])
pins = {'basis':'c32dfe260','domain':'MC-BOOLEAN-PREFLIGHT1','address':engine_address,'owner':'0x4d432d424f4f4c45414e2d4f574e455200000002','runtimeCap':393216,'accepted320Unchanged':True,'engine':{'bytes':size, **ea['codeHashes']},'coordinator':{'bytes':len(ca['deployedBytecode']) // 2, **ca['codeHashes']},'Boolean':{'bytes':len(boolean),'sha256':hashlib.sha256(boolean).hexdigest()},'System':{'bytes':len(system),'sha256':hashlib.sha256(system).hexdigest()},'IllegalArgumentException':{'bytes':len(iae),'sha256':hashlib.sha256(iae).hexdigest()},'bootstrapCount':66,'externalLocalGas':1000000000,'resourceLookupGas':1000000,'reserve':25000000,'maxFrames':128,'rawLimits':[24,262144]}
(out / 'pins.json').write_text(json.dumps(pins, indent=2) + '\n')
print(json.dumps(pins, indent=2))
