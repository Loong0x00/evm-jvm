#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const solc = require('solc');
const expectedVersion = '0.8.30+commit.73712a01.Emscripten.clang';
if (solc.version() !== expectedVersion) throw new Error(`wrong solc: ${solc.version()}`);
const arg = process.argv[2];
const check = arg === '--check' || arg === '--check-over-cap';
const measureOverCap = arg === '--measure-over-cap' || arg === '--check-over-cap';
if (process.argv.length !== (arg ? 3 : 2) || (arg && !check && !measureOverCap)) {
  throw new Error('usage: node build.js [--check|--measure-over-cap|--check-over-cap]');
}
const dir = __dirname;
const sourceName = 'VFS0aInterpreter.sol';
const source = fs.readFileSync(path.join(dir, sourceName), 'utf8');
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
let bootstrapImagesLength = 0;
const pins = [
  {fn: '_bootstrapString', source: 'bootstrap/java/lang/String.java', sourceSHA256: '95542f5d4b869cc96ee395c322f8368a275fe3338ae60c7810afded6d4b81f2e', classHex: 'bootstrap/java/lang/String.class.hex', bytes: 984, classSHA256: '7999610c7686c7622667ee57fef88d6bf576e61595ec09310dc3905cd18aedad', reproduction: 'javac --release 8 -g:none'},
  {fn: '_bootstrapThrowable', source: 'bootstrap/java/lang/Throwable.java', sourceSHA256: 'f6578dc0cc5fb2372819e856d37745b652843571ffcab4c75171a4349c644fc4', classHex: 'bootstrap/java/lang/Throwable.class.hex', bytes: 516, classSHA256: '49b74f001ee43478dae744abc5413dcffd5dd5294856fdfbb92504f5ef0f0df1'},
  {fn: '_bootstrapException', source: 'bootstrap/java/lang/Exception.java', sourceSHA256: 'c442694d877ced78496bbb1565bed26de17bcaa7e991578002af807a0f20d016', classHex: 'bootstrap/java/lang/Exception.class.hex', bytes: 203, classSHA256: '25cb2ac6e090fc75f4ca3faa8b00586b6373a53d0ace3024fe36be272a19b34e'},
  {fn: '_bootstrapExceptionInInitializerError', source: 'bootstrap/java/lang/ExceptionInInitializerError.java', sourceSHA256: 'bda6877f6c8e3a1b91aa8f37c5453572e693bae3ccb613c0b4d671a509a299bf', classHex: 'bootstrap/java/lang/ExceptionInInitializerError.class.hex', bytes: 389, classSHA256: '21fe8c2605bbb61c248207ed1e9c1a42b194aba9661e6b930b2c605cde962609'},
  {fn: '_bootstrapIOException', source: 'bootstrap/java/io/IOException.java', sourceSHA256: '253a0242548de74f85e287cd9225db1213a331ecb8f14ff4e24194bc08acfff8', classHex: 'bootstrap/java/io/IOException.class.hex', bytes: 203, classSHA256: '61b742b86e9be1d4c3bc8c5d90156befc8ce38afc5d4425bd5751b77224d4d17'},
  {fn: '_bootstrapFileNotFoundException', source: 'bootstrap/java/io/FileNotFoundException.java', sourceSHA256: '5c1a2d81945ef9f058d98e7e9c0348228a4f116c86f109de5526af3aba5d9206', classHex: 'bootstrap/java/io/FileNotFoundException.class.hex', bytes: 213, classSHA256: 'd964d55dc660566a64eda14af9dacbfa51a93baa8d5b772e73a083d2d258f654'},
  {fn: '_bootstrapEOFException', source: 'bootstrap/java/io/EOFException.java', sourceSHA256: 'ab20cb1aa1b69d5cc525ee9fea4445fef6da74881a6c004bb299944b8cbb84c3', classHex: 'bootstrap/java/io/EOFException.class.hex', bytes: 204, classSHA256: '6cb3a2c8d9baa1403f9e5a11e7e46872bcc0da45099cbe315ec248f841a6fd0c'},
  {fn: '_bootstrapAutoCloseable', source: 'bootstrap/java/lang/AutoCloseable.java', sourceSHA256: '3520639a2c4c5e9c43b1cd6dc6ea269058d787d436be4dbeac38a1323fbe8d08', classHex: 'bootstrap/java/lang/AutoCloseable.class.hex', bytes: 145, classSHA256: 'cafa160ddd47f90df802399cbd3ea0f4a62dc0d382c77fde7917b8b84fa51ea8'},
  {fn: '_bootstrapCloseable', source: 'bootstrap/java/io/Closeable.java', sourceSHA256: 'c00f4d65711c584a549245e5e56bcefcdff748fab8c616602cdd249431128a28', classHex: 'bootstrap/java/io/Closeable.class.hex', bytes: 170, classSHA256: '79fae4d62aee6a6f46bd7483265bb3a19ba9fcc89c3f6dc8a14d5814a10ed86f'},
  {fn: '_bootstrapFlushable', source: 'bootstrap/java/io/Flushable.java', sourceSHA256: '38590df5c917ae27beb7e264449a6ce617950ef8a28e648cf15f0428798cbff1', classHex: 'bootstrap/java/io/Flushable.class.hex', bytes: 139, classSHA256: 'b5679864201f2fe3eb8e7fad6a7121790281ad1ca87391d928ca9c1bc9277513'},
  {fn: '_bootstrapFile', source: 'bootstrap/java/io/File.java', sourceSHA256: '8a7a73c9aa27481f585523b9e389aaae0018550fee33470f2cabbb880fc72378', classHex: 'bootstrap/java/io/File.class.hex', bytes: 1267, classSHA256: 'aee6861b45213674f41d257a87a0508b3b9ca1d900ec995234bd51d129b83bc4'},
  {fn: '_bootstrapInputStream', source: 'bootstrap/java/io/InputStream.java', sourceSHA256: '3468cf45fceaf0f720028330ae8ad41c895625235f37a655e3d8e55864fc2714', classHex: 'bootstrap/java/io/InputStream.class.hex', bytes: 595, classSHA256: '224fd0acae8f99ca75c2cba79902dca8408fe91fa839599a96377a31a687ba72'},
  {fn: '_bootstrapOutputStream', source: 'bootstrap/java/io/OutputStream.java', sourceSHA256: 'e9d18ab9aa2dafcbb2be033bf85a21e344346f16ccd9210f936cfc1808f8fbcb', classHex: 'bootstrap/java/io/OutputStream.class.hex', bytes: 601, classSHA256: '2698b53831772935d798d8739ffe77b786f343e30f7bc5d7b1d1ae5c8efeb4c2'},
  {fn: '_bootstrapFileInputStream', source: 'bootstrap/java/io/FileInputStream.java', sourceSHA256: 'dfe7fdd545d48c5fdacaa57985e3a5a839ebfe6ea929adc9338dbe3c7e34d78b', classHex: 'bootstrap/java/io/FileInputStream.class.hex', bytes: 1478, classSHA256: '68fd8bf1cdb48a5309b60a28ec9573dd68b5cc96318487b82f93cfce058e4545'},
  {fn: '_bootstrapFileOutputStream', source: 'bootstrap/java/io/FileOutputStream.java', sourceSHA256: '18d546ad0458c82df99aa2762171e76fff7ed6f287277a7b98123ea8e77e7768', classHex: 'bootstrap/java/io/FileOutputStream.class.hex', bytes: 1581, classSHA256: '4e5175528984798d6da3ef9c3cd58395e0f66788be9e11ed1a2a35fb2015f6a8'},
];
const imagePins = [
  ['Object','af9136af3be2c44ce120ac403beccb8b1cc963fc83dc1457e63f8b69dd497fe0'],
  ['Cloneable','07930c21cec8dfc8a031c04590af290511e2be6dbae7ad1282a2cfa00a06c457'],
  ['Serializable','90bd3c397ef8d1f81a72b59b80c6a96ac158ac9fc97c95851d246eff8e66a70a'],
  ['Float','437d784b11d0b632017a94cc2c0d99b35cd93c39f49b98b0660e4316d9960dd4'],
  ['Double','d9ac93be34df21e1ec5872e307f67b1301c0606c1ccd57ee6a61030b0aa45363'],
  ['Throwable','49b74f001ee43478dae744abc5413dcffd5dd5294856fdfbb92504f5ef0f0df1'],
  ['Error','17c5ca84f07e432aadbcebb2bc455cc3c45643074a3678f0dc10a4058b3eb3af'],
  ['VirtualMachineError','5d642ae5c82224f1591dc542933a229b17f0db1ae72affe32b8b99d4f18523ee'],
  ['StackOverflowError','fccb08bbd1cfe883b6144aa55509123e94de269371e94d7365ea1ad7821bd13d'],
  ['OutOfMemoryError','96ede0eb8b6318503da363809b13ac9a7b33d99edaa69ed1c075fcab70ffe241'],
  ['LinkageError','eeb36cd0d4771d3bccd8f5d5839c140a44d1e12ac94a0cda4d79f4aa64bb6f11'],
  ['ExceptionInInitializerError','21fe8c2605bbb61c248207ed1e9c1a42b194aba9661e6b930b2c605cde962609'],
  ['IncompatibleClassChangeError','30129372d01781ee244be4ca0920d1f50e934f640f50b7fbb975673e6a8f1b6d'],
  ['NoClassDefFoundError','32060804295c79139e095a9efa9a6633f96be11ef6971f848f891473811f883f'],
  ['AbstractMethodError','877fbe3a7d637c386f08400a34cfe7c265a3ed66b384f8eac958e2ff78f88ca6'],
  ['Exception','25cb2ac6e090fc75f4ca3faa8b00586b6373a53d0ace3024fe36be272a19b34e'],
  ['RuntimeException','fb43c3b06c92c52d97957d80cc75c39a4b026d6bc94c11d4f126575406cdefad'],
  ['ArithmeticException','7d8aa035041464b3c175a642b129747f3345ed4e7df87232971968c9125ceecf'],
  ['NullPointerException','7eef86618751a918ba17f6249289e386dbcee4305ddb3a5b30d721e603ca70b8'],
  ['NegativeArraySizeException','56c402963e50be92fcf1d2808684c6ec7686c890975c06fcca33177a70e442cb'],
  ['ClassCastException','0e3883f17eb9a46d99e977879bf408be11f9418bf3902b7ea0884f57ea72b654'],
  ['ArrayStoreException','bbe8ba14a08a545da205a070b6965b2875815b1b9bd0474312fd4de4e7483ffd'],
  ['IndexOutOfBoundsException','057576b458d9581f2a1b49fd9055947038adeab15132541372a137cf89c723d1'],
  ['ArrayIndexOutOfBoundsException','2309a8d0ad31f094867d449013000340f2b22e412d7cb770f93fbc05a8439c99'],
  ['Comparable','9d291a315ca765cdcb404feb72aa3d6f1216e542476ec071238fe105f2b85775'],
  ['CharSequence','c996ea063c00b6a8e320c73d81660bf2a733e492c312a032205c8d4f1e051576'],
  ['String','7999610c7686c7622667ee57fef88d6bf576e61595ec09310dc3905cd18aedad'],
  ['IOException','61b742b86e9be1d4c3bc8c5d90156befc8ce38afc5d4425bd5751b77224d4d17'],
  ['FileNotFoundException','d964d55dc660566a64eda14af9dacbfa51a93baa8d5b772e73a083d2d258f654'],
  ['EOFException','6cb3a2c8d9baa1403f9e5a11e7e46872bcc0da45099cbe315ec248f841a6fd0c'],
  ['AutoCloseable','cafa160ddd47f90df802399cbd3ea0f4a62dc0d382c77fde7917b8b84fa51ea8'],
  ['Closeable','79fae4d62aee6a6f46bd7483265bb3a19ba9fcc89c3f6dc8a14d5814a10ed86f'],
  ['Flushable','b5679864201f2fe3eb8e7fad6a7121790281ad1ca87391d928ca9c1bc9277513'],
  ['File','aee6861b45213674f41d257a87a0508b3b9ca1d900ec995234bd51d129b83bc4'],
  ['InputStream','224fd0acae8f99ca75c2cba79902dca8408fe91fa839599a96377a31a687ba72'],
  ['OutputStream','2698b53831772935d798d8739ffe77b786f343e30f7bc5d7b1d1ae5c8efeb4c2'],
  ['FileInputStream','68fd8bf1cdb48a5309b60a28ec9573dd68b5cc96318487b82f93cfce058e4545'],
  ['FileOutputStream','4e5175528984798d6da3ef9c3cd58395e0f66788be9e11ed1a2a35fb2015f6a8'],
];
const bootstrapImages = imagePins.map(([name, expected]) => {
  const match = source.match(new RegExp(`function _bootstrap${name}\\(\\)[\\s\\S]*?return hex"([0-9a-f]+)";`));
  if (!match) throw new Error(`missing embedded bootstrap: ${name}`);
  const bytes = Buffer.from(match[1], 'hex');
  if (sha256(bytes) !== expected) throw new Error(`embedded bootstrap hash differs: ${name}`);
  return {slot: bootstrapImagesLength++, name, classBytes: bytes.length, classSHA256: expected};
});

