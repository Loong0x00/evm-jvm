package bundle.m4c.types;

/** Ordinary-class, Object, and int[] checkcast/instanceof fixtures. */
public class TypeRoot {
    public static int instanceDogTrue(int yes) {
        Object value = new TypeDog();
        return value instanceof TypeDog ? yes : -1;
    }

    public static int instanceAnimalTrue(int yes) {
        Object value = new TypeDog();
        return value instanceof TypeAnimal ? yes : -1;
    }

    public static int instanceCatFalse(int yes) {
        Object value = new TypeDog();
        return value instanceof TypeCat ? -1 : yes;
    }

    public static int instanceObjectFromClass(int yes) {
        Object value = new TypeDog();
        return value instanceof Object ? yes : -1;
    }

    public static int instanceArrayTrue(int yes) {
        Object value = new int[2];
        return value instanceof int[] ? yes : -1;
    }

    public static int instanceObjectFromArray(int yes) {
        Object value = new int[2];
        return value instanceof Object ? yes : -1;
    }

    public static int instanceArrayFalseForObject(int yes) {
        Object value = new TypeDog();
        return value instanceof int[] ? -1 : yes;
    }

    public static int instanceClassFalseForArray(int yes) {
        Object value = new int[1];
        return value instanceof TypeAnimal ? -1 : yes;
    }

    public static int instanceNullClass(int yes) {
        Object value = null;
        return value instanceof TypeAnimal ? -1 : yes;
    }

    public static int instanceNullArray(int yes) {
        Object value = null;
        return value instanceof int[] ? -1 : yes;
    }

    public static int castDogIdentity(int yes) {
        TypeDog dog = new TypeDog();
        Object value = dog;
        TypeDog result = (TypeDog) value;
        return result == dog ? yes : -1;
    }

    public static int castAnimalIdentity(int yes) {
        TypeDog dog = new TypeDog();
        Object value = dog;
        TypeAnimal result = (TypeAnimal) value;
        return result == dog ? yes : -1;
    }

    public static int castArrayIdentity(int value) {
        int[] array = new int[1];
        Object object = array;
        int[] result = (int[]) object;
        result[0] = value;
        return array[0];
    }

    public static int castNullClass(int yes) {
        Object value = null;
        TypeDog result = (TypeDog) value;
        return result == null ? yes : -1;
    }

    public static int castNullArray(int yes) {
        Object value = null;
        int[] result = (int[]) value;
        return result == null ? yes : -1;
    }

    public static int castSiblingFails(int value) {
        Object object = new TypeCat();
        TypeDog dog = (TypeDog) object;
        return dog.value + value;
    }

    public static int castObjectToArrayFails(int value) {
        Object object = new TypeDog();
        int[] array = (int[]) object;
        return array[0] + value;
    }

    public static int castArrayToClassFails(int value) {
        Object object = new int[1];
        TypeAnimal animal = (TypeAnimal) object;
        return animal.value + value;
    }

    public static int initializerCastFails(int value) {
        return FailingCastHolder.DOG.value + value;
    }

    public static int castThenVirtual(int value) {
        Object object = new TypeDog();
        TypeAnimal animal = (TypeAnimal) object;
        return animal.virtualValue(value);
    }
}

class TypeAnimal {
    int value;
    int virtualValue(int add) { return value + add + 1; }
}

class TypeDog extends TypeAnimal {
    int virtualValue(int add) { return value + add + 10; }
}

class TypeCat extends TypeAnimal {
}

class FailingCastHolder {
    static TypeDog DOG = (TypeDog) (Object) new TypeCat();
}
