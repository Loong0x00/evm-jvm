#!/bin/bash
set -euo pipefail
w=$1
"$w/driver" setup-chain "$w/q7" "$w/coordinator.json" "$w/fixtures/shared-two.zip" 7 7
"$w/driver" finish "$w/q7" "$w/coordinator.json"
"$w/driver" verify "$w/q7" "$w/coordinator.json"
"$w/driver" setup-chain "$w/q1" "$w/coordinator.json" "$w/fixtures/shared-two.zip" 1 7
"$w/driver" negatives "$w/q1" "$w/coordinator.json"
"$w/driver" resume-one "$w/q1" "$w/coordinator.json" publication-probe
"$w/driver" finish "$w/q1" "$w/coordinator.json"
"$w/driver" verify "$w/q1" "$w/coordinator.json"
"$w/driver" setup-chain "$w/input9" "$w/coordinator.json" "$w/fixtures/shared-two.zip" 4096 9
"$w/driver" verify "$w/input9" "$w/coordinator.json"
"$w/driver" setup-memory "$w/memory1" "$w/coordinator.json" "$w/fixtures/shared-two.zip" 1 7
"$w/driver" setup-memory "$w/memory7" "$w/coordinator.json" "$w/fixtures/shared-two.zip" 7 7
"$w/driver" boundary "$w/boundary" "$w/coordinator.json" "$w/fixtures/boundary-seven.zip"