const bootstrap = pins.map(pin => {
  const sourceText = fs.readFileSync(path.join(dir, pin.source), 'utf8');
  const hexText = fs.readFileSync(path.join(dir, pin.classHex), 'utf8').trim().toLowerCase();
  if (!/^[0-9a-f]+$/.test(hexText) || hexText.length % 2 !== 0) throw new Error(`malformed ${pin.classHex}`);
  const bytes = Buffer.from(hexText, 'hex');
  if (sha256(sourceText) !== pin.sourceSHA256 || bytes.length !== pin.bytes || sha256(bytes) !== pin.classSHA256) throw new Error(`pinned bootstrap differs: ${pin.source}`);
  const escaped = pin.fn.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const embedded = source.match(new RegExp(`function ${escaped}\\(\\)[\\s\\S]*?return hex"([0-9a-f]+)";`));
  if (!embedded || embedded[1] !== hexText) throw new Error(`embedded Solidity image differs: ${pin.fn}`);
  return {source: pin.source, sourceSHA256: sha256(sourceText), classHex: pin.classHex,
    classBytes: bytes.length, classSHA256: sha256(bytes),
    reproduction: pin.reproduction || 'javac -source 8 -target 8 -g:none'};
});
const input = {language: 'Solidity', sources: {[sourceName]: {content: source}}, settings: {
  optimizer: {enabled: true, runs: 200}, viaIR: true, evmVersion: 'cancun',
  metadata: {appendCBOR: false, bytecodeHash: 'none'},
  outputSelection: {'*': {'*': ['abi','evm.deployedBytecode.object']}}
}};
const output = JSON.parse(solc.compile(JSON.stringify(input)));
for (const e of output.errors || []) console.error(e.formattedMessage);
if ((output.errors || []).some(e => e.severity === 'error')) process.exit(1);
const c = output.contracts[sourceName].VFS0aInterpreter;
const hex = c.evm.deployedBytecode.object.toLowerCase();
const runtimeBytes = Buffer.from(hex, 'hex').length;
const capPassed = runtimeBytes <= 320 * 1024;
if (!capPassed && !measureOverCap) {
  throw new Error(`VFS0a runtime ${runtimeBytes} bytes exceeds 320 KiB by ${runtimeBytes - 320 * 1024} bytes`);
}
const runtimePath = path.join(dir, 'VFS0aInterpreter.runtime.hex');
const abiPath = path.join(dir, 'VFS0aInterpreter.abi.json');
const abi = JSON.stringify(c.abi, null, 2) + '\n';
const manifestPath = path.join(dir, 'artifacts', 'VFS0aInterpreter.json');
const manifest = JSON.stringify({contractName: 'VFS0aInterpreter', abi: c.abi,
  deployedBytecode: hex, compiler: {version: expectedVersion,
    optimizer: {enabled: true, runs: 200}, viaIR: true, evmVersion: 'cancun',
    metadata: {appendCBOR: false, bytecodeHash: 'none'}},
  sourceHashes: {[sourceName]: sha256(source)}, bootstrapImages, bootstrap
}, null, 2) + '\n';
if (check) {
  if (fs.readFileSync(runtimePath, 'utf8').trim() !== hex) throw new Error('runtime artifact differs');
  if (fs.readFileSync(abiPath, 'utf8') !== abi) throw new Error('ABI artifact differs');
  if (fs.readFileSync(manifestPath, 'utf8') !== manifest) throw new Error('combined artifact/provenance differs');
} else {
  fs.writeFileSync(runtimePath, hex + '\n'); fs.writeFileSync(abiPath, abi);
  fs.mkdirSync(path.dirname(manifestPath), {recursive: true}); fs.writeFileSync(manifestPath, manifest);
}
console.log(JSON.stringify({compiler: solc.version(), runtimeBytes,
  runtimeSHA256: sha256(Buffer.from(hex, 'hex')), sourceSHA256: sha256(source),
  acceptanceCapBytes: 320 * 1024, acceptanceCapPassed: capPassed,
  settings: {optimizer: 200, viaIR: true, evmVersion: 'cancun', metadata: false}}));
