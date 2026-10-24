import java.lang.reflect.Array;
import java.util.ListIterator;
/** Generated-only dynamic reference-array allocation witness. */
public final class ParentReflectReferenceArray {
    interface Tag { }
    private static final class Value implements Tag { Value() { } }
    private static abstract class AbstractValue { }
    private static final class Poison {
        static { if (fail()) throw new ArithmeticException(); }
        static boolean fail() { return true; }
        static void touch() { }
    }
    private static void check(boolean ok) { if (!ok) throw new ArithmeticException(); }
    private static Object allocate(Class<?> component, int length) { return Array.newInstance(component, length); }
    public static void main(String[] args) {
        // Retain actual old tail identities and canonical Class native paths.
        java.util.function.Function[] functions = new java.util.function.Function[0];
        java.util.NavigableMap[] maps = new java.util.NavigableMap[0];
        java.util.Comparator[] comparators = new java.util.Comparator[0];
        java.util.SortedSet[] sorted = new java.util.SortedSet[0];
        java.util.NavigableSet[] navigable = new java.util.NavigableSet[0];
        check(functions.length + maps.length + comparators.length + sorted.length + navigable.length == 0);
        java.util.Map<Object,Object> map = new java.util.HashMap<Object,Object>();
        java.util.Map.Entry[] target = new java.util.Map.Entry[0];
        check(map.entrySet().toArray(target) == target);
        check(String.class.getName().equals("java.lang.String"));
        check(Value.class.asSubclass(Tag.class) == Value.class);
        Object[] empty = (Object[]) allocate(Object.class, 0);
        Object[] secondEmpty = (Object[]) allocate(Object.class, 0);
        check(empty != secondEmpty && empty.length == 0 && secondEmpty.length == 0);
        String[] strings = (String[]) allocate(String.class, 2);
        check(strings.length == 2 && strings[0] == null && strings[1] == null);
        strings[0] = "x";
        check(strings[0].equals("x"));
        Tag[] values = (Tag[]) allocate(Tag.class, 3);
        check(values.length == 3 && values[0] == null && values[2] == null);
        Value value = new Value();
        values[0] = value;
        Tag[] copied = values.clone();
        check(copied != values && copied[0] == value && copied[1] == null);
        Tag[] viaArraycopy = new Tag[3];
        System.arraycopy(values, 0, viaArraycopy, 0, 3);
        check(viaArraycopy[0] == value && viaArraycopy[2] == null);
        try { ((Object[]) values)[1] = new Object(); throw new ArithmeticException(); }
        catch (ArrayStoreException expected) { }
        AbstractValue[] abstractValues = (AbstractValue[]) allocate(AbstractValue.class, 2);
        check(abstractValues.length == 2 && abstractValues[0] == null);
        ListIterator[] iteratorArray = (ListIterator[]) allocate(ListIterator.class, 1);
        check(iteratorArray.length == 1 && iteratorArray[0] == null);
        // Array creation must not trigger a component class's initialization.
        Poison[] poison = (Poison[]) allocate(Poison.class, 1);
        check(poison.length == 1 && poison[0] == null);
        try { Poison.touch(); throw new ArithmeticException(); }
        catch (ExceptionInInitializerError expected) { }
        try { allocate(null, 0); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        try { allocate(null, -1); throw new ArithmeticException(); }
        catch (NullPointerException expected) { }
        try { allocate(Tag.class, -1); throw new ArithmeticException(); }
        catch (NegativeArraySizeException expected) { }
    }
}
