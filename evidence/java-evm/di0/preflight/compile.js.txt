const fs = require("fs");
const solc = require("solc");
const source = fs.readFileSync("DI0Inflate.sol", "utf8");
const input = {
  language: "Solidity",
  sources: {"DI0Inflate.sol": {content: source}},
  settings: {
    optimizer: {enabled: true, runs: 200},
    viaIR: true,
    evmVersion: "cancun",
    metadata: {appendCBOR: false, bytecodeHash: "none"},
    outputSelection: {"*": {"*": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object"]}}
  }
};
const output = JSON.parse(solc.compile(JSON.stringify(input)));
for (const problem of output.errors || []) console.error(problem.formattedMessage);
if ((output.errors || []).some(problem => problem.severity === "error")) process.exit(1);
const c = output.contracts["DI0Inflate.sol"].DI0Inflate;
fs.writeFileSync("DI0Inflate.json", JSON.stringify({
  abi: c.abi,
  bytecode: c.evm.bytecode.object,
  runtime: c.evm.deployedBytecode.object
}, null, 2) + "\n");
console.log("solc=" + solc.version());
console.log("init_bytes=" + c.evm.bytecode.object.length / 2);
console.log("runtime_bytes=" + c.evm.deployedBytecode.object.length / 2);
