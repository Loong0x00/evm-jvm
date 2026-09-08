package bundle.m4e.transport;

/** Nested arrays transported through fields and static, private-special, and virtual calls. */
public class TransportRoot {
    static TransportCell[][] staticValues;

    public static int staticArgument(int value) {
        int[][] values = new int[2][2];
        values[1][0] = value;
        return TransportHelpers.read(values);
    }

    public static int staticReturn(int value) {
        TransportCell[][] values = TransportHelpers.make(value);
        return values[1][0].read();
    }

    public static int privateSpecialArgument(int value) {
        TransportRoot root = new TransportRoot();
        TransportCell[][] values = new TransportCell[1][2];
        values[0][1] = new TransportCell(value);
        return root.readPrivate(values);
    }

    public static int privateSpecialReturn(int value) {
        TransportRoot root = new TransportRoot();
        int[][][] values = root.makePrivate(value);
        return values[0][1][0];
    }

    public static int virtualArgument(int value) {
        TransportVirtualBase helper = new TransportVirtualChild();
        int[][] values = new int[1][2];
        values[0][1] = value;
        return helper.read(values);
    }

    public static int virtualReturn(int value) {
        TransportVirtualBase helper = new TransportVirtualChild();
        TransportCell[][] values = helper.make(value);
        return values[0][1].read();
    }

    public static int instanceField(int value) {
        TransportHolder holder = new TransportHolder();
        holder.cells = new TransportCell[2][1];
        holder.cells[1][0] = new TransportCell(value);
        return holder.cells[1][0].read();
    }

    public static int staticField(int value) {
        staticValues = new TransportCell[1][2];
        staticValues[0][1] = new TransportCell(value);
        return staticValues[0][1].read();
    }

    public static int finalField(int value) {
        TransportHolder holder = new TransportHolder();
        holder.finalValues[1][0] = value;
        return holder.finalValues[1][0];
    }

    public static int objectField(int value) {
        TransportHolder holder = new TransportHolder();
        holder.object = new int[1][2];
        int[][] values = (int[][]) holder.object;
        values[0][1] = value;
        return values[0][1];
    }

    public static int fieldAliasMutation(int value) {
        TransportHolder holder = new TransportHolder();
        holder.cells = new TransportCell[2][1];
        TransportCell[][] alias = holder.cells;
        alias[1] = alias[0];
        alias[0][0] = new TransportCell(value);
        return holder.cells[1][0].read();
    }

    public static int helperPreservesPartialNull(int value) {
        int[][][] values = new int[1][2][];
        return TransportHelpers.partial(values, value);
    }

    private int readPrivate(TransportCell[][] values) {
        return values[0][1].read();
    }

    private int[][][] makePrivate(int value) {
        int[][][] values = new int[1][2][1];
        values[0][1][0] = value;
        return values;
    }
}

class TransportCell {
    int value;
    TransportCell(int value) { this.value = value; }
    int read() { return value; }
}

class TransportHolder {
    TransportCell[][] cells;
    final int[][] finalValues = new int[2][1];
    Object object;
}

class TransportHelpers {
    static int read(int[][] values) {
        return values[1][0];
    }

    static TransportCell[][] make(int value) {
        TransportCell[][] values = new TransportCell[2][1];
        values[1][0] = new TransportCell(value);
        return values;
    }

    static int partial(int[][][] values, int value) {
        values[0][1] = new int[1];
        values[0][1][0] = value;
        return values[0][0] == null ? values[0][1][0] : -1;
    }
}

class TransportVirtualBase {
    int read(int[][] values) {
        return -1;
    }

    TransportCell[][] make(int value) {
        return new TransportCell[1][1];
    }
}

class TransportVirtualChild extends TransportVirtualBase {
    int read(int[][] values) {
        return values[0][1];
    }

    TransportCell[][] make(int value) {
        TransportCell[][] values = new TransportCell[1][2];
        values[0][1] = new TransportCell(value);
        return values;
    }
}
