public class Cap2 { static int s = 5; static { s += 7; } public static int run(int x) { return Cap3.run(x + s) + 2; } }
