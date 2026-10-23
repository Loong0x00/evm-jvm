package probe;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

public final class ArrayListDefaultProbe {
    static ArrayList factory() { return new ArrayList(); }

    public static void main(String[] args) {
        ArrayList first = factory();
        ArrayList second = factory();
        List asList = first;
        Collection asCollection = second;
        if (first == null || second == null || first == second) throw new IllegalStateException();
        if (first.size() != 0 || second.size() != 0 || !first.isEmpty() || !second.isEmpty()) throw new IllegalStateException();
        if (!(first instanceof List) || !(second instanceof Collection) || asList.size() != 0 || asCollection.size() != 0) throw new IllegalStateException();
        ArrayList zero = new ArrayList(0);
        ArrayList positive = new ArrayList(3);
        if (zero.size() != 0 || positive.size() != 0 || !zero.isEmpty() || !positive.isEmpty()) throw new IllegalStateException();
    }
}
