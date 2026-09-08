# This Makefile is meant to be used by people that do not usually work
# with Go source code. If you know what GOPATH is then you probably
# don't need to bother with make.

.PHONY: geth evm all test lint fmt clean devtools help

GOBIN = ./build/bin
GO ?= latest
GORUN = go run

#? geth: Build geth.
geth:
	$(GORUN) build/ci.go install ./cmd/geth
	@echo "Done building."
	@echo "Run \"$(GOBIN)/geth\" to launch geth."

#? evm: Build evm.
evm:
	$(GORUN) build/ci.go install ./cmd/evm
	@echo "Done building."
	@echo "Run \"$(GOBIN)/evm\" to launch evm."

#? all: Build all packages and executables.
all:
	$(GORUN) build/ci.go install

#? test: Run the tests.
test: all
	$(GORUN) build/ci.go test

#? lint: Run certain pre-selected linters.
lint: ## Run linters.
	$(GORUN) build/ci.go lint

#? fmt: Ensure consistent code formatting.
fmt:
	gofmt -s -w $(shell find . -name "*.go")

#? clean: Clean go cache, built executables, and the auto generated folder.
clean:
	go clean -cache
	rm -fr build/_workspace/pkg/ $(GOBIN)/*

# The devtools target installs tools required for 'go generate'.
# You need to put $GOBIN (or $GOPATH/bin) in your PATH to use 'go generate'.

#? devtools: Install recommended developer tools.
devtools:
	env GOBIN= go install golang.org/x/tools/cmd/stringer@latest
	env GOBIN= go install github.com/fjl/gencodec@latest
	env GOBIN= go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
	env GOBIN= go install ./cmd/abigen
	@type "solc" 2> /dev/null || echo 'Please install solc'
	@type "protoc" 2> /dev/null || echo 'Please install protoc'

#? help: Get more info on make commands.
help: Makefile
	@echo ''
	@echo 'Usage:'
	@echo '  make [target]'
	@echo ''
	@echo 'Targets:'
	@sed -n 's/^#?//p' $< | column -t -s ':' |  sort | sed -e 's/^/ /'

# Java-in-EVM staged gates. The java-aot-* targets preserve the M0 baseline.
.PHONY: java-build java-demo java-test java-runtime-build java-runtime-check java-aot-demo java-aot-test java-harness-test java-diff-m1 java-smoke java-fast java-full
JAVA_DIFF_SEED ?= 56

java-build:
	go build -o build/bin/jvmevm ./cmd/jvmevm

java-demo: java-build
	mkdir -p build/java-evm-interpreter
	javac --release 8 -d build/java-evm-interpreter examples/java/Add.java jvmevm/testdata/differential/Loops.java jvmevm/testdata/differential/M4aArrays.java jvmevm/testdata/differential/bundle/basic/BasicRoot.java jvmevm/testdata/differential/bundle/basic/BasicHelper.java
	build/bin/jvmevm -class build/java-evm-interpreter/Add.class -method add -args 20,22 -gas 2000000
	# Typed-slot checks raised measured sum(100) execution to ~2.23M gas; no oracle case budgets changed.
	build/bin/jvmevm -class build/java-evm-interpreter/Loops.class -method sum -args 100 -gas 3000000
	build/bin/jvmevm -class build/java-evm-interpreter/Loops.class -method fibonacci -args 20 -gas 2000000
	build/bin/jvmevm -class build/java-evm-interpreter/bundle/basic/BasicHelper.class -class build/java-evm-interpreter/bundle/basic/BasicRoot.class -entry-class bundle/basic/BasicRoot -method threeArguments -args 1,2,3 -gas 5000000
	build/bin/jvmevm -class build/java-evm-interpreter/M4aArrays.class -method fillSum -args 10,3 -gas 10000000

java-test: java-runtime-check java-build
	go test -count=1 ./jvmevm ./cmd/jvmevm
	PYTHONDONTWRITEBYTECODE=1 JAVA_DIFF_REAL_EVM_BIN="$(CURDIR)/build/bin/jvmevm" python3 -m unittest discover -s tools -p 'test_java_diff.py'
	PYTHONDONTWRITEBYTECODE=1 python3 tools/java_diff.py --stage all --tier full --seed $(JAVA_DIFF_SEED) --artifacts build/java-diff-full

java-harness-test: java-build
	PYTHONDONTWRITEBYTECODE=1 JAVA_DIFF_REAL_EVM_BIN="$(CURDIR)/build/bin/jvmevm" python3 -m unittest discover -s tools -p 'test_java_diff.py'

java-diff-m1: java-build
	PYTHONDONTWRITEBYTECODE=1 python3 tools/java_diff.py --stage m1 --tier full --artifacts build/java-diff-m1

java-smoke: java-build
	PYTHONDONTWRITEBYTECODE=1 python3 tools/java_diff.py --stage all --tier smoke --seed $(JAVA_DIFF_SEED) --artifacts build/java-diff-smoke

java-fast: java-build
	PYTHONDONTWRITEBYTECODE=1 python3 tools/java_diff.py --stage all --tier fast --seed $(JAVA_DIFF_SEED) --artifacts build/java-diff-fast

java-full: java-build
	PYTHONDONTWRITEBYTECODE=1 python3 tools/java_diff.py --stage all --tier full --seed $(JAVA_DIFF_SEED) --artifacts build/java-diff-full

java-runtime-build:
	cd jvmevm/runtime && npm ci --ignore-scripts && npm run build

java-runtime-check:
	cd jvmevm/runtime && npm ci --ignore-scripts && npm run check

java-aot-demo:
	mkdir -p build/java-evm
	javac --release 8 -d build/java-evm examples/java/Add.java
	go run ./cmd/javaevm -class build/java-evm/Add.class -method add -args 20,22 -gas 100000

java-aot-test:
	go test -count=1 ./javaevm ./cmd/javaevm
	go build -o build/bin/javaevm ./cmd/javaevm

# Separate stock-EVM architecture slice, not the full interpreter's case corpus.
.PHONY: java-stock-build java-stock-check java-stock-test java-stock-demo

java-stock-build:
	cd jvmevm/stock/runtime && npm ci --ignore-scripts && npm run build

java-stock-check:
	cd jvmevm/stock/runtime && npm ci --ignore-scripts && npm run check

java-stock-test: java-stock-check
	go test -count=1 -timeout=10m ./jvmevm/stock

java-stock-demo: java-stock-check
	go test -count=1 -v -run '^TestStockHarnessSignedCanonicalAndDeterministicReplay$$' ./jvmevm/stock

# Versioned S1 actual legacy workloads; S0 and monolith targets remain separate.
.PHONY: java-stock-s1-build java-stock-s1-check java-stock-s1-test java-stock-s1-demo
java-stock-s1-build:
	cd jvmevm/stock/s1/runtime && npm ci --ignore-scripts && npm run build
java-stock-s1-check:
	cd jvmevm/stock/s1/runtime && npm ci --ignore-scripts && npm run check
java-stock-s1-test: java-stock-s1-check
	go test -count=1 -timeout=15m ./jvmevm/stock/s1
java-stock-s1-demo: java-stock-s1-check
	go test -count=1 -v -run '^TestStockS1HarnessSignedAll82ReuseBudgetsPrefixesAndDirectReplay$$' ./jvmevm/stock/s1
