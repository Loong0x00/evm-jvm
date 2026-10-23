#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
JAVA_HOME=${JAVA_HOME:-/usr/lib/jvm/java-8-openjdk}
case $("$JAVA_HOME/bin/javac" -version 2>&1) in
  'javac 1.8.'*) ;;
  *) echo "requires Java 8 javac: $JAVA_HOME" >&2; exit 1 ;;
esac
mkdir -p "$ROOT/java-classes"
"$JAVA_HOME/bin/javac" -source 8 -target 8 -g:none \
  -bootclasspath "$JAVA_HOME/jre/lib/rt.jar" \
  -d "$ROOT/java-classes" \
  "$ROOT/java-src/java/util/SortedSet.java" \
  "$ROOT/java-src/java/util/NavigableSet.java"
