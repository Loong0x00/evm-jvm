#!/usr/bin/env python3
"""TEST-ONLY integer Q120 model against the pinned generated OpenJDK 8 data."""
from pathlib import Path
import hashlib, json, struct

here=Path(__file__).resolve().parent; root=here.parents[4]
oracle=root/'evidence/java-evm/minecraft-entry/math-asin-independent-oracle'
samples=oracle/'results/samples.tsv'
assert hashlib.sha256(samples.read_bytes()).hexdigest()=='827279a72a83c80392da8dccd38bc94d3d1ff5f4e4cec4199cf228f5d60ca0e6'
Q=1<<120; PI_OVER_TWO_Q=int('1921fb54442d18469898cc51701b83a',16)
ONE=0x3ff0000000000000; HALF=0x3fe0000000000000; TINY=0x3e40000000000000; MASK=(1<<64)-1
max_bits={}
def observe(label,n):
 b=abs(n).bit_length(); max_bits[label]=max(max_bits.get(label,0),b)
 assert abs(n)<(1<<255),(label,b)
def even(n,d,label):
 assert n>=0 and d>0
 observe(label+'.numerator',n); observe(label+'.denominator',d)
 q,r=divmod(n,d); observe(label+'.twice-rem',2*r)
 if 2*r>d or (2*r==d and q&1): q+=1
 observe(label+'.quotient',q); return q
def input_q(mag):
 e=(mag>>52)&0x7ff; sig=(1<<52)|(mag&((1<<52)-1)); value=sig<<(e-955)
 observe('input-q',value); return value
def series(x):
 term=x; total=x; observe('series-term',term); observe('series-sum',total)
 for n in range(1,129):
  a=even(term*x,Q,'series-mul1'); b=even(a*x,Q,'series-mul2')
  odd=2*n-1; term=even(b*odd*odd,2*n*(2*n+1),'series-ratio')
  total+=term; observe('series-term',term); observe('series-sum',total)
 return total
def qdouble(value):
 assert value>=0
 if value==0:return 0
 top=value.bit_length()-1; shift=top-52
 if shift>0: sig=even(value,1<<shift,'binary64')
 else: sig=value<<(-shift); observe('binary64',sig)
 if sig==(1<<53):sig>>=1;top+=1
 return ((top+903)<<52)|(sig&((1<<52)-1))
def asin(raw):
 mag=raw&0x7fffffffffffffff; e=(mag>>52)&0x7ff
 if e==0x7ff or mag>ONE: raise ValueError
 if mag<=TINY:return raw
 x=input_q(mag)
 if mag<=HALF: out=series(x)
 elif mag==ONE:out=PI_OVER_TWO_Q
 else:
  delta=Q-x; y=even(delta,2,'half-delta'); rad=y*Q; observe('sqrt-radicand',rad)
  root=__import__('math').isqrt(rad); observe('sqrt-root',root)
  assert root*root<=rad<(root+1)*(root+1)
  out=PI_OVER_TWO_Q-2*series(root)
  observe('asin-result',out)
 result=qdouble(out)
 return result|(raw&(1<<63))
def ordered(x):return (~x&MASK) if x>>63 else x|(1<<63)
def floatbits(bits):return struct.unpack('>I',struct.pack('>f',struct.unpack('>d',struct.pack('>Q',bits))[0]))[0]
rows=[]; refused=[]
with samples.open(encoding='ascii',newline='') as f:
 assert f.readline().startswith('# generated OpenJDK 8 oracle;')
 assert f.readline().rstrip('\n')=='categories\tinput_bits\tpolicy\tasin_bits\tfloat_bits'
 for line in f:
  cats,raw,policy,out,fb=line.rstrip('\n').split('\t'); row=(cats,int(raw,16),policy,out,fb)
  (rows if policy=='SUPPORTED' else refused).append(row)
assert len(rows)==17066 and len(refused)==11
mismatches=[]; float_mismatches=[]; worst=0; prior=None; monotonic_violations=0
for cats,raw,policy,out,fb in rows:
 got=asin(raw); expected=int(out,16); distance=abs(ordered(got)-ordered(expected));worst=max(worst,distance)
 if distance:mismatches.append((raw,got,expected,distance))
 cast=floatbits(got)
 if cast!=int(fb,16):float_mismatches.append((raw,cast,int(fb,16)))
 key=ordered(raw); value=ordered(got)
 if prior and key>prior[0] and value<prior[1]:monotonic_violations+=1
 prior=(key,value)
assert worst<=1 and len(mismatches)==472 and not float_mismatches and not monotonic_violations
# Explicit refusals are only classified from raw inputs; no Math.asin output is generated.
assert all((((r>>52)&0x7ff)==0x7ff or (r&0x7fffffffffffffff)>ONE) for _,r,_,_,_ in refused)
report={'purpose':'TEST-ONLY pure-integer Q120 model compared to generated OpenJDK 8 oracle; never guest execution input','oracleSamplesSHA256':hashlib.sha256(samples.read_bytes()).hexdigest(),'supportedRows':len(rows),'refusedControls':len(refused),'qBits':120,'piOverTwoQ':str(PI_OVER_TWO_Q),'seriesLastN':128,'tailBound':'<2^-258 for |x|<=1/2','maxBinary64ULPDistanceFromJava8':worst,'binary64BitMismatchCount':len(mismatches),'floatCastBitMismatchCount':len(float_mismatches),'sampledMonotonicityViolations':monotonic_violations,'maximumIntermediateBitLengths':dict(sorted(max_bits.items())),'strictSigned256Bound':'all observed intermediate magnitudes <2^255','algorithm':'exact raw-bit input conversion; tiny identity <=2^-27; 128-term nearest-even series; exact isqrt for high-domain transform; nearest-even Q120 binary64 packing','limitation':'Generated samples only; Java8 <=1 ULP is observed on these rows, not a global execution or original-program claim.'}
print(json.dumps(report,indent=2,sort_keys=True))
