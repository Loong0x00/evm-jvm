public class ValidRevisitCFG {
    public static int revisit(int n) {
        int assigned;
        while (n > 0) {
            if (n == 1) {
                assigned = 7;
            } else {
                assigned = 9;
            }
            n = n - 1;
        }
        return n;
    }
}
