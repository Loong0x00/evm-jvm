package bundle.m4d.init;

/** Component no-initialization and reference-array class-initialization fixtures. */
public class InitRoot {
    public static int failingComponentZero(int value) {
        FailingComponent[] values = new FailingComponent[0];
        return values.length == 0 ? value : -1;
    }

    public static int failingComponentPositive(int value) {
        FailingComponent[] values = new FailingComponent[2];
        return values[0] == null && values[1] == null ? value : -1;
    }

    public static int failingComponentNested(int value) {
        FailingComponent[][] values = new FailingComponent[1][];
        return values[0] == null ? value : -1;
    }

    public static int abstractComponentNoInit(int value) {
        FailingAbstract[] values = new FailingAbstract[1];
        return values[0] == null ? value : -1;
    }

    public static int initializedArrayHolder(int value) {
        return AllocatingHolder.values.length + AllocatingHolder.marker + value;
    }

    public static int initializedArrayElement(int value) {
        AllocatingHolder.values[0] = new InitCell(value);
        return AllocatingHolder.values[0].value;
    }

    public static int initializedFinalArray(int value) {
        AllocatingHolder.FINAL_VALUES[0] = new InitCell(value);
        return ((InitCell) AllocatingHolder.FINAL_VALUES[0]).value;
    }

    public static int reentrantPreparedArray(int value) {
        return ReentrantArray.observedNull + ReentrantArray.values.length + value;
    }

    public static int componentTriggerFails(int value) {
        FailingComponent[] values = new FailingComponent[1];
        return values.length + FailingComponent.marker + value;
    }

    public static int arrayStoreInitializerFails(int value) {
        return ArrayStoreInitializer.values.length + value;
    }
}

class InitCell {
    int value;
    InitCell(int value) { this.value = value; }
}

class FailingComponent {
    static int marker = fail();
    static int fail() {
        int zero = 0;
        return 1 / zero;
    }
}

abstract class FailingAbstract {
    static int marker = fail();
    static int fail() {
        int zero = 0;
        return 2 / zero;
    }
}

class AllocatingHolder {
    static InitCell[] values = new InitCell[2];
    static final Object[] FINAL_VALUES = new Object[1];
    static int marker = 7;
}

class ReentrantArray {
    static int observedNull;
    static InitCell[] values = make();

    static InitCell[] make() {
        InitCell[] made = new InitCell[2];
        observedNull = ReentrantHelper.observe(made);
        return made;
    }
}

class ReentrantHelper {
    static int observe(InitCell[] made) {
        return ReentrantArray.values == null && made.length == 2 ? 10 : -10;
    }
}

class StoreBase {
}

class StoreChild extends StoreBase {
}

class ArrayStoreInitializer {
    static StoreBase[] values = make();

    static StoreBase[] make() {
        StoreBase[] values = new StoreChild[1];
        values[0] = new StoreBase();
        return values;
    }
}
