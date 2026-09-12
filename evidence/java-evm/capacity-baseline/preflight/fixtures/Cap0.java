public class Cap0 { static int s = 3; static { s += 5; } public static int run(int x) { return Cap1.run(x + s) + 0; } }
