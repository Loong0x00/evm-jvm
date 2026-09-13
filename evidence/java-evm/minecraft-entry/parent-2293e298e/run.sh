#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 NODE_PATH="$PWD/jvmevm/runtime/node_modules"
p=evidence/java-evm/minecraft-entry/parent-2293e298e
b=build/java-diff-mc-security-getter-parent-build3-2293e298e
python3 "$p/rebuild.py" "$b"
python3 - <<'PY'
from pathlib import Path
p=Path('evidence/java-evm/minecraft-entry/security-getter-preflight');out=Path('build/java-diff-mc-security-getter-parent-run-script.py')
s=(p/'run_generated.py').read_text().replace('start_new_session=True','').replace('group_rss_kib(p.pid)','group_rss_kib(os.getpgid(p.pid))').replace('os.killpg(p.pid, 9)','os.killpg(os.getpgid(p.pid), 9)')
s=s.replace('HERE = Path(__file__).resolve().parent',"HERE = Path('"+str(p.resolve())+"')").replace('ROOT = HERE.parents[3]',"ROOT = Path('"+str(Path.cwd().resolve())+"')")
assert 'start_new_session=True' not in s and "HERE = Path('/home/user/evm-jvm/geth/evidence/java-evm/minecraft-entry/security-getter-preflight')" in s
out.write_text(s)
PY
python3 build/java-diff-mc-security-getter-parent-run-script.py "$b" build/java-diff-mc-security-getter-parent-smoke3-2293e298e
python3 "$p/frontier.py" "$b" build/java-diff-mc-security-getter-parent-official21c-2293e298e /home/user/evm-jvm/mc-startup-inventory/build/java-diff-mc-startup-preflight/artifacts/minecraft_server.1.12.2.jar "$p/official21-bindings.json" 7
node "$p/verify_receipts.js" "$b" build/java-diff-mc-security-getter-parent-official21c-2293e298e 1 official
