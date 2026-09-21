#!/usr/bin/env python3
"""Emit the exact bounded PrintStream(OutputStream) image; no host output exists."""
from pathlib import Path

# Accepted direct-OutputStream PrintStream image. This producer appends only the
# Object.getClass null-check CP entries, the OutputStream constructor descriptor,
# and the one public constructor member; all retained member bytes stay exact.
_BASE = bytes.fromhex(
    "cafebabe0000003400180a0004000b090003000c07000d07000e0100124c6a6176612f6c616e672f537472696e673b0100063c696e69743e010003282956010004436f64650100077072696e746c6e010015284c6a6176612f6c616e672f537472696e673b29560c000600070c000900050100136a6176612f696f2f5072696e7453747265616d0100146a6176612f696f2f4f757470757453747265616d09000300120100057072696e74010001430c00100011010004284329560c001000130100057772697465010004284929560c0015001600210003000400000002000200090005000000020010001100000004000100060007000100080000001100010001000000052ab70001b10000000000010009000a0001000800000016000200020000000a2bc22bc32a2bb50002b100000000000100100013000100080000001200020002000000062a1bb5000fb1000000000001001500160001000800000017000300020000000b2a1b1100ff7e92b5000fb1000000000000"
)


def _u2(data, at):
    return int.from_bytes(data[at:at + 2], "big"), at + 2


def _u4(data, at):
    return int.from_bytes(data[at:at + 4], "big"), at + 4


def _skip_cp(data, at, count):
    index = 1
    while index < count:
        tag = data[at]
        at += 1
        if tag == 1:
            size, at = _u2(data, at)
            at += size
        elif tag in (3, 4):
            at += 4
        elif tag in (5, 6):
            at += 8
            index += 1
        elif tag in (7, 8, 16, 19, 20):
            at += 2
        elif tag in (9, 10, 11, 12, 18):
            at += 4
        elif tag == 15:
            at += 3
        else:
            raise AssertionError(("cp tag", tag))
        index += 1
    return at


def _skip_member(data, at):
    at += 6
    attributes, at = _u2(data, at)
    for _ in range(attributes):
        at += 2
        length, at = _u4(data, at)
        at += length
    return at


def build():
    count = int.from_bytes(_BASE[8:10], "big")
    assert count == 24
    cp_end = _skip_cp(_BASE, 10, count)
    at = cp_end + 6
    interfaces, at = _u2(_BASE, at)
    at += 2 * interfaces
    fields, at = _u2(_BASE, at)
    for _ in range(fields):
        at = _skip_member(_BASE, at)
    methods_at = at
    methods, at = _u2(_BASE, at)
    assert methods == 4
    first_end = _skip_member(_BASE, at)

    # #24 Methodref java/lang/Object.getClass:()Ljava/lang/Class;
    # #25 Class java/lang/Object; #26 Utf8 java/lang/Object;
    # #27 NameAndType getClass:()Ljava/lang/Class;; #28/#29 are its Utf8 items;
    # #30 is the constructor descriptor.
    extra_cp = bytes.fromhex(
        "0a0019001b"  # #24 Methodref #25.#27
        "07001a"      # #25 Class #26
        "0100106a6176612f6c616e672f4f626a656374"  # #26 java/lang/Object
        "0c001c001d"  # #27 NameAndType #28:#29
        "010008676574436c617373"  # #28 getClass
        "01001328294c6a6176612f6c616e672f436c6173733b"  # #29 ()Ljava/lang/Class;
        "010019284c6a6176612f696f2f4f757470757453747265616d3b2956"  # #30 (Ljava/io/OutputStream;)V
    )
    # public PrintStream(OutputStream sink) { super(); sink.getClass(); }
    # invokevirtual Object.getClass supplies the ordinary canonical guest NPE
    # for a null sink without constructing or forwarding a FilterOutputStream.
    constructor = bytes.fromhex(
        "00010006001e0001000800000016"
        "000100020000000a2ab700012bb6001857b1"
        "00000000"
    )
    image = (
        _BASE[:8] + (31).to_bytes(2, "big") + _BASE[10:cp_end] + extra_cp
        + _BASE[cp_end:methods_at] + (5).to_bytes(2, "big")
        + _BASE[at:first_end] + constructor + _BASE[first_end:]
    )
    assert image[:8] == bytes.fromhex("cafebabe00000034")
    return image


if __name__ == "__main__":
    (Path(__file__).parent / "java/io/PrintStream.class.hex").write_text(build().hex() + "\n")
