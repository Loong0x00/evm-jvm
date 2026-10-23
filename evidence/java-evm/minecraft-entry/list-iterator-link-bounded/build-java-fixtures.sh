#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
J=/usr/lib/jvm/java-8-openjdk/bin
mkdir -p "$ROOT/tests/classes" "$ROOT/tests/raw150-src" "$ROOT/tests/raw150-classes" "$ROOT/tests/api-classes" "$ROOT/tests/api-src"
"$J/javac" -g:none -source 8 -target 8 -d "$ROOT/tests/classes" "$ROOT/tests/src/LinkCheck.java"
"$J/javac" -g:none -source 8 -target 8 -cp "$ROOT/tests/classes" -d "$ROOT/tests/api-classes" "$ROOT/tests/src/ApiCalls.java"
cp "$ROOT/tests/classes/Cursor.class" "$ROOT/tests/api-classes/"
cp "$ROOT/tests/classes/CursorBase.class" "$ROOT/tests/api-classes/"
cp "$ROOT/tests/classes/CursorContract.class" "$ROOT/tests/api-classes/"
cp "$ROOT/tests/classes/SideMarker.class" "$ROOT/tests/api-classes/"
cp "$ROOT/tests/src/ApiCalls.java" "$ROOT/tests/api-src/"
cp "$ROOT/tests/src/LinkCheck.java" "$ROOT/tests/api-src/"
for i in $(seq -w 0 144); do printf 'public final class Filler%s {}\n' "$i" > "$ROOT/tests/raw150-src/Filler$i.java"; done
"$J/javac" -g:none -source 8 -target 8 -d "$ROOT/tests/raw150-classes" "$ROOT/tests/raw150-src"/*.java
cp "$ROOT/tests/classes"/*.class "$ROOT/tests/raw150-classes"/
count=$(find "$ROOT/tests/raw150-classes" -name '*.class' | wc -l)
test "$count" -eq 150
