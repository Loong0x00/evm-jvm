#!/usr/bin/env python3
# Static planning-only raw ZIP inventory. It never executes or imports the JAR.
import collections, hashlib, json, os, struct, sys
p=sys.argv[1]
b=open(p,'rb').read()
assert hashlib.sha256(b).hexdigest()=="fe1f9274e6dad9191bf6e6e8e36ee6ebc737f373603df0946aafcded0d53167e"
assert len(b)==30222121

def u16(o): return struct.unpack_from('<H',b,o)[0]
def u32(o): return struct.unpack_from('<I',b,o)[0]
# APPNOTE EOCD is in last 65557 bytes; accept only records ending exactly at EOF.
cands=[]
for o in range(max(0,len(b)-65557),len(b)-21):
    if b[o:o+4]==b'PK\x05\x06' and o+22+u16(o+20)==len(b): cands.append(o)
assert len(cands)==1,cands
e=cands[0]; comment=b[e+22:]
disk,cd_disk,n_disk,n_total,cd_size,cd_off=struct.unpack_from('<HHHHII',b,e+4)
entries=[]; o=cd_off
for i in range(n_total):
    assert b[o:o+4]==b'PK\x01\x02',(i,o,b[o:o+4])
    made,need,flags,method,mtime,mdate,crc,cs,us,nl,xl,cl,dstart,iattr,eattr,lo=struct.unpack_from('<HHHHHHIIIHHHHHII',b,o+4)
    name=b[o+46:o+46+nl]; extra=b[o+46+nl:o+46+nl+xl]; com=b[o+46+nl+xl:o+46+nl+xl+cl]
    # Extra records must frame exactly; gather IDs.
    ex=[]; q=0
    while q<len(extra):
        assert q+4<=len(extra),(i,'extra header')
        xid,xn=struct.unpack_from('<HH',extra,q); assert q+4+xn<=len(extra),(i,'extra body')
        ex.append((xid,xn));q+=4+xn
    assert q==len(extra)
    assert b[lo:lo+4]==b'PK\x03\x04',(i,lo,b[lo:lo+4])
    lneed,lflags,lmethod,lmtime,lmdate,lcrc,lcs,lus,lnl,lxl=struct.unpack_from('<HHHHHIIIHH',b,lo+4)
    lname=b[lo+30:lo+30+lnl]; lextra=b[lo+30+lnl:lo+30+lnl+lxl]
    data=lo+30+lnl+lxl; end=data+cs
    descriptor='none'; desc_len=0
    if flags & 8:
        # Determine descriptor from central sizes and bytes at compressed-data end.
        sig=(b[end:end+4]==b'PK\x07\x08'); z=end+(4 if sig else 0)
        if cs<=0xffffffff and us<=0xffffffff and z+12<=len(b) and struct.unpack_from('<III',b,z)==(crc,cs,us):
            desc_len=(4 if sig else 0)+12; descriptor=('sig-' if sig else 'nosig-')+'classic'
        elif z+20<=len(b) and struct.unpack_from('<IQQ',b,z)==(crc,cs,us):
            desc_len=(4 if sig else 0)+20; descriptor=('sig-' if sig else 'nosig-')+'zip64'
        else: descriptor='unrecognized'
    entries.append(dict(i=i,off=o,name=name,extra=extra,comment=com,made=made,need=need,flags=flags,method=method,crc=crc,cs=cs,us=us,dstart=dstart,lo=lo,nl=nl,xl=xl,cl=cl,ex=ex,lneed=lneed,lflags=lflags,lmethod=lmethod,lcrc=lcrc,lcs=lcs,lus=lus,lnl=lnl,lxl=lxl,lname=lname,data=data,end=end,descriptor=descriptor,desc_len=desc_len,record_end=end+desc_len))
    o += 46+nl+xl+cl
assert o==cd_off+cd_size,(o,cd_off+cd_size)
# Exact local-record non-overlap and relation to central directory.
bylo=sorted(entries,key=lambda x:x['lo'])
overlaps=[]
for a,z in zip(bylo,bylo[1:]):
    if a['record_end']>z['lo']: overlaps.append((a['i'],z['i'],a['record_end']-z['lo']))
# Duplicate names are full byte equality.
dups={k.hex():v for k,v in collections.defaultdict(list).items()}
nameinds=collections.defaultdict(list)
for x in entries:nameinds[x['name']].append(x['i'])
dups={k.hex():v for k,v in nameinds.items() if len(v)>1}
def _utf8(raw):
    try: raw.decode('utf-8','strict'); return True
    except UnicodeDecodeError: return False
