public class Cap5 { static int s = 8; static { s += 10; } public static int run(int x) { return Cap6.run(x + s) + 5; } }
