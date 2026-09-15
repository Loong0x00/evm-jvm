public final class FlagMain { static int x; public static void main(String[] a) { x=new Flagged().touch(); if(x!=7) throw new Error(); } }
