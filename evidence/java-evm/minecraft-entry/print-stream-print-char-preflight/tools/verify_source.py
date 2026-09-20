#!/usr/bin/env python3
"""Verify the sole image83/finite-loop layout delta for PrintStream.print(char)."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,subprocess,sys
sys.dont_write_bytecode=True
here=Path(__file__).resolve().parent;stage=here.parent;root=here.parents[4]
parent=stage.parent/'print-stream-println-string-preflight'
PD,D='MC-PRINTLN-STRING-0001','MC-PRINT-CHAR-SINK-001'
PE,E='4d432d5052494e544c4e2d535452494e472d3031','4d432d5052494e542d434841522d53494e4b2d33'
PO,O='4d432d5052494e544c4e2d535452494e472d3032','4d432d5052494e542d434841522d53494e4b2d34'
IMAGE_SHA='af8d5e198451494ab7a20f6f92c1559dedc3591a082268e50b9b6c9ccca16017'
IMAGE_KECCAK='3731cc740c09a9df0c76d9775252bff86b931e928d443a2e340f9d7076deca45'
STALE_INVALID_IMAGE_SHA='5bf25322cbe18f3d7d22e8a258652c63741306d3fda03998ceb78cff129bdd95'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def _u2(data, at):
 assert at + 2 <= len(data)
 return int.from_bytes(data[at:at + 2], 'big'), at + 2
def _u4(data, at):
 assert at + 4 <= len(data)
 return int.from_bytes(data[at:at + 4], 'big'), at + 4
def _class_members(data):
 """Return enough classfile structure to prove member descriptors, not snippets."""
 assert data[:8] == bytes.fromhex('cafebabe00000034')
 at = 8
 count, at = _u2(data, at)
 cp = [None] * count
 index = 1
 while index < count:
  assert at < len(data)
  tag = data[at]; at += 1
  if tag == 1:
   size, at = _u2(data, at); assert at + size <= len(data)
   cp[index] = ('utf8', data[at:at + size]); at += size
  elif tag in (3, 4):
   assert at + 4 <= len(data); at += 4
  elif tag in (5, 6):
   assert at + 8 <= len(data); at += 8; index += 1
  elif tag in (7, 8, 16, 19, 20):
   assert at + 2 <= len(data); at += 2
  elif tag in (9, 10, 11, 12, 18):
   assert at + 4 <= len(data); at += 4
  elif tag == 15:
   assert at + 3 <= len(data); at += 3
  else:
   raise AssertionError(('constant-pool-tag', tag))
  index += 1
 assert at + 8 <= len(data); at += 6
 interfaces, at = _u2(data, at); assert at + 2 * interfaces <= len(data); at += 2 * interfaces
 def utf(index):
  assert 0 < index < count and cp[index] is not None and cp[index][0] == 'utf8'
  return cp[index][1]
 def members():
  nonlocal at
  amount, at = _u2(data, at)
  result = []
  for _ in range(amount):
   access, at = _u2(data, at)
   name_index, at = _u2(data, at)
   descriptor_offset = at
   descriptor_index, at = _u2(data, at)
   attributes, at = _u2(data, at)
   attrs = []
   for _ in range(attributes):
    attribute_name, at = _u2(data, at)
    size, at = _u4(data, at); assert at + size <= len(data)
    attrs.append((utf(attribute_name), data[at:at + size])); at += size
   result.append({'access':access, 'name':utf(name_index), 'descriptor':utf(descriptor_index),
                  'descriptorIndex':descriptor_index, 'descriptorOffset':descriptor_offset,
                  'attributes':attrs})
  return result
 fields = members(); methods = members()
 attributes, at = _u2(data, at)
 for _ in range(attributes):
  _, at = _u2(data, at); size, at = _u4(data, at); assert at + size <= len(data); at += size
 assert at == len(data)
 return fields, methods
def _code(member):
 assert len(member['attributes']) == 1 and member['attributes'][0][0] == b'Code'
 data = member['attributes'][0][1]; at = 0
 maximum_stack, at = _u2(data, at); maximum_locals, at = _u2(data, at)
 size, at = _u4(data, at); assert at + size <= len(data)
 code = data[at:at + size]; at += size
 handlers, at = _u2(data, at); assert at + handlers * 8 <= len(data); at += handlers * 8
 attributes, at = _u2(data, at)
 for _ in range(attributes):
  _, at = _u2(data, at); nested_size, at = _u4(data, at); assert at + nested_size <= len(data); at += nested_size
 assert at == len(data)
 return maximum_stack, maximum_locals, code
def _assert_print_stream_contract(data):
 fields, methods = _class_members(data)
 assert [(x['access'], x['name'], x['descriptor']) for x in fields] == [
  (2, b'println', b'Ljava/lang/String;'), (2, b'print', b'C')]
 assert [(x['access'], x['name'], x['descriptor']) for x in methods] == [
  (1, b'<init>', b'()V'), (1, b'println', b'(Ljava/lang/String;)V'), (1, b'print', b'(C)V')]
 assert all(x['descriptor'].startswith(b'(') for x in methods)
 assert _code(methods[0]) == (1, 1, bytes.fromhex('2ab70001b1'))
 assert _code(methods[1]) == (2, 2, bytes.fromhex('2bc22bc32a2bb50002b1'))
 assert _code(methods[2]) == (2, 2, bytes.fromhex('2a1bb5000fb1'))
 return fields, methods
inputs={
 'engine/MCEntryInterpreter.sol':parent/'engine/MCEntryInterpreter.sol','coordinator/MCEntryCoordinator.sol':parent/'coordinator/MCEntryCoordinator.sol','tools/Go.txt':parent/'tools/Go.txt','tools/checkpoint_diagnostic.py':parent/'tools/checkpoint_diagnostic.py','tools/checkpoint_frames.py':parent/'tools/checkpoint_frames.py','tools/verify_receipts.js':parent/'tools/verify_receipts.js','engine/build.js':parent/'engine/build.js','coordinator/build.js':parent/'coordinator/build.js','build-pins.json':parent/'build-pins.json','tools/gate.py':parent/'tools/gate.py','tools/generate_fixtures.py':parent/'tools/generate_fixtures.py','root-commitment.json':parent/'root-commitment.json'}
assert json.loads((stage/'parent-input.json').read_text())=={'basis':'3dee801e7','parentEvidence':'print-stream-println-string-preflight','fixtureBasis':'print-stream-println-string-preflight','sha256':{n:sha(p) for n,p in inputs.items()}}
parent_pins=json.loads((parent/'build-pins.json').read_text())
assert parent_pins['domain']==PD and parent_pins['engine']['bytes']==393206
assert parent_pins['runtimeCap']==393216 and parent_pins['bootstrapCount']==91 and parent_pins['rawLimits']==[38,285489]
# Exact local producer/image: two private fields, Object constructor, preserved println and char putfield.
# Parse the classfile member table so a field descriptor `C` can never be mistaken
# for the required print method descriptor `(C)V` again.
spec=importlib.util.spec_from_file_location('print_stream_image',stage/'bootstrap/build_print_stream.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);image=mod.build()
assert len(image)==317 and hashlib.sha256(image).hexdigest()==IMAGE_SHA and IMAGE_SHA!=STALE_INVALID_IMAGE_SHA
assert image.hex()==''.join((stage/'bootstrap/java/io/PrintStream.class.hex').read_text().split())
assert image.startswith(bytes.fromhex('cafebabe0000003400150a0004000b090003000c07000d07000e'))
assert image.count(bytes.fromhex('0002000900050000'))==1 and image.count(bytes.fromhex('0002001000110000'))==1
fields,methods=_assert_print_stream_contract(image)
# The old 305-byte image gave `print` the field's bare `C` descriptor. A
# structurally intact descriptor-index mutation must fail this verifier.
invalid=bytearray(image);invalid[methods[2]['descriptorOffset']:methods[2]['descriptorOffset']+2]=fields[1]['descriptorIndex'].to_bytes(2,'big')
try:_assert_print_stream_contract(bytes(invalid))
except AssertionError:pass
else:raise AssertionError('accepted print descriptor C')
assert image.count(b'java/io/PrintStream')==1 and image.count(b'Ljava/lang/String;')==2
source=(stage/'bootstrap/java/io/PrintStream.java').read_text()
for text in ('private String println;','private char print;','public PrintStream() {}','public void println(String line)','synchronized (line) {}','println = line;','public void print(char codeUnit)','print = codeUnit;'):
 assert source.count(text)==1,text
# Mechanically recover the unoptimized image/domain-only layout from the accepted parent.
p=(parent/'engine/MCEntryInterpreter.sol').read_text();assert p.count(PD)==9
pre=p.replace(PD,D)
old_comment='''    /// @dev Bounded Java 8 PrintStream: constructor plus println(String) only.
    /// @dev println performs a balanced monitor null check then stores that exact reference in private println.
'''
new_comment='''    /// @dev Bounded Java 8 PrintStream: retained println(String) plus bounded print(char).
    /// @dev println preserves monitor/null/reference semantics; print stores one UTF-16 code unit privately.
'''
assert pre.count(old_comment)==1;pre=pre.replace(old_comment,new_comment)
pattern=r'(function _bootstrapPrintStream\(\) private pure returns \(bytes memory\) \{ return hex")[0-9a-f]+("; \})'
assert len(re.findall(pattern,pre))==1;pre,n=re.subn(pattern,r'\g<1>'+image.hex()+r'\g<2>',pre);assert n==1
assert pre.count('hex"03915016b845257751cbb6de613d95effdc3c84cd4b59216de7783d0ca95ff2e"')==1
pre=pre.replace('hex"03915016b845257751cbb6de613d95effdc3c84cd4b59216de7783d0ca95ff2e"','hex"'+IMAGE_KECCAK+'"')
assert (stage/'engine/pre-layout-MCEntryInterpreter.sol').read_text()==pre
# Every cleanup is a private strict finite loop whose relevant index/offset is bounded
# before the loop: raw classes <=38/285489, parsed names/CP slices <= class bytes,
# VFS/array/string units <= profile allocation limits, and checkpoint args <=8.
# The only code-layout recovery is ten exact private unchecked regions (twelve loops).  Every bound is
# already finite before entry: parsed methods/names/slices are within class data,
# external raw input is at most38/285489, and checkpoint arguments are at most8.
# Array/bytes bounds checks remain emitted; unchecked suppresses only unreachable
# uint256 overflow checks for these bounded increments/offsets.
method_loop='''for (uint256 m = 0; m < methodsCount; ++m) {
            uint16 access = _u2(r);'''
assert pre.count(method_loop)==1
engine=pre.replace(method_loop, '''unchecked { for (uint256 m; m < methodsCount; ++m) {
            uint16 access = _u2(r);''')
method_tail='''            c.methods[m] = packed;
        }
        _skipAttributes(r);'''
assert engine.count(method_tail)==1
engine=engine.replace(method_tail, '''            c.methods[m] = packed;
        } }
        _skipAttributes(r);''')
package_loop='''        uint256 aSlash;
        uint256 bSlash;
        for (uint256 i = 0; i < a.thisNameLength; ++i) {
            if (a.data[a.thisNameOffset + i] == bytes1("/")) aSlash = i + 1;
        }
        for (uint256 i = 0; i < b.thisNameLength; ++i) {
            if (b.data[b.thisNameOffset + i] == bytes1("/")) bSlash = i + 1;
        }
        if (aSlash != bSlash) return false;
        for (uint256 i = 0; i < aSlash; ++i) {
            if (a.data[a.thisNameOffset + i] != b.data[b.thisNameOffset + i]) return false;
        }
'''
assert engine.count(package_loop)==1
engine=engine.replace(package_loop, '''        uint256 aSlash;
        uint256 bSlash;
        unchecked {
            for (uint256 i; i < a.thisNameLength; ++i) {
                if (a.data[a.thisNameOffset + i] == bytes1("/")) aSlash = i + 1;
            }
            for (uint256 i; i < b.thisNameLength; ++i) {
                if (b.data[b.thisNameOffset + i] == bytes1("/")) bSlash = i + 1;
            }
            if (aSlash != bSlash) return false;
            for (uint256 i; i < aSlash; ++i) {
                if (a.data[a.thisNameOffset + i] != b.data[b.thisNameOffset + i]) return false;
            }
        }
''')
generic_loops=[
'''for (uint256 i = 0; i < a.thisNameLength; ++i) {
            if (a.data[a.thisNameOffset + i] != b.data[b.thisNameOffset + i]) return false;
        }''',
'''for (uint256 i = 0; i < n; ++i) {
            bytes1 ch = data[off + i];
            if (ch == bytes1(".") || ch == bytes1(";") || ch == bytes1("[")
                || ch == bytes1("/") || ch == bytes1("<") || ch == bytes1(">")
                || uint8(ch) == 0) return false;
        }''',
'''for (uint256 i = 0; i < n; ++i) {
            bytes1 ch = data[off + i];
            if (ch == bytes1(".") || ch == bytes1(";") || ch == bytes1("[")
                || uint8(ch) == 0) return false;
            if (ch == bytes1("/")) {
                if (slash) return false;
                slash = true;
            } else slash = false;
        }''',
'for (uint256 i; i < n; ++i) name[i] = data[off + i];',
'for (uint256 i; i < length; ++i) value[i] = data[n + i];',
'''for (uint256 i; i < value.length; ++i) {
            uint8 c = uint8(value[i]);
            if (c == 0 || c > 0x7f) return false;
        }''',
'for (uint256 i; i < rawClasses.length; ++i) total += rawClasses[i].length;',
'for (uint256 i; i < args.length; ++i) at = _put(out, at, uint32(args[i]), 4);',
]
for loop in generic_loops:
 assert engine.count(loop)==1,loop[:48]
 engine=engine.replace(loop,'unchecked { '+loop+' }')
assert (stage/'engine/MCEntryInterpreter.sol').read_text()==engine
assert engine.count('unchecked { for (uint256')==12 # three inherited, one method, eight generic

for invariant in ('h[0] = keccak256(_bootstrapObject());','h[83] = DBOOT_PRINT_STREAM;','h[84] = keccak256(_bootstrapStringBuilder());','new bytes32[](91)','MAX_RAW_CLASSES = 38;','MAX_RAW_BYTES = 285489;','MAX_FRAMES = 128;','COMMIT_RESERVE = 25_000_000;','return keccak256(abi.encode(DBOOT, h));'):
 assert engine.count(invariant)==1,invariant
assert engine.count('DBOOT_PRINT_STREAM')==2 and 'DBOOT_OBJECT' not in engine
# Recompute ordered root and prove image83 is the only altered leaf.
base_root=json.loads((parent/'root-commitment.json').read_text());leaves=list(base_root['keccak256'])
js=r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8")),w=n=>{const b=Buffer.alloc(32);b.writeUInt32BE(n,28);return b};const leaf=keccak256(Buffer.from(x.image,"hex"));x.leaves[83]=leaf;const d=keccak256(Buffer.from("JVMEVM:"+x.domain+":BOOTSTRAP:1"));const r=keccak256(Buffer.concat([Buffer.from(d,"hex"),w(64),w(x.leaves.length),...x.leaves.map(z=>Buffer.from(z,"hex"))]));console.log(JSON.stringify({leaf,d,r,leaves:x.leaves}));'''
node_modules=root/'jvmevm/runtime/node_modules';assert node_modules.is_dir()
calc=json.loads(subprocess.run(['node','-e',js],input=json.dumps({'domain':D,'image':image.hex(),'leaves':leaves}),text=True,capture_output=True,check=True,env={**os.environ,'NODE_PATH':str(node_modules)}).stdout)
assert calc['leaf']==IMAGE_KECCAK
record=json.loads((stage/'root-commitment.json').read_text())
assert record=={'domain':D,'bootstrapCount':91,'dboot':calc['d'],'bootstrapRoot':calc['r'],'order':base_root['order'],'keccak256':calc['leaves']}
assert [i for i,(a,b) in enumerate(zip(base_root['keccak256'],record['keccak256'])) if a!=b]==[83]
assert record['keccak256'][0]==base_root['keccak256'][0]
for name in ('checkpoint_diagnostic.py','checkpoint_frames.py','verify_receipts.js','strip_stackmap.py'):
 assert (stage/'tools'/name).read_bytes()==(parent/'tools'/name).read_bytes(),name
assert (stage/'engine/build.js').read_bytes()==(parent/'engine/build.js').read_bytes()
assert (stage/'coordinator/build.js').read_bytes()==(parent/'coordinator/build.js').read_bytes()
initial_coord=(parent/'coordinator/MCEntryCoordinator.sol').read_text().replace(PD,D).replace(PE,E)
initial_driver=(parent/'tools/Go.txt').read_text().replace(PD,D).replace(PE,E).replace(PO,O)
args=sys.argv[1:]
if args==['--prebuild']:
 assert not (stage/'build-pins.json').exists()
 assert (stage/'coordinator/MCEntryCoordinator.sol').read_text()==initial_coord
 assert (stage/'tools/Go.txt').read_text()==initial_driver
 phase='prebuild';runtime=None
else:
 assert len(args)==2 and args[0]=='--built'; pins=json.loads(Path(args[1]).read_text())
 boot=dict(parent_pins['bootstrapSHA256']);boot['PrintStream']=IMAGE_SHA
 expected={'basis':'3dee801e7','parentEvidence':'print-stream-println-string-preflight','phase':'built','domain':D,'runtimeBaseline':393206,'runtimeCap':393216,'bootstrapCount':91,'bootstrapSHA256':boot,'globalNativeBindings':13,'stringLocalBinding':10,'exceptionKinds':14,'maxFrames':128,'externalLocalGas':1000000000,'reserve':25000000,'rawLimits':[38,285489],'checkpointCap':1048576,'headCap':32768,'diagnosticClassBound':129,'address':'0x'+E,'owner':'0x'+O,'limitsCommitment':parent_pins['limitsCommitment'],'compiler':parent_pins['compiler'],'engine':pins['engine'],'coordinator':pins['coordinator']}
 assert pins==expected and pins['engine']['bytes']<=393216 and pins['coordinator']['bytes']==5394
 coord=initial_coord.replace(parent_pins['engine']['runtimeKeccak256'],pins['engine']['runtimeKeccak256'])
 assert (stage/'coordinator/MCEntryCoordinator.sol').read_text()==coord
 driver=initial_driver
 for old,new in ((parent_pins['engine']['runtimeSHA256'],pins['engine']['runtimeSHA256']),('0x'+parent_pins['engine']['runtimeKeccak256'],'0x'+pins['engine']['runtimeKeccak256']),('0x'+parent_pins['coordinator']['runtimeKeccak256'],'0x'+pins['coordinator']['runtimeKeccak256'])):
  assert driver.count(old)==1;driver=driver.replace(old,new)
 for pat,repl in ((r'len\(coordRun\) != \d+','len(coordRun) != %d'%pins['coordinator']['bytes']),(r'len\(engineRun\) != \d+','len(engineRun) != %d'%pins['engine']['bytes']),(r'len\(run\) != \d+','len(run) != %d'%pins['engine']['bytes'])):
  driver,n=re.subn(pat,repl,driver);assert n==1
 assert (stage/'tools/Go.txt').read_text()==driver and json.loads((stage/'build-pins.json').read_text())==pins
 phase='built';runtime=pins['engine']['bytes']
print(json.dumps({'phase':phase,'domain':D,'printStreamBytes':len(image),'printStreamSHA256':IMAGE_SHA,'rejectsBarePrintDescriptor':True,'bootstrapRoot':record['bootstrapRoot'],'layoutUncheckedRegions':10,'runtimeBytes':runtime,'runtimeCap':393216},indent=2))
