package bundle.m4b.core;

/** Ordinary-object, reference-transport, field, alias, and private-call fixtures. */
public class CoreRoot {
    public int rootValue;

    public CoreRoot() {}

    private int addPrivate(int a, int b) {
        return a + b + rootValue;
    }

    private int recursePrivate(int n, int acc) {
        if (n == 0) return acc + rootValue;
        return recursePrivate(n - 1, acc + n);
    }

    private CoreCell echoCell(CoreCell value) { return value; }
    private Object echoObject(Object value) { return value; }
    private int[] echoArray(int[] value) { return value; }
    private void writePrivate(int value) { rootValue = value; }

    public static int defaultInt(int add) {
        CoreCell cell = new CoreCell();
        return cell.value + add;
    }

    public static int defaultObjectNull(int yes) {
        CoreCell cell = new CoreCell();
        return cell.object == null ? yes : -1;
    }

    public static int defaultArrayNull(int yes) {
        CoreCell cell = new CoreCell();
        return cell.array == null ? yes : -1;
    }

    public static int defaultCellNull(int yes) {
        CoreCell cell = new CoreCell();
        return cell.next == null ? yes : -1;
    }

    public static int constructorValue(int value) {
        return new CoreCell(value).value;
    }

    public static int constructorPair(int a, int b) {
        CorePair pair = new CorePair(a, b);
        return pair.left.value * 31 + pair.right.value;
    }

    public static int writeReadInt(int value) {
        CoreCell cell = new CoreCell();
        cell.value = value;
        return cell.value;
    }

    public static int assignmentExpression(int value) {
        CoreCell cell = new CoreCell();
        return (cell.value = value) + cell.value;
    }

    public static int postIncrement(int value) {
        CoreCell cell = new CoreCell(value);
        int old = cell.value++;
        return old + cell.value;
    }

    public static int preIncrement(int value) {
        CoreCell cell = new CoreCell(value);
        return ++cell.value;
    }

    public static int aliasWrite(int value) {
        CoreCell first = new CoreCell(1);
        CoreCell second = first;
        second.value = value;
        return first.value;
    }

    public static int distinctObjects(int value) {
        CoreCell first = new CoreCell(value);
        CoreCell second = new CoreCell(value + 1);
        first.value = second.value + 10;
        return first.value - second.value;
    }

    public static int sameIdentity(int yes) {
        CoreCell first = new CoreCell();
        CoreCell second = first;
        return first == second ? yes : -1;
    }

    public static int distinctIdentity(int yes) {
        CoreCell first = new CoreCell();
        CoreCell second = new CoreCell();
        return first != second ? yes : -1;
    }

    public static int nullIdentity(int yes) {
        CoreCell cell = null;
        return cell == null ? yes : -1;
    }

    public static int referenceFieldAlias(int value) {
        CoreCell owner = new CoreCell();
        CoreCell child = new CoreCell(value);
        owner.next = child;
        child.value += 3;
        return owner.next.value;
    }

    public static int referenceFieldReplace(int value) {
        CoreCell owner = new CoreCell();
        owner.next = new CoreCell(value);
        CoreCell old = owner.next;
        owner.next = new CoreCell(value + 9);
        return owner.next.value - old.value;
    }

    public static int objectStoresObject(int yes) {
        CoreCell owner = new CoreCell();
        CoreCell child = new CoreCell();
        owner.object = child;
        return owner.object == child ? yes : -1;
    }

    public static int objectStoresArray(int yes) {
        CoreCell owner = new CoreCell();
        int[] array = new int[2];
        owner.object = array;
        return owner.object == array ? yes : -1;
    }

    public static int arrayFieldAlias(int value) {
        CoreCell owner = new CoreCell();
        int[] array = new int[2];
        owner.array = array;
        owner.array[1] = value;
        return array[1];
    }

    public static int mixedHeapIdentity(int yes) {
        CoreCell object = new CoreCell();
        int[] array = new int[1];
        Object left = object;
        Object right = array;
        return left != right ? yes : -1;
    }

    public static int objectStaticTransport(int yes) {
        CoreCell cell = new CoreCell();
        Object result = CoreCell.passObject(cell);
        return result == cell ? yes : -1;
    }

    public static int arrayStaticTransport(int value) {
        int[] array = new int[1];
        CoreCell.passArray(array)[0] = value;
        return array[0];
    }

    public static int cellStaticTransport(int value) {
        CoreCell cell = new CoreCell(value);
        return CoreCell.passCell(cell).value;
    }

    public static int staticFieldAccessor(int value) {
        CoreCell cell = new CoreCell(value);
        return CoreCell.readValue(cell);
    }

    public static int privateArgs(int a, int b) {
        CoreRoot root = new CoreRoot();
        root.rootValue = 7;
        return root.addPrivate(a, b);
    }

    public static int privateRecursion(int n) {
        CoreRoot root = new CoreRoot();
        root.rootValue = 1;
        return root.recursePrivate(n, 0);
    }

    public static int privateReferenceReturn(int value) {
        CoreRoot root = new CoreRoot();
        CoreCell cell = new CoreCell(value);
        return root.echoCell(cell).value;
    }

    public static int privateObjectReturn(int yes) {
        CoreRoot root = new CoreRoot();
        CoreCell cell = new CoreCell();
        return root.echoObject(cell) == cell ? yes : -1;
    }

    public static int privateArrayReturn(int value) {
        CoreRoot root = new CoreRoot();
        int[] array = new int[1];
        root.echoArray(array)[0] = value;
        return array[0];
    }

    public static int privateVoid(int value) {
        CoreRoot root = new CoreRoot();
        root.writePrivate(value);
        return root.rootValue;
    }
}

class CoreCell {
    public int value;
    public CoreCell next;
    public Object object;
    public int[] array;

    CoreCell() {}
    CoreCell(int value) { this.value = value; }

    static CoreCell passCell(CoreCell value) { return value; }
    static Object passObject(Object value) { return value; }
    static int[] passArray(int[] value) { return value; }
    static int readValue(CoreCell value) { return value.value; }
}

class CorePair {
    public CoreCell left;
    public CoreCell right;

    CorePair(int left, int right) {
        this.left = new CoreCell(left);
        this.right = new CoreCell(right);
    }
}
