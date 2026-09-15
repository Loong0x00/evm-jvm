public final class FlagMain implements FlagIface { public int touch(){return 7;} public static void main(String[] a) { int x=new FlagMain().touch(); if(x!=7) throw new Error(); } }
