# Parent catchable ClassNotFoundException preflight

**Parent-verified LOCAL384 guest CNFE kind13.** Not reflection, Class.forName,
lazy archive loading or Minecraft startup. Evidence:
`evidence/java-evm/minecraft-entry/parent-10c10d224/`.

Worker615a5424f/10c10d224 session ended after its commit. It appends minimal Java8
ReflectiveOperationException(156B, SHA
`3760596609ce01d864acfa7ab9740f751a80471a8818406bf14bd5a2122d0e14`)
and ClassNotFoundException(169B, SHA
`8bddff8a7bf6ffd746c72b8d8993b0625b29a91ffa34bd49e042ad28ef8d0ce7`)
at66/67, total68. Both are reserved throwable classes.

Exception registry expands13→14 and maps kind13 to Throwable bootstrap+62. Envelope
javaKind, decoded heap exception-kind, pending-kind and exact-known-kind bounds all
accept13. Binding8 present lookup/mirror/no-init/frontier and guest OOM remain exact;
missing or lexical-invalid names consume the native argument and call `_raiseJava(13)`.
Existing Java handler selection catches exact CNFE or ReflectiveOperationException.
An uncaught miss commits lifecycle3/javaKind13 instead of EVM refusal or fake null.

Worker's initial fixture used getter before mirror, dotted nested-name syntax and an
initialization read that initialized its target; final committed fixtures corrected all.
Worker did not finish retained prior controls/whole watchdog before transport loss.
Parent independently source-builds both images and verifies all kind13 boundaries.

## Pins and generated proof

* LOCAL engine `0x4d432d434e46452d504152454e54000000000001`, domain
  `MC-CLASS-NOT-FOUND-PARENT1` all nine;
* engine357178B/36038B LOCAL384 headroom, SHA256
  `2be4190b19396daab9a83ddd7435526d4b1fc8c8da9f9859cac748daa70ca87e`,
  Keccak `d5feac58d5e617c8e5dbeab019a03691266b968a053d85d721be0b98189ef30d`;
* ordinary coordinator4146B, Keccak
  `2a0c1641f7056732bdd08c655881b0f48cae1e46fb4a8163587c0667fca485de`;
*68 bootstrap/native1..8/exception kinds14; all accepted/LOCAL limits unchanged.

Combined generated exact+super catches, malformed CNFE, present loadClass identity/
no-init and all Boolean/System/IAE/EVM-ZI0 resource/URL/set/thread/PA controls finish
VOID3580J/24I, q1/q7/q4096 epochs3580/512/1, machine
`8693fe8c9ff1f6a125dd42770c486c9886cef7b922afd5badc1ce8e9de85db3f`, opaque
SHA `80163e6da4a1307dcc2e0badfbf1a8d0e36fb72716a13a1359f855697d6b9c30`.
Uncaught q1/q7/q4096 agree at9J/3I, epochs10/2/1, lifecycle3/kind13, machine
`8f3c13cb1706041e1ce783854696fe00bc30d800dbb07d14667e7feb20a1ff76`, opaque
`8da76e190e8a33bdd66a7eb9b72afa3e8b65e804562e9522353876280eca59d5`.
4106 canonical receipts/reopens pass; new/prior replacements and omissions refuse.

Parent's first source+q1 gate failed at unsupported fixture Object.getClass/getCause
(221.490360s/971255808B); those methods were never in the claimed profile, so the
fixture now proves exact catch via handler/instanceof. Second source+all positive/new
controls gate reached only a missing archived ClassLoader replacement source
(875.189299s/975110144B). Both full compiler peaks and failures are preserved. Final
fresh all-EVM/generated/original execution gate exits0 in
798.931427s/158773248B using that exact source-built engine. No failed state is reused.

## Original frontier

Fresh unchanged original22 catches CNFE for absent `javax.servlet.Servlet` and enters
LoaderUtil.loadClass fallback. q7 reaches epoch326/**2282J/25I**, CP SHA
`f0b206947a6a41d1e9fcba7cf61a8c0969c51aca6bb67ec0edcbd4d76faafead`,
then CallError(3,21). One q1 commits fallback PC21 with class-name String on stack.

Final epoch327/**2283J/25I**,15247B CP SHA
`471502b3096314dba76c2185a065994224eae260109b80dc8da0fcf32d36b562`,
checkpoint root `3b64b316a34112f230ca726c4d167ed9e5946067fb028ea6b2c60596dcee740b`,
machine root `48033a772cda15cfca7828145a0b452a4e566a869ccafb3bd4b9592aa1573d3a`.
Last gas153908358/max160366677. Next q1 repeats CallError(3,21), gas105702690,
Head/root unchanged.327 canonical original receipts pass.

PC21 is exact static `Class.forName(String)Class` for the same absent Servlet name.
Next adds missing-only catchable forName via binding9; present targets return only if
already initialized, never fake Java initialization. Archive10734 files excludes
original payload/LevelDB. No push/main-body/world/Done.
