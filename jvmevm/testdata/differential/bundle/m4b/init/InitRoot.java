package bundle.m4b.init;

/** Static object fields and allocation during lazy/reentrant class initialization. */
public class InitRoot {
    public static int preparedNull(int yes) {
        return PreparedOwner.CELL == null ? yes : -1;
    }

    public static int initializerAllocation(int add) {
        return AllocOwner.CELL.value + add;
    }

    public static int initializerArrayInObject(int value) {
        AllocOwner.CELL.array[0] = value;
        return AllocOwner.CELL.array[0];
    }

    public static int staticAlias(int yes) {
        InitCell cell = new InitCell(3);
        MutableOwner.FIRST = cell;
        MutableOwner.SECOND = cell;
        return MutableOwner.FIRST == MutableOwner.SECOND ? yes : -1;
    }

    public static int staticReplacement(int value) {
        MutableOwner.FIRST = new InitCell(value);
        InitCell old = MutableOwner.FIRST;
        MutableOwner.FIRST = new InitCell(value + 5);
        return MutableOwner.FIRST.value - old.value;
    }

    public static int helperReturnsObject(int value) {
        MutableOwner.FIRST = MutableOwner.make(value);
        return MutableOwner.FIRST.value;
    }

    public static int reentrantPreparedNull(int yes) {
        return ReentrantOwner.SAW_NULL == 1 && ReentrantOwner.CELL.value == 23 ? yes : -1;
    }

    public static int reentrantAllocatedAlias(int yes) {
        return ReentrantOwner.CELL == ReentrantOwner.ALIAS ? yes : -1;
    }

    public static int superclassInitializationOrder(int add) {
        return InitChild.TRACE + add;
    }

    public static int superclassObjectReady(int add) {
        return InitChild.PARENT_CELL.value + InitChild.CHILD_CELL.value + add;
    }

    public static int newTriggersInitialization(int value) {
        LazyAllocated instance = new LazyAllocated(value);
        return LazyAllocated.TRACE + instance.value;
    }

    public static int initializedOnce(int value) {
        OnceObject first = new OnceObject(value);
        OnceObject second = new OnceObject(value + 1);
        return OnceObject.COUNT + first.value + second.value;
    }

    public static int staticObjectToObject(int yes) {
        Object value = AllocOwner.CELL;
        return value == AllocOwner.CELL ? yes : -1;
    }

    public static int staticArrayToObject(int yes) {
        Object value = AllocOwner.CELL.array;
        return value == AllocOwner.CELL.array ? yes : -1;
    }
}

class InitCell {
    public int value;
    public int[] array;

    InitCell(int value) {
        this.value = value;
        this.array = new int[1];
    }
}

class PreparedOwner {
    static InitCell CELL;
}

class AllocOwner {
    static InitCell CELL = new InitCell(19);
}

class MutableOwner {
    static InitCell FIRST;
    static InitCell SECOND;

    static InitCell make(int value) { return new InitCell(value); }
}

class ReentrantOwner {
    static InitCell CELL = make();
    static InitCell ALIAS = CELL;
    static int SAW_NULL;

    private static InitCell make() {
        if (CELL == null) SAW_NULL = 1;
        return new InitCell(23);
    }
}

class InitParent {
    static int TRACE = 1;
    static InitCell PARENT_CELL = new InitCell(7);
}

class InitChild extends InitParent {
    static int TRACE = InitParent.TRACE * 10 + 2;
    static InitCell CHILD_CELL = new InitCell(8);
}

class LazyAllocated {
    static int TRACE = 40;
    public int value;
    LazyAllocated(int value) { this.value = value; }
}

class OnceObject {
    static int COUNT = count();
    public int value;

    private static int count() { return 1; }
    OnceObject(int value) { this.value = value; }
}
