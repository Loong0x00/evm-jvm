package perfcheck.missing;

public final class Main {
    public static void main(String[] args) {
        int sum = 0;
        for (int i = 0; i < 80; i++) {
            sum += i;
        }
        MissingDependency.touch();
        if (sum == -1) {
            sum++;
        }
    }
}
