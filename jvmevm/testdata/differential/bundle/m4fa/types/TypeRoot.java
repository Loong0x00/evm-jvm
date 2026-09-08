package bundle.m4fa.types;

import java.io.Serializable;

/** Interface references, interface-leaf arrays, marker arrays, covariance, casts, and failures. */
public class TypeRoot {
    static TypeFace staticFace;
    static TypeFace[] staticFaces;

    private static int invoke(TypeFace receiver, int value) {
        return receiver.value(value);
    }

    public static int interfaceInstanceField(int value) {
        TypeHolder holder = new TypeHolder();
        holder.face = new TypeImpl(value);
        return holder.face.value(1);
    }

    public static int interfaceStaticField(int value) {
        staticFace = new TypeImpl(value);
        return staticFace.value(2);
    }

    public static int interfaceArrayInstanceField(int value) {
        TypeHolder holder = new TypeHolder();
        holder.faces = new TypeFace[2];
        holder.faces[1] = new TypeImpl(value);
        return holder.faces[1].value(3);
    }

    public static int interfaceArrayStaticField(int value) {
        staticFaces = new TypeFace[1];
        staticFaces[0] = new TypeImpl(value);
        return staticFaces[0].value(4);
    }

    public static int interfaceArrayDefaults(int value) {
        TypeFace[] values = new TypeFace[2];
        return values[0] == null && values[1] == null ? value : -1;
    }

    public static int interfaceArrayStore(int value) {
        TypeFace[] values = new TypeFace[2];
        values[1] = new TypeOther(value);
        return values[1].value(5);
    }

    public static int childArrayToParentArray(int value) {
        TypeChild[] children = new TypeChild[1];
        TypeFace[] parents = children;
        children[0] = new TypeChild(value);
        return parents[0].value(6);
    }

    public static int interfaceMatrixDefaults(int value) {
        TypeFace[][] values = new TypeFace[2][3];
        return values.length == 2 && values[0].length == 3 && values[1][2] == null ? value : -1;
    }

    public static int interfaceMatrixStore(int value) {
        TypeFace[][] values = new TypeFace[2][2];
        values[1][0] = new TypeImpl(value);
        return values[1][0].value(7);
    }

    public static int interfaceCubePartial(int value) {
        TypeFace[][][] values = new TypeFace[2][1][];
        return values[0] != values[1] && values[0][0] == null && values[1][0] == null ? value : -1;
    }

    public static int objectCastToInterface(int value) {
        Object object = new TypeImpl(value);
        TypeFace face = (TypeFace) object;
        return face.value(8);
    }

    public static int parentCastToChildInterface(int value) {
        TypeFace face = new TypeChild(value);
        TypeSubFace child = (TypeSubFace) face;
        return child.value(9);
    }

    public static int implementingInstanceof(int value) {
        Object object = new TypeImpl(value);
        return object instanceof TypeFace ? value : -1;
    }

    public static int nonImplementingInstanceof(int value) {
        Object object = new TypePlain(value);
        return object instanceof TypeFace ? -1 : value;
    }

    public static int childInterfaceInstanceof(int value) {
        TypeFace face = new TypeChild(value);
        return face instanceof TypeSubFace ? value : -1;
    }

    public static int nullInterfaceCast(int value) {
        Object object = null;
        TypeFace face = (TypeFace) object;
        return face == null ? value : -1;
    }

    public static int nullInterfaceInstanceof(int value) {
        TypeFace face = null;
        return face instanceof TypeFace ? -1 : value;
    }

    public static int intArrayCloneable(int value) {
        Object array = new int[2];
        return array instanceof Cloneable ? value : -1;
    }

    public static int intArraySerializable(int value) {
        Object array = new int[2];
        return array instanceof Serializable ? value : -1;
    }

    public static int objectArrayCloneable(int value) {
        Object array = new Object[2];
        return array instanceof Cloneable ? value : -1;
    }

    public static int objectArraySerializable(int value) {
        Object array = new Object[2];
        return array instanceof Serializable ? value : -1;
    }

    public static int objectArrayNotCloneableArray(int value) {
        Object array = new Object[2];
        return array instanceof Cloneable[] ? -1 : value;
    }

    public static int intMatrixAsCloneableArray(int value) {
        Object array = new int[2][1];
        return array instanceof Cloneable[] ? value : -1;
    }

    public static int intMatrixAsSerializableArray(int value) {
        Object array = new int[2][1];
        return array instanceof Serializable[] ? value : -1;
    }

    public static int interfaceArrayMarkers(int value) {
        Object array = new TypeFace[1];
        return array instanceof Cloneable && array instanceof Serializable ? value : -1;
    }

    public static int markerCastIdentity(int value) {
        int[] array = new int[] { value };
        Cloneable marker = (Cloneable) array;
        return marker == array ? array[0] : -1;
    }

    public static int serializableCastIdentity(int value) {
        TypeFace[] array = new TypeFace[1];
        Serializable marker = (Serializable) array;
        return marker == array ? value : -1;
    }

    public static int nestedMarkerStore(int value) {
        Cloneable[] markers = new Cloneable[2];
        markers[0] = new int[] { value };
        markers[1] = new TypeFace[1];
        return ((int[]) markers[0])[0] + ((TypeFace[]) markers[1]).length;
    }

    public static int interfaceArrayCovariantStoreFailure(int value) {
        TypeFace[] values = new TypeChild[1];
        values[0] = new TypeImpl(value);
        return value;
    }

    public static int nestedInterfaceArrayStoreFailure(int value) {
        Object[] values = new TypeChild[1][];
        values[0] = new TypeImpl[1];
        return value;
    }

    public static int objectToInterfaceCastFailure(int value) {
        Object object = new TypePlain(value);
        return ((TypeFace) object).value(1);
    }

    public static int interfaceSiblingCastFailure(int value) {
        TypeFace face = new TypeImpl(value);
        return ((TypeSubFace) face).value(2);
    }

    public static int nullInterfaceCall(int value) {
        TypeFace face = null;
        return invoke(face, value);
    }

    public static int nullInterfaceArrayLength(int value) {
        TypeFace[] values = null;
        return values.length + value;
    }
}

interface TypeFace {
    int value(int add);
}

interface TypeSubFace extends TypeFace {
}

class TypeImpl implements TypeFace {
    int stored;
    TypeImpl(int stored) { this.stored = stored; }
    public int value(int add) { return stored + add; }
}

class TypeOther implements TypeFace {
    int stored;
    TypeOther(int stored) { this.stored = stored; }
    public int value(int add) { return stored * 2 + add; }
}

class TypeChild extends TypeImpl implements TypeSubFace {
    TypeChild(int stored) { super(stored); }
}

class TypePlain {
    int stored;
    TypePlain(int stored) { this.stored = stored; }
}

class TypeHolder {
    TypeFace face;
    TypeFace[] faces;
}
