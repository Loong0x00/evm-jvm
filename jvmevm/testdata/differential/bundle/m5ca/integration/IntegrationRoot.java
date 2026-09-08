package bundle.m5ca.integration;

/** Switches composed with calls, defaults, objects, arrays, longs, and statics. */
public class IntegrationRoot {
    public static int defaultCall(int key, int seed) {
        M5caChoice choice = new M5caChoiceImpl(seed);
        return choice.choose(key) + choice.adjust(key - 1);
    }

    public static int defaultLoop(int key, int rounds) {
        M5caChoice choice = new M5caChoiceImpl(key);
        int value = key;
        for (int i = 0; i < rounds; i++) {
            value = choice.choose((value + i) % 9) ^ value;
        }
        return value;
    }

    public static int virtualCall(int key, int seed) {
        M5caBase base = key < 0 ? new M5caBase(seed) : new M5caDerived(seed);
        return base.choose(key) + base.value;
    }

    public static int staticInitialized(int key) {
        return M5caState.initial + M5caState.select(key);
    }

    public static int staticUpdates(int key, int seed) {
        M5caState.value = seed;
        return M5caState.update(key) * 31 + M5caState.value;
    }

    public static int arrayBody(int key, int seed) {
        int[] values = new int[] {seed, key, seed ^ key};
        switch (key) {
        case -2: values[0] += values[2]; break;
        case 0: values[1] = values[0] * 7; break;
        case 5: values[2] ^= 0x10203040; break;
        default: values[0] = values[1] = key + 11; break;
        }
        return values[0] + values[1] * 3 + values[2] * 5;
    }

    public static int longBody(int key, int seed) {
        long value = ((long) seed << 33) ^ (key & 0xffffffffL);
        switch (key) {
        case -7: value = -value; break;
        case 0: value += 0x123456789abcdef0L; break;
        case 9: value ^= Long.MIN_VALUE; break;
        default: value += (long) key * 0x100000001L; break;
        }
        return (int) (value ^ (value >>> 32));
    }
}

interface M5caChoice {
    default int choose(int key) {
        switch (key) {
        case -8: return 80;
        case -1: return 11;
        case 0: return 17;
        case 1: return 23;
        case 8: return 89;
        default: return key * 13 + 7;
        }
    }

    default int adjust(int key) {
        switch (key) {
        case -1000: return 31;
        case 4: return 37;
        case 700000: return 41;
        default: return key - 43;
        }
    }
}

class M5caChoiceImpl implements M5caChoice {
    int seed;
    M5caChoiceImpl(int seed) { this.seed = seed; }
}

class M5caBase {
    int value;
    M5caBase(int value) { this.value = value; }
    int choose(int key) {
        switch (key) {
        case -3: return value - 30;
        case 2: return value + 20;
        default: return value ^ key;
        }
    }
}

class M5caDerived extends M5caBase {
    M5caDerived(int value) { super(value); }
    int choose(int key) {
        switch (key) {
        case 0: return value + 100;
        case 2: return value + 200;
        case 4: return value + 400;
        default: return value - key;
        }
    }
}

class M5caState {
    static int initial = initialize();
    static int value;

    static int initialize() {
        int key = 4;
        switch (key) {
        case -1: return 101;
        case 4: return 404;
        default: return 909;
        }
    }

    static int select(int key) {
        switch (key) {
        case -9: return initial - 9;
        case 0: return initial;
        case 12: return initial + 12;
        default: return initial ^ key;
        }
    }

    static int update(int key) {
        switch (key) {
        case -2: value -= 20; break;
        case 0: value = -value; break;
        case 3: value = value * 3 + 1; break;
        default: value ^= key; break;
        }
        return value;
    }
}
