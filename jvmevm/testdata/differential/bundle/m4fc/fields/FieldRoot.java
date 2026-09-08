package bundle.m4fc.fields;

/** Source-valid interface field resolution, qualifier ownership, and shared final references. */
public class FieldRoot {
    public static int declaredParent(int value) { return FieldParent.PARENT + FieldState.trace * 100 + value; }
    public static int parentThroughChild(int value) { return FieldChild.PARENT + FieldState.trace * 100 + value; }
    public static int parentThroughClass(int value) { return FieldImpl.PARENT + FieldState.trace * 100 + value; }
    public static int ownChild(int value) { return FieldChild.CHILD + FieldState.trace * 100 + value; }
    public static int grandThroughChild(int value) { return FieldChild.GRAND + FieldState.trace * 100 + value; }
    public static int diamondShared(int value) { return FieldDiamond.GRAND + FieldState.trace * 100 + value; }
    public static int repeatedQualifiers(int value) { return FieldParent.PARENT + FieldChild.PARENT + FieldImpl.PARENT + FieldState.trace * 100 + value; }
    public static int hiddenParent(int value) { return HiddenParent.SAME + FieldState.trace * 100 + value; }
    public static int hiddenChild(int value) { return HiddenChild.SAME + FieldState.trace * 100 + value; }
    public static int hiddenBoth(int value) { return HiddenParent.SAME * 10 + HiddenChild.SAME + FieldState.trace * 100 + value; }
    public static int classSuperclassField(int value) { return ResolutionClass.BASE + FieldState.trace * 100 + value; }
    public static int classInterfaceField(int value) { return ResolutionClass.FACE + FieldState.trace * 100 + value; }
    public static int interfaceExplicit(int value) { return ResolutionFace.FACE + FieldState.trace * 100 + value; }
    public static int referenceSharedMutation(int value) { FieldParent.BOX.value = value; return FieldChild.BOX.value; }
    public static int referenceClassQualifierMutation(int value) { FieldImpl.BOX.value = value; return FieldParent.BOX.value; }
    public static int arraySharedMutation(int value) { FieldChild.VALUES[1] = value; return FieldParent.VALUES[1]; }
    public static int arrayClassQualifierMutation(int value) { FieldImpl.VALUES[0] = value; return FieldParent.VALUES[0]; }
    public static int preparedObjectNonNull(int value) { return FieldParent.BOX.value + value; }
    public static int preparedArrayValues(int value) { return FieldParent.VALUES[0] * 10 + FieldParent.VALUES[1] + value; }
}

class FieldState {
    static int trace;
    static int mark(int digit, int value) { trace = trace * 10 + digit; return value; }
    static FieldBox box(int digit, int value) { mark(digit, 0); return new FieldBox(value); }
    static int[] values(int digit) { mark(digit, 0); int[] result = new int[2]; result[0] = 3; result[1] = 4; return result; }
}
class FieldBox { int value; FieldBox(int value) { this.value = value; } }
interface FieldGrand { int GRAND = FieldState.mark(3, 30); }
interface FieldParent extends FieldGrand {
    int PARENT = FieldState.mark(1, 10);
    FieldBox BOX = FieldState.box(4, 40);
    int[] VALUES = FieldState.values(5);
}
interface FieldChild extends FieldParent { int CHILD = FieldState.mark(2, 20); }
interface FieldLeft extends FieldGrand {}
interface FieldRight extends FieldGrand {}
interface FieldDiamond extends FieldLeft, FieldRight {}
class FieldImpl implements FieldChild {}
interface HiddenParent { int SAME = FieldState.mark(6, 6); }
interface HiddenChild extends HiddenParent { int SAME = FieldState.mark(7, 7); }
interface ResolutionFace { int FACE = FieldState.mark(8, 80); }
class ResolutionBase { static int BASE = FieldState.mark(9, 90); }
class ResolutionClass extends ResolutionBase implements ResolutionFace {}
