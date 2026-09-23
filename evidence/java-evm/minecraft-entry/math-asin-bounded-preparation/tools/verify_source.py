#!/usr/bin/env python3
"""Verify the exact Math-image + global-binding-20 semantic delta and root."""
from pathlib import Path
import hashlib, json, os, re, subprocess, tempfile
here=Path(__file__).resolve().parent; stage=here.parent; root=here.parents[4]
previous=stage.parent/'math-sin-bounded-preparation'
baseline_path=previous/'engine/MCEntryInterpreter.sol'; source_path=stage/'engine/MCEntryInterpreter.sol'
source=source_path.read_text(); baseline=baseline_path.read_text()
pins=json.loads((stage/'baseline-pins.json').read_text())
assert hashlib.sha256(baseline.encode()).hexdigest()==pins['baselineEngineSourceSHA256']

def block(text,start):
 at=text.index(start); end=text.find('\n    function ',at+1)
 return text[at:end if end>=0 else len(text)]
def image(text,name):
 values=re.findall(r'hex"([0-9a-f]+)"',block(text,'    function '+name+'('))
 assert len(values)==1,(name,len(values)); return bytes.fromhex(values[0])
def pascal_constant(name):
 overrides={'ENUMSET':'EnumSet','ITERABLE':'Iterable','MATH':'Math','RANDOM':'Random','THREAD':'Thread','THREAD_LOCAL':'ThreadLocal','STACK_TRACE_ELEMENT':'StackTraceElement','PRINT_STREAM':'PrintStream','SECURITY_MANAGER':'SecurityManager'}
 tail=name.removeprefix('DBOOT_'); return '_bootstrap'+overrides.get(tail,''.join(part.title() for part in tail.split('_')))
