package bundle.m5ca.switches;

/** Bounded source-level integer switch shapes compiled unchanged with --release 8. */
public class SwitchRoot {
    private static int helper(int key) {
        switch (key) {
        case -9: return 91;
        case -1: return 17;
        case 0: return 23;
        case 4: return 47;
        case 19: return 193;
        default: return key * 3 - 5;
        }
    }

    public static int dense(int key) {
        switch (key) {
        case 2: return 20;
        case 3: return 31;
        case 4: return 42;
        case 5: return 53;
        case 6: return 64;
        default: return key - 700;
        }
    }

    public static int negativeDense(int key) {
        switch (key) {
        case -6: return 601;
        case -5: return 502;
        case -4: return 403;
        case -3: return 304;
        case -2: return 205;
        default: return key + 900;
        }
    }

    public static int sparse(int key) {
        switch (key) {
        case Integer.MIN_VALUE: return 101;
        case -1000000000: return 202;
        case -32769: return 303;
        case -1: return 404;
        case 0: return 505;
        case 32768: return 606;
        case 1000000000: return 707;
        case Integer.MAX_VALUE: return 808;
        default: return key ^ 0x13579bdf;
        }
    }

    public static int fallThrough(int key) {
        int value = 3;
        switch (key) {
        case -1:
            value += 5;
        case 0:
            value = value * 2 + 1;
        case 1:
            value += 11;
            break;
        case 2:
        case 3:
            value += key * 7;
        default:
            value = value * 3 - 4;
        }
        return value;
    }

    public static int nested(int outer, int inner) {
        int value;
        switch (outer) {
        case -1:
            switch (inner) {
            case 0: value = 101; break;
            case 1: value = 102; break;
            default: value = 109; break;
            }
            break;
        case 3:
            switch (inner) {
            case -1000: value = 301; break;
            case 7: value = 302; break;
            case 900000: value = 303; break;
            default: value = 309; break;
            }
            break;
        default:
            value = 900 + inner;
            break;
        }
        return value;
    }

    public static int loop(int seed, int rounds) {
        int value = seed;
        for (int i = 0; i < rounds; i++) {
            switch ((value + i) & 7) {
            case 0: value += 17; break;
            case 1: value ^= 0x1234; break;
            case 2: value = value * 3 + i; break;
            case 3: value -= 29; break;
            case 4: value = (value << 1) | (value >>> 31); break;
            case 5: value += helper(i - 4); break;
            case 6: value = ~value; break;
            default: value ^= i * 31; break;
            }
        }
        return value;
    }

    public static int callAndLong(int key, int seed) {
        long prefix = ((long) seed << 32) | (key & 0xffffffffL);
        int selected = helper(key);
        long mixed = prefix + (long) selected * 0x100000001L;
        return (int) (mixed ^ (mixed >>> 32));
    }

    public static int callAndReference(int key, int seed) {
        int[] prefix = new int[] {seed, seed ^ 0x55aa55aa};
        int selected = helper(key);
        return prefix[0] + prefix[1] * 3 + selected * 5;
    }

    public static int twoSwitches(int first, int second) {
        int value = helper(first);
        switch (second) {
        case -2000000000: value += 13; break;
        case -17: value *= 3; break;
        case 6: value ^= 0x77777777; break;
        case 2000000000: value -= 19; break;
        default: value += second;
        }
        return value;
    }
}
