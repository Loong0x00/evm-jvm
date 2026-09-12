#!/bin/sh
# Reproduce after-repair focused validation from the repository root.
set -eu

timeout 30s go test ./jvmevm/localcontinuation/cb0 \
  -run 'TestCB0(ArtifactValidation|HeadValidationInitialWorld|HeadValidationRejectsCopiedStateShape)' -count=1
timeout 120s go test ./jvmevm/localcontinuation/cb0 \
  -run TestCB0HeadValidationBoundaryGas -count=1
timeout 30s go vet ./jvmevm/localcontinuation/cb0
