package bundle.m5bb.basic;

public class LongArrayRoot {
    private static long join(int high, int low) {
        return ((long) high << 32) | (low & 0xffffffffL);
    }

    private static int fold(long value) {
        return (int) (value ^ (value >>> 32));
    }

    public static int patterns(int seed) {
        long[] values = new long[6];
        values[0] = 0L;
        values[1] = Long.MIN_VALUE;
        values[2] = Long.MAX_VALUE;
        values[3] = 0x0123456789abcdefL;
        values[4] = 0xfedcba9876543210L;
        values[5] = join(seed, seed * 17 + 3);
        long digest = 0L;
        for (int i = 0; i < values.length; i++) {
            digest = (digest * 33L) ^ values[i];
        }
        return fold(digest);
    }

    public static int storeLoad(int high, int low) {
        long[] values = new long[1];
        values[0] = join(high, low);
        return fold(values[0]);
    }

    public static int defaultZero(int length) {
        long[] values = new long[length];
        long digest = length;
        for (int i = 0; i < values.length; i++) {
            digest |= values[i];
        }
        return fold(digest);
    }

    public static int zeroLengthDistinct(int seed) {
        long[] first = new long[0];
        long[] second = new long[0];
        return (first == second ? 1000 : 2000) + first.length + second.length + seed;
    }

    public static int aliases(int high, int low) {
        long[] first = new long[2];
        long[] alias = first;
        alias[1] = join(high, low);
        return fold(first[1]) + (first == alias ? 17 : 0);
    }

    public static int distinct(int high, int low) {
        long[] first = new long[1];
        long[] second = new long[1];
        first[0] = join(high, low);
        return fold(second[0]) + (first == second ? 31 : 47);
    }

    public static int signedSum(int seed) {
        long[] values = new long[] {
            Long.MIN_VALUE, Long.MAX_VALUE, join(seed, ~seed), -7L, 9L
        };
        long sum = 0L;
        for (int i = 0; i < values.length; i++) {
            sum += values[i];
        }
        return fold(sum);
    }

    public static int signedSearch(int selector) {
        long[] values = new long[] {
            Long.MIN_VALUE, -0x100000001L, 0L, 0x100000001L, Long.MAX_VALUE
        };
        long target = selector < 0 ? -0x100000001L
            : (selector == 0 ? 0x100000001L : 0x7000000000000007L);
        for (int i = 0; i < values.length; i++) {
            if (values[i] == target) {
                return i * 100 + fold(values[i]);
            }
        }
        return -1;
    }

    public static int smallSort(int seed) {
        long[] values = new long[] {
            join(seed, 7), Long.MAX_VALUE, Long.MIN_VALUE, join(-seed, -9)
        };
        for (int i = 1; i < values.length; i++) {
            long selected = values[i];
            int j = i - 1;
            while (j >= 0 && values[j] > selected) {
                values[j + 1] = values[j];
                j--;
            }
            values[j + 1] = selected;
        }
        long digest = 0L;
        for (int i = 0; i < values.length; i++) {
            digest = digest * 17L + values[i];
        }
        return fold(digest);
    }

    public static int postIncrement(int high, int low) {
        long[] values = new long[1];
        values[0] = join(high, low);
        long old = values[0]++;
        return fold(old) * 31 + fold(values[0]);
    }

    public static int preIncrement(int high, int low) {
        long[] values = new long[1];
        values[0] = join(high, low);
        long observed = ++values[0];
        return fold(observed) * 31 + fold(values[0]);
    }

    public static int compoundAssignment(int high, int low, int delta) {
        long[] values = new long[1];
        values[0] = join(high, low);
        long observed = (values[0] += (long) delta << 33);
        return fold(observed) * 31 + fold(values[0]);
    }

    public static int assignmentExpression(int high, int low) {
        long[] values = new long[2];
        long observed = (values[1] = join(high, low));
        return fold(observed) * 31 + fold(values[1]);
    }

    public static int chainedAssignment(int high, int low) {
        long[] values = new long[2];
        long observed = (values[0] = values[1] = join(high, low));
        return fold(observed) + fold(values[0]) * 3 + fold(values[1]) * 5;
    }

    public static int nullRead(int index) {
        long[] values = null;
        return fold(values[index]);
    }

    public static int nullWrite(int index) {
        long[] values = null;
        values[index] = 0x1234567887654321L;
        return index;
    }

    public static int nullLength(int seed) {
        long[] values = null;
        return values.length + seed;
    }

    public static int boundsRead(int index) {
        long[] values = new long[2];
        return fold(values[index]);
    }

    public static int boundsWrite(int index) {
        long[] values = new long[2];
        values[index] = Long.MIN_VALUE;
        return index;
    }

    public static int negativeLength(int length) {
        return new long[length].length;
    }

    public static int arithmeticBeforeNullStore(int zero) {
        long[] values = null;
        values[-1] = 0x123456789abcdef0L / (long) zero;
        return 1;
    }

    public static int arithmeticBeforeBoundsStore(int zero) {
        long[] values = new long[0];
        values[7] = Long.MIN_VALUE / (long) zero;
        return 1;
    }
}