# Strict properties relevant to candidate profile.
res={}
for target in [b'META-INF/log4j-provider.properties',b'log4j2.xml',b'net/minecraft/server/MinecraftServer.class',b'org/apache/logging/log4j/LogManager.class']:
    x=next((q for q in entries if q['name']==target),None)
    res[target.decode()] = None if x is None else {k:x[k] for k in ('i','lo','data','cs','us','method','flags','descriptor')}
out={
 'path':os.path.abspath(p),'size':len(b),'sha256':hashlib.sha256(b).hexdigest(),'sha1':hashlib.sha1(b).hexdigest(),
 'eocd':{'offset':e,'candidates':len(cands),'disk':disk,'cd_disk':cd_disk,'entries_disk':n_disk,'entries_total':n_total,'cd_offset':cd_off,'cd_size':cd_size,'comment_len':len(comment),'comment_sig_counts':{s.hex():comment.count(s) for s in [b'PK\x05\x06',b'PK\x01\x02',b'PK\x03\x04']}},
 'counts':{'entries':len(entries),'methods':collections.Counter(x['method'] for x in entries),'flags':collections.Counter(x['flags'] for x in entries),'descriptor_forms':collections.Counter(x['descriptor'] for x in entries),'versions_needed':collections.Counter(x['need'] for x in entries),'made_by':collections.Counter(x['made'] for x in entries)},
 'names':{'sum_len':sum(x['nl'] for x in entries),'max_len':max(x['nl'] for x in entries),'empty':sum(not x['name'] for x in entries),'invalid_utf8':sum(1 for x in entries if not _utf8(x['name'])),'directory_suffix':sum(x['name'].endswith(b'/') for x in entries),'absolute_slash':sum(x['name'].startswith(b'/') for x in entries),'backslash':sum(b'\\' in x['name'] for x in entries),'dotdot_component':sum(b'..' in x['name'].split(b'/') for x in entries),'duplicate_sets':len(dups),'duplicate_entries':sum(len(v) for v in dups.values()),'duplicates':dups},
 'extras':{'central_sum':sum(x['xl'] for x in entries),'central_max':max(x['xl'] for x in entries),'central_nonempty':sum(x['xl']>0 for x in entries),'local_sum':sum(x['lxl'] for x in entries),'local_max':max(x['lxl'] for x in entries),'local_nonempty':sum(x['lxl']>0 for x in entries),'ids':collections.Counter(hex(y[0]) for x in entries for y in x['ex'])},
 'comments':{'entry_sum':sum(x['cl'] for x in entries),'entry_max':max(x['cl'] for x in entries),'entry_nonempty':sum(x['cl']>0 for x in entries)},
 'features':{'zip64_sentinel_entries':sum(1 for x in entries if x['cs']==0xffffffff or x['us']==0xffffffff or x['lo']==0xffffffff or x['dstart']==0xffff),'zip64_extra_entries':sum(1 for x in entries if any(y[0]==1 for y in x['ex'])),'encrypted':sum(1 for x in entries if x['flags']&1),'strong_encryption':sum(1 for x in entries if x['flags']&0x40),'patched_data':sum(1 for x in entries if x['flags']&0x20),'multidisk_entry':sum(1 for x in entries if x['dstart']!=0),'data_descriptor':sum(1 for x in entries if x['flags']&8)},
 'consistency':{'local_name_mismatch':sum(x['name']!=x['lname'] for x in entries),'local_method_mismatch':sum(x['method']!=x['lmethod'] for x in entries),'local_flags_mismatch':sum(x['flags']!=x['lflags'] for x in entries),'local_sizes_crc_mismatch_without_descriptor':sum((not x['flags']&8) and (x['crc'],x['cs'],x['us'])!=(x['lcrc'],x['lcs'],x['lus']) for x in entries),'unrecognized_descriptor':sum(x['descriptor']=='unrecognized' for x in entries),'overlaps':overlaps,'first_local_offset':bylo[0]['lo'],'last_local_record_end':max(x['record_end'] for x in entries),'central_order_equals_local_order':[x['i'] for x in bylo]==list(range(len(entries)))},
 'resources':res
}
# JSON cannot serialize Counter with integer keys predictably; stringify recursively via dump default.
print(json.dumps(out,indent=2,sort_keys=True,default=lambda x:dict(x)))
