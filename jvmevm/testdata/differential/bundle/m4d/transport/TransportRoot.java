package bundle.m4d.transport;

/** Reference arrays through fields and static/special/virtual helper calls and returns. */
public class TransportRoot {
    private TransportCell[] privateIdentity(TransportCell[] values) {
        return values;
    }

    private int privateMutate(TransportCell[] values, int value) {
        values[0] = new TransportCell(value);
        return values[0].value;
    }

    private static TransportCell[] staticIdentity(TransportCell[] values) {
        return values;
    }

    public static int instanceFieldDefault(int value) {
        TransportHolder holder = new TransportHolder();
        return holder.cells == null ? value : -1;
    }

    public static int instanceFieldStore(int value) {
        TransportHolder holder = new TransportHolder();
        holder.cells = new TransportCell[1];
        holder.cells[0] = new TransportCell(value);
        return holder.cells[0].value;
    }

    public static int instanceFieldAlias(int value) {
        TransportHolder holder = new TransportHolder();
        TransportCell[] values = new TransportCell[1];
        holder.cells = values;
        values[0] = new TransportCell(value);
        return holder.cells[0].value;
    }

    public static int instanceFieldReplace(int value) {
        TransportHolder holder = new TransportHolder();
        holder.cells = new TransportCell[1];
        TransportCell[] first = holder.cells;
        holder.cells = new TransportCell[2];
        holder.cells[1] = new TransportCell(value);
        return first != holder.cells ? holder.cells[1].value : -1;
    }

    public static int objectFieldArray(int value) {
        TransportHolder holder = new TransportHolder();
        holder.object = new TransportCell[1];
        TransportCell[] values = (TransportCell[]) holder.object;
        values[0] = new TransportCell(value);
        return values[0].value;
    }

    public static int nestedField(int value) {
        TransportHolder holder = new TransportHolder();
        holder.matrix = new TransportCell[1][];
        holder.matrix[0] = new TransportCell[1];
        holder.matrix[0][0] = new TransportCell(value);
        return holder.matrix[0][0].value;
    }

    public static int finalFieldMutation(int value) {
        TransportHolder holder = new TransportHolder();
        holder.finalCells[0] = new TransportCell(value);
        return holder.finalCells[0].value;
    }

    public static int staticFieldDefault(int value) {
        return TransportHolder.shared == null ? value : -1;
    }

    public static int staticFieldStore(int value) {
        TransportHolder.shared = new TransportCell[1];
        TransportHolder.shared[0] = new TransportCell(value);
        return TransportHolder.shared[0].value;
    }

    public static int staticFieldReplace(int value) {
        TransportHolder.shared = new TransportCell[1];
        TransportCell[] first = TransportHolder.shared;
        TransportHolder.shared = new TransportCell[2];
        return first != TransportHolder.shared && TransportHolder.shared.length == 2 ? value : -1;
    }

    public static int staticFinalMutation(int value) {
        TransportHolder.FINAL_OBJECTS[1] = new TransportCell(value);
        return ((TransportCell) TransportHolder.FINAL_OBJECTS[1]).value;
    }

    public static int staticArgumentReturn(int value) {
        TransportCell[] values = new TransportCell[1];
        TransportCell[] returned = staticIdentity(values);
        returned[0] = new TransportCell(value);
        return returned == values ? values[0].value : -1;
    }

    public static int privateSpecialReturn(int value) {
        TransportRoot root = new TransportRoot();
        TransportCell[] values = new TransportCell[1];
        TransportCell[] returned = root.privateIdentity(values);
        returned[0] = new TransportCell(value);
        return returned == values ? values[0].value : -1;
    }

    public static int privateSpecialMutation(int value) {
        TransportRoot root = new TransportRoot();
        TransportCell[] values = new TransportCell[1];
        return root.privateMutate(values, value) + values[0].value;
    }

    public static int virtualArgument(int value) {
        TransportLibrary library = new TransportLibrary();
        TransportCell[] values = new TransportCell[1];
        return library.write(values, value) + values[0].value;
    }

    public static int virtualOverrideArgument(int value) {
        TransportLibrary library = new TransportLibraryChild();
        TransportCell[] values = new TransportCell[1];
        return library.write(values, value) + values[0].value;
    }

    public static int virtualArrayReturn(int value) {
        TransportLibrary library = new TransportLibraryChild();
        TransportCell[] values = library.make(value);
        return values[0].value;
    }

    public static int virtualObjectArrayReturn(int value) {
        TransportLibrary library = new TransportLibraryChild();
        Object[] values = library.makeObjects(value);
        return ((TransportCell) values[0]).value;
    }

    public static int crossClassNestedReturn(int value) {
        TransportCell[][] matrix = TransportUtility.matrix(value);
        return matrix[0][0].value;
    }

    public static int recursiveArrayIdentity(int depth) {
        TransportCell[] values = new TransportCell[1];
        values[0] = new TransportCell(depth);
        TransportCell[] returned = TransportUtility.recurse(values, depth);
        return returned == values ? returned[0].value : -1;
    }
}

class TransportCell {
    int value;
    TransportCell(int value) { this.value = value; }
}

class TransportHolder {
    TransportCell[] cells;
    Object object;
    TransportCell[][] matrix;
    final TransportCell[] finalCells = new TransportCell[1];
    static TransportCell[] shared;
    static final Object[] FINAL_OBJECTS = new Object[2];
}

class TransportLibrary {
    int write(TransportCell[] values, int value) {
        values[0] = new TransportCell(value);
        return value + 1;
    }

    TransportCell[] make(int value) {
        TransportCell[] values = new TransportCell[1];
        values[0] = new TransportCell(value + 2);
        return values;
    }

    Object[] makeObjects(int value) {
        Object[] values = new Object[1];
        values[0] = new TransportCell(value + 3);
        return values;
    }
}

class TransportLibraryChild extends TransportLibrary {
    int write(TransportCell[] values, int value) {
        values[0] = new TransportCell(value + 10);
        return value + 20;
    }

    TransportCell[] make(int value) {
        TransportCell[] values = new TransportCell[1];
        values[0] = new TransportCell(value + 20);
        return values;
    }

    Object[] makeObjects(int value) {
        Object[] values = new Object[1];
        values[0] = new TransportCell(value + 30);
        return values;
    }
}

class TransportUtility {
    static TransportCell[][] matrix(int value) {
        TransportCell[][] values = new TransportCell[1][];
        values[0] = new TransportCell[1];
        values[0][0] = new TransportCell(value);
        return values;
    }

    static TransportCell[] recurse(TransportCell[] values, int depth) {
        if (depth == 0) {
            return values;
        }
        values[0].value = values[0].value + 1;
        return recurse(values, depth - 1);
    }
}
