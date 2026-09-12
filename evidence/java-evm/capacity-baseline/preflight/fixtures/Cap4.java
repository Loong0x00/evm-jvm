public class Cap4 { static int s = 7; static { s += 9; } public static int run(int x) { return Cap5.run(x + s) + 4; } }
