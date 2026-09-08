package bundle.m4b.finals;

/** Final instance initialization and ordinary mutation through final references. */
public class FinalRoot {
    public static int constructorFinal(int value) {
        FinalHolder holder = new FinalHolder(value);
        return holder.number;
    }

    public static int initializedFinal(int value) {
        FinalHolder holder = new FinalHolder(value);
        return holder.initialized + value;
    }

    public static int finalReference(int value) {
        FinalHolder holder = new FinalHolder(value);
        return holder.cell.value;
    }

    public static int finalArrayMutation(int value) {
        FinalHolder holder = new FinalHolder(value);
        holder.array[0] = value + 1;
        return holder.array[0];
    }

    public static int finalObjectMutation(int value) {
        FinalHolder holder = new FinalHolder(value);
        holder.cell.value = value + 2;
        return holder.cell.value;
    }

    public static int distinctFinalStorage(int value) {
        FinalHolder first = new FinalHolder(value);
        FinalHolder second = new FinalHolder(value + 1);
        return second.number - first.number;
    }

    public static int finalAlias(int yes) {
        FinalHolder holder = new FinalHolder(1);
        FinalCell cell = holder.cell;
        return cell == holder.cell ? yes : -1;
    }

    public static int inheritedFinal(int value) {
        FinalChild child = new FinalChild(value);
        return child.parentFinal + child.childFinal;
    }
}

class FinalCell {
    public int value;
    FinalCell(int value) { this.value = value; }
}

class FinalHolder {
    public final int number;
    // Non-constant final: force an actual getfield, not javac's constant folding
    // with an out-of-profile java/util/Objects.requireNonNull call.
    public final int initialized;
    public final FinalCell cell;
    public final int[] array;

    FinalHolder(int value) {
        number = value;
        initialized = 17;
        cell = new FinalCell(value);
        array = new int[1];
    }
}

class FinalParent {
    public final int parentFinal;
    FinalParent(int value) { parentFinal = value; }
}

class FinalChild extends FinalParent {
    public final int childFinal;
    FinalChild(int value) {
        super(value);
        childFinal = value + 1;
    }
}
