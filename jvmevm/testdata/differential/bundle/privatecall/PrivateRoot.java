package bundle.privatecall;

public class PrivateRoot {
    private static int privateLeaf(int value) {
        return value * 13 + 5;
    }

    private static int privateNested(int value) {
        return privateLeaf(value - 2) * 3;
    }

    public static int sameClassPrivate(int value) {
        return privateLeaf(value);
    }

    public static int privateThenExternal(int value) {
        return PrivatePartner.external(privateLeaf(value));
    }

    public static int externalThenPrivate(int value) {
        return privateLeaf(PrivatePartner.external(value));
    }

    public static int nestedPrivateInBundle(int value) {
        return privateNested(value) + PrivatePartner.external(value);
    }

    public static int crossVoidThenPrivate(int value) {
        PrivatePartner.consume(value);
        return privateLeaf(value + 1);
    }
}
