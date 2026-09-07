public class M3aRecursion {
    private static int sumTo(int value) {
        if (value <= 0) {
            return 0;
        }
        return value + sumTo(value - 1);
    }

    private static int factorial(int value) {
        if (value <= 1) {
            return 1;
        }
        return value * factorial(value - 1);
    }

    private static int fibonacci(int value) {
        if (value <= 1) {
            return value;
        }
        return fibonacci(value - 1) + fibonacci(value - 2);
    }

    private static int even(int value) {
        if (value == 0) {
            return 1;
        }
        return odd(value - 1);
    }

    private static int odd(int value) {
        if (value == 0) {
            return 0;
        }
        return even(value - 1);
    }

    private static int gcd(int first, int second) {
        if (second == 0) {
            return first;
        }
        return gcd(second, first % second);
    }

    private static int carryThroughFrames(int value, int depth) {
        int saved = value;
        if (depth == 0) {
            return saved;
        }
        int nested = carryThroughFrames(value + 3, depth - 1);
        return saved + nested;
    }

    private static int recurseForever(int value) {
        return recurseForever(value + 1);
    }

    public static int recursiveSum(int value) {
        return sumTo(value);
    }

    public static int recursiveFactorial(int value) {
        return factorial(value);
    }

    public static int recursiveFibonacci(int value) {
        return fibonacci(value);
    }

    public static int mutualParity(int value) {
        return even(value);
    }

    public static int recursiveGcd(int first, int second) {
        return gcd(first, second);
    }

    public static int recursiveFrameIsolation(int value, int depth) {
        return carryThroughFrames(value, depth);
    }

    public static int unboundedRecursion(int value) {
        return recurseForever(value);
    }
}
