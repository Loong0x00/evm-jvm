public class Cap3 { static int s = 6; static { s += 8; } public static int run(int x) { return Cap4.run(x + s) + 3; } }
