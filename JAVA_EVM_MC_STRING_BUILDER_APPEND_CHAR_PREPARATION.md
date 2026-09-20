# Java-on-EVM Minecraft bounded StringBuilder.append(char) preparation

Accepted `parent-868c7d1b8` runs unchanged original38 through monitor opcodes to60814J/50I in21 successful LOCAL4.2B/q4096 blocks. Exact blocker is `SimpleLogger.logMessage` PC88 invoking `StringBuilder.append(C)` for a space separator.

Replace only image84 to add ordinary append(char): preserve prior logical chars and append the UTF-16 code unit. Preserve all existing StringBuilder subset,91 images/runtime-derived root,raw38/285489,diagnostic129,native13,and all other limits/toolchain/semantics. Runtime<=393216 (baseline393191,25B headroom); verified semantics-preserving cleanup only. Focus NUL/ASCII/surrogate char, prefix, q1/q7/direct/reopen and retained controls<=1200s canonical receipts. Worker no originals; parent accelerated replay. No other append overload/provider factory/world/Done claim.
