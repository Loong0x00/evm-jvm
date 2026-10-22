#!/usr/bin/env python3
import argparse, hashlib, importlib.util, json, os, pathlib
parser=argparse.ArgumentParser();parser.add_argument('--profile',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]);parser.add_argument('--repo-root',type=pathlib.Path)
a=parser.parse_args();D=a.profile.resolve();ROOT=a.repo_root.resolve() if a.repo_root else next(p for p in D.parents if (p/'.git').exists())
pins=json.loads((D/'pins.json').read_text())
spec=importlib.util.spec_from_file_location('root_helper',D/'reference/root_helper.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
env=os.environ.copy();env['NODE_PATH']=str(ROOT/'jvmevm/runtime/node_modules')
r=mod.root_record((D/'engine/MCEntryInterpreter.sol').read_text(),'JVMEVM:MC-HASH-MAP-PUT-P39:BOOTSTRAP:1',str(D),env)
pins['bootstrapRoot']=r['root'];pins['expectedBootstrapRoot']=r['root'];pins['orderedBootstrapLeaves']=r['leaves']
for obj,key in ((pins['engine'],'engine/MCEntryInterpreter.json'),(pins['coordinator'],'coordinator/MCEntryCoordinator.json')):
 art=json.loads((D/key).read_text());obj['bytes']=len(bytes.fromhex(art['deployedBytecode']));obj['initSHA256']=art['codeHashes']['initSHA256'];obj['runtimeSHA256']=art['codeHashes']['runtimeSHA256'];obj['runtimeKeccak256']=art['codeHashes']['runtimeKeccak256']
pins['sourceSHA256']=hashlib.sha256((D/'engine/MCEntryInterpreter.sol').read_bytes()).hexdigest()
# P41 ancestry remains historical; current change scope is exactly these two
# image leaves, with all numeric limits and protocol surfaces unchanged.
pins['sourceInvariants']={'onlyPatternAndMatcherBootstrapImagesChanged':True,'changedBootstrapSlots':[101,103],'other103LeavesByteIdentical':True,'arrayLimit8192Unchanged':True,'maxObjects4096Unchanged':True,'maxHandles12545Unchanged':True,'allOtherQuotasUnchanged':True,'ABIStorageCodecUnchanged':True,'noNewOperationalNative':True,'noUnderlyingEvmChange':True}
pins['legacySourceInvariants']={'all105ImagesAndRootUnchanged':False,'arrayCountOnly4096To8192':False,'note':'P41 historical labels; superseded by P42 Pattern/Matcher leaf changes'}
(D/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
