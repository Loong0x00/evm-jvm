public final class BooleanHostOracle { public static void main(String[] args) { BooleanProbe.main(args); if (BooleanProbe.result != 127) throw new AssertionError(BooleanProbe.result); } }
