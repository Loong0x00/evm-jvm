public class Loops {
    public static int sum(int count) {
        int total = 0;
        while (count > 0) {
            total += count;
            count--;
        }
        return total;
    }

    public static int fibonacci(int count) {
        int previous = 0;
        int current = 1;
        while (count > 0) {
            int next = previous + current;
            previous = current;
            current = next;
            count--;
        }
        return previous;
    }

    public static int select(int condition, int whenZero, int otherwise) {
        int result;
        if (condition == 0) {
            result = whenZero;
        } else {
            result = otherwise;
        }
        return result;
    }
}
