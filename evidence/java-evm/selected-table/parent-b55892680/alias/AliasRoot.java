public class AliasRoot {
    static int start = 3;
    static { start += 4; }
    public static int run(int mode) {
        if (mode == 99) throw new RuntimeException();
        AliasChild c = new AliasChild(mode + start);
        AliasBase b = c;
        AliasFace f = c;
        int total = b.v(5) + f.v(7) + f.d(9) + c.superV(11)
                  + b.special(13) + (int)b.wide(19L);
        total += catchA(0) + catchA(0) + catchB(null) + catchB(null)
               + caughtThrow() + caughtThrow();
        String s = "ok";
        if (!s.equals("ok")) throw new RuntimeException();
        return total;
    }
    static int catchA(int divisor) {
        try { return 100 / divisor; }
        catch (ArithmeticException e) { return 23; }
    }
    static int catchB(int[] array) {
        try { return array.length; }
        catch (NullPointerException e) { return 29; }
    }
    static int caughtThrow() {
        try { throw new RuntimeException(); }
        catch (RuntimeException e) { return 37; }
    }
}
