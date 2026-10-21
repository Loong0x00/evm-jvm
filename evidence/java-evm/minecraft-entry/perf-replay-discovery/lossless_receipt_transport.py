#!/usr/bin/env python3
"""Generate a metadata-only lossless failure-receipt transport source copy.

No EVM/JVM instructions, call budget, authorization or state/publication logic is
changed. Existing frozen drivers/evidence must not be overwritten.
"""
from pathlib import Path
import argparse,hashlib,json

OLD = 'var receipt map[string]interface{}\n\tmust(json.Unmarshal(encoded, &receipt))'
NEW = ('var receipt map[string]interface{}\n'
       '\tdecoder := json.NewDecoder(bytes.NewReader(encoded))\n'
       '\tdecoder.UseNumber()\n'
       '\tmust(decoder.Decode(&receipt))')

def patch_source(source: str) -> str:
    if source.count(OLD) != 1 or 'func annotateDurableHeadAtomicity(' not in source:
        raise ValueError('expected one known diagnostic receipt-annotation decode')
    result = source.replace(OLD, NEW)
    if result.count(NEW) != 1 or result.replace(NEW, OLD) != source:
        raise ValueError('source normalization failed')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-go',type=Path,required=True)
    p.add_argument('--output-go',type=Path,required=True)
    p.add_argument('--audit',type=Path,required=True)
    a=p.parse_args()
    if a.input_go.resolve()==a.output_go.resolve() or a.output_go.exists() or a.audit.exists():
        raise ValueError('fresh, distinct output source/audit paths required')
    data=a.input_go.read_bytes();result=patch_source(data.decode()).encode()
    a.output_go.parent.mkdir(parents=True,exist_ok=True);a.output_go.write_bytes(result)
    a.audit.parent.mkdir(parents=True,exist_ok=True)
    a.audit.write_text(json.dumps({'inputSHA256':hashlib.sha256(data).hexdigest(),
       'outputSHA256':hashlib.sha256(result).hexdigest(),'normalizationExact':True,
       'change':'json.Decoder.UseNumber in diagnostic failure-receipt annotation only',
       'guestEvmGasAndStateLogicUnchanged':True,'noExistingEvidenceRewritten':True},indent=2)+'\n')

if __name__=='__main__':main()
