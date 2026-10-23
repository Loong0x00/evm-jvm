#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
J=/usr/lib/jvm/java-8-openjdk/bin
mkdir -p "$ROOT/build/compiler-support-classes" "$ROOT/build/bootstrap-classes"
"$J/javac" -g:none -source 8 -target 8 -d "$ROOT/build/compiler-support-classes" "$ROOT/compiler-support/java/lang/Object.java" "$ROOT/compiler-support/java/lang/Throwable.java" "$ROOT/compiler-support/java/util/Iterator.java"
"$J/javac" -g:none -source 8 -target 8 -bootclasspath "$ROOT/build/compiler-support-classes" -d "$ROOT/build/bootstrap-classes" "$ROOT/bootstrap/java/util/ListIterator.java"
cp "$ROOT/build/bootstrap-classes/java/util/ListIterator.class" "$ROOT/ListIterator.class"