# Recompile exactly the modified Java 8 bootstrap leaf; source image is authoritative.
javac=Path('/usr/lib/jvm/java-8-openjdk/bin/javac'); assert javac.is_file()
with tempfile.TemporaryDirectory(prefix='java-diff-mc-math-asin-source-',dir=root/'build') as tmp:
 subprocess.run([javac,'-source','8','-target','8','-g:none','-d',tmp,stage/'bootstrap/java/lang/Math.java'],cwd=root,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 generated=(Path(tmp)/'java/lang/Math.class').read_bytes()
math_hex=stage/'bootstrap/java/lang/Math.class.hex'; math_sha=stage/'bootstrap/java/lang/Math.sha256'
assert math_hex.read_text().strip()==generated.hex()
assert math_sha.read_text().strip()==hashlib.sha256(generated).hexdigest()
assert image(source,'_bootstrapMath')==generated
assert len(generated)>pins['baselineMathBytes'] and hashlib.sha256(generated).hexdigest()!=pins['baselineMathSHA256']
# All image function names and all 96 non-Math bytes are inherited unchanged.
base_functions=set(re.findall(r'    function (_bootstrap\w+)\(',baseline)); functions=set(re.findall(r'    function (_bootstrap\w+)\(',source))
assert base_functions==functions
assert block(source,'    function _bootstrapRoot()')==block(baseline,'    function _bootstrapRoot()')
changed=[]
for fn in sorted(base_functions):
 if fn=='_bootstrapRoot': continue
 if image(source,fn)!=image(baseline,fn): changed.append(fn)
assert changed==['_bootstrapMath'],changed
# Derive the full ordered root from the root expression and exact embedded images.
root_block=block(source,'    function _bootstrapRoot()')
assignments={int(i):rhs.strip() for i,rhs in re.findall(r'h\[(\d+)\]\s*=\s*([^;]+);',root_block)}
assert set(assignments)==set(range(97))
leaves=[]
for index in range(97):
 rhs=assignments[index]; call=re.fullmatch(r'keccak256\((_bootstrap\w+)\(\)\)',rhs); const=re.fullmatch(r'(DBOOT_[A-Z_]+)',rhs)
 name=call.group(1) if call else pascal_constant(const.group(1))
 assert (name=='_bootstrapMath') == (index==89),(index,name)
 leaf=image(source,name)
 if const:
  declaration=re.search(r'bytes32 private constant '+const.group(1)+r'\s*=\s*([^;]+);',source); assert declaration
  value=declaration.group(1).strip()
  if value.startswith('keccak256(hex"'): assert bytes.fromhex(value[len('keccak256(hex"'):-2])==leaf
 leaves.append(leaf)
node=r'''const fs=require("fs"),{keccak256}=require("js-sha3");const x=JSON.parse(fs.readFileSync(0,"utf8"));const k=b=>keccak256(Buffer.from(b,"hex"));const word=n=>Buffer.from(BigInt(n).toString(16).padStart(64,"0"),"hex");const d=keccak256(x.domain);const hs=x.images.map(k);const enc=Buffer.concat([Buffer.from(d,"hex"),word(64),word(hs.length),...hs.map(h=>Buffer.from(h,"hex"))]);process.stdout.write(JSON.stringify({domain:d,hashes:hs,root:keccak256(enc)}));'''
env={**os.environ,'NODE_PATH':str(root/'jvmevm/runtime/node_modules')}
commit=json.loads(subprocess.run(['node','-e',node],input=json.dumps({'domain':'JVMEVM:MC-RANDOM-CLASS-P2:BOOTSTRAP:1','images':[x.hex() for x in leaves]}),text=True,cwd=root,env=env,capture_output=True,check=True).stdout)
# Normalize the exact native-20 changes back to the sine baseline.
normalized=source
for old,new,label in [
 ('    error MathAsinProfileError(uint256 code, uint256 pc);\n','', 'error'),
 ('            // Binding18 is deterministic sqrt, binding19 bounded integer sin,\n            // and binding20 the measured bounded integer inverse-sine surface.\n            // Raw Math replacement is refused during preparation.\n','            // Binding18 preserves the measured deterministic sqrt surface;\n            // binding19 is only the measured signed-zero Math.sin leaf. Raw Math\n            // replacement is refused during preparation.\n','owner comment'),
 ('            if (_equalsLiteral(c.data, nameOffset, nameLength, bytes("asin"))\n                && _equalsLiteral(c.data, descriptorOffset, descriptorLength, bytes("(D)D"))) {\n                return 20;\n            }\n','', 'mapping'),
 (' && binding != 20', '', 'native whitelist'),
 (' || binding == 20', '', 'native descriptor'),
]:
 if normalized.count(old)!=1: raise AssertionError((label,normalized.count(old)))
 normalized=normalized.replace(old,new,1)
new_dispatch='''                    if (nativeBinding == 20) {
                        // Binding20 computes only from the authenticated guest's
                        // binary64 bits using bounded EVM integer arithmetic.
                        _requireKind(f.stack[base], KIND_DOUBLE, opPC);
                        uint64 raw = uint64(_payload(f.stack[base]));
                        f.stack[base] = _packDouble(_mathAsinBits(raw, opPC));
                        f.sp = base + 1;
                        continue;
                    }
'''
assert normalized.count(new_dispatch)==1
normalized=normalized.replace(new_dispatch,'',1)
start='    /// @dev Bounded Q120 inverse sine over the exact guest binary64 encoding.\n'
end='    /// @dev Signed nearest-even integer division; callers prove |numerator| < 2^255.\n'
a=normalized.index(start); b=normalized.index(end,a); kernel=normalized[a:b]
normalized=normalized[:a]+normalized[b:]
# The bootstrap image was separately recompiled above; restore its old literal in this source-delta comparison.
math_start='    function _bootstrapMath() private pure returns (bytes memory) {'
old_math=block(baseline,math_start)
new_math=block(normalized,math_start)
assert normalized.count(new_math)==1
normalized=normalized.replace(new_math,old_math,1)
assert normalized==baseline, 'unreviewed engine source changes beyond Math.asin native20'
assert 'Math.asin(' not in kernel and 'Math.sqrt(' not in kernel and 'blockhash(' not in kernel
for phrase in ('for (uint256 n = 1; n <= 128; ++n)','for (uint256 i; i < 120; ++i)','0x3ff0000000000000','0x3e40000000000000','2087946453251888179413438228831778874','MathAsinProfileError(1, pc)'):
 assert phrase in kernel,phrase
assert 'return 20;' in block(source,'    function _nativeBinding(')
assert 'binding != 20' in block(source,'    function _loadNativeCallee(')
report={'result':'PASS','basis':'math-sin-bounded-preparation','baselineEngineSourceSHA256':hashlib.sha256(baseline.encode()).hexdigest(),'candidateEngineSourceSHA256':hashlib.sha256(source.encode()).hexdigest(),'onlySemanticDelta':['global native binding20 exact bounded Q120 integer Math.asin(D)D','bootstrap Math image89 adds only exact native asin(D)D'],'bootstrapCount':97,'changedBootstrapIndices':[89],'changedBootstrapImages':['Math'],'mathImageBytes':len(generated),'mathImageSHA256':hashlib.sha256(generated).hexdigest(),'mathImageKeccak256':commit['hashes'][89],'previousMathImageSHA256':pins['baselineMathSHA256'],'previousMathImageBytes':pins['baselineMathBytes'],'bootstrapRoot':commit['root'],'previousSourceDerivedRoot':pins['bootstrapRoot'],'orderedRoot':commit['root'],'orderedLeafKeccak256':commit['hashes'],'globalNativeBindings':20,'stringLocalBinding':12,'rawLimits':[71,471911],'diagnosticClassBound':168,'kernel':{'qBits':120,'piOverTwoQ':'2087946453251888179413438228831778874','seriesLastN':128,'tailBound':'<2^-258','inputMagnitudeMaxRaw':'3ff0000000000000','smallIdentityMaxRaw':'3e40000000000000','sqrtRounds':120,'externalMath':False,'lookupTable':False,'all96OtherBootstrapImagesByteIdentical':True,'intermediateProof':'all series products <2^240; sqrt radicand <2^238; sums <2^121; each <2^255'}}
historical_p1=json.loads((previous/'baseline-pins.json').read_text())['bootstrapRoot']
(stage/'root-commitment.json').write_text(json.dumps({'basis':'math-sin-bounded-preparation','bootstrapCount':97,'priorSourceDerivedRoot':pins['bootstrapRoot'],'priorHistoricalP1PinRoot':historical_p1,'historicalP1PinMatchesSourceDerivedRoot':historical_p1==pins['bootstrapRoot'],'changedIndices':[89],'orderedLeafKeccak256':commit['hashes'],'bootstrapRoot':commit['root']},indent=2)+'\n')
(stage/'results/source-invariants.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
