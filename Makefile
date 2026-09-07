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

# Java-in-EVM interpreter helpers. The java-aot-* targets preserve the M0 baseline.
.PHONY: java-demo java-test java-runtime-build java-runtime-check java-aot-demo java-aot-test

java-demo:
	mkdir -p build/java-evm-interpreter
	javac --release 8 -d build/java-evm-interpreter examples/java/Add.java
	go run ./cmd/jvmevm -class build/java-evm-interpreter/Add.class -method add -args 20,22 -gas 2000000

java-test: java-runtime-check
	go test -count=1 ./jvmevm ./cmd/jvmevm
	go build -o build/bin/jvmevm ./cmd/jvmevm

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
