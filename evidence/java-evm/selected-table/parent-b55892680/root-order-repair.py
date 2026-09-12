#!/usr/bin/env python3
"""COPY-only proposed repair: preserve accepted argument/local-check precedence.
Apply only AFTER retaining the original-candidate counterexample. No accepted edit.
"""
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()
old='        _predecode(p.classes[p.rootClass], rootSelection);\n        _putSelection(p.selected, p.rootClass, p.rootMethod, rootSelection);\n        Selected memory rs = _selectedAt(p.selected, p.rootClass, p.rootMethod);\n        if (args.length != rs.argumentCount) revert MethodError(9);\n        if (rs.maxLocals < rs.argumentWords) revert MethodError(10);'
new='        if (args.length != rootSelection.argumentCount) revert MethodError(9);\n        if (rootSelection.maxLocals < rootSelection.argumentWords) revert MethodError(10);\n        _predecode(p.classes[p.rootClass], rootSelection);\n        _putSelection(p.selected, p.rootClass, p.rootMethod, rootSelection);'
assert s.count(old)==1
p.write_text(s.replace(old,new))
