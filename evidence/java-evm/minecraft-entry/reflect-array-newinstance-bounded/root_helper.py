"""Recompute the append-only 117-leaf commitment from this candidate's Solidity source."""
import importlib.util
import json
import os
from pathlib import Path

BASE = Path(__file__).parents[1] / "reflect-array-source-base-p52" / "root_helper.py"
spec = importlib.util.spec_from_file_location("p52_root", BASE)
p52 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p52)


def root_record(source, domain, root_dir, environment):
    result = p52.root_record(source, domain, root_dir, environment)
    assert len(result["leaves"]) == 117, len(result["leaves"])
    return result


if __name__ == "__main__":
    source_path = Path(__file__).parent / "engine" / "MCEntryInterpreter.sol"
    source = source_path.read_text()
    import re
    domain = re.search(r'bytes32 private constant DBOOT = keccak256\("([^"]+)"\);', source).group(1)
    result = root_record(source, domain, str(Path(__file__).parent), os.environ.copy())
    base = json.loads((Path(__file__).parents[1] / "reflect-array-source-base-p52" / "pins.json").read_text())
    assert result["leaves"][:116] == base["orderedBootstrapLeaves"]
    print(json.dumps({"bootstrapCount": 117, "bootstrapRoot": result["root"],
                      "oldPrefixExact": True, "newLeaf116": result["leaves"][116],
                      "orderedBootstrapLeaves": result["leaves"]}, indent=2))
