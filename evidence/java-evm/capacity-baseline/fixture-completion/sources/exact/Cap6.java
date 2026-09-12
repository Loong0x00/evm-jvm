public class Cap6 { static int s = 9; static { s += 11; } public static int run(int x) { return Cap7.run(x + s) + 6; } }
