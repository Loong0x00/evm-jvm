#!/usr/bin/env python3
"""Replace only Pattern/Matcher image slots in a disposable engine source."""
import argparse, pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
D = HERE.parent
parser = argparse.ArgumentParser()
parser.add_argument('--class-dir', type=pathlib.Path, default=D / 'results/compiled')
parser.add_argument('--engine', type=pathlib.Path, default=D / 'engine/MCEntryInterpreter.sol')
parser.add_argument('--base', type=pathlib.Path)
parser.add_argument('--repo-root', type=pathlib.Path)
args = parser.parse_args()
ROOT = args.repo_root.resolve() if args.repo_root else next(p for p in D.parents if (p / '.git').exists())
BASE = ROOT / 'evidence/java-evm/minecraft-entry/regex-anchor-plus-source-base-p41'
if args.base is None:
    args.base = BASE / 'engine/MCEntryInterpreter.sol'
source = args.engine.read_text()
for name in ('Pattern', 'Matcher'):
    image = (args.class_dir / f'java/util/regex/{name}.class').read_bytes().hex()
    pattern = rf'(function _bootstrap{name}\(\) private pure returns \(bytes memory\) \{{ return hex")[0-9a-f]+("; \}})'
    source, count = re.subn(pattern, lambda m: m.group(1) + image + m.group(2), source)
    if count != 1:
        raise SystemExit(f'{name} image replacement count {count}')
base = args.base.read_text()
def strip_images(text):
    for name in ('Pattern', 'Matcher'):
        pattern = rf'(function _bootstrap{name}\(\) private pure returns \(bytes memory\) \{{ return hex")[0-9a-f]+("; \}})'
        text, n = re.subn(pattern, r'\1IMAGE\2', text)
        if n != 1:
            raise SystemExit(f'cannot audit {name}: {n}')
    return text
if strip_images(source) != strip_images(base):
    raise SystemExit('engine source changed outside Pattern/Matcher image slots')
args.engine.write_text(source)
