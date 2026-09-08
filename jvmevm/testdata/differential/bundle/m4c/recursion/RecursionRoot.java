package bundle.m4c.recursion;

/** Bounded recursive virtual calls with inherited code and dynamic hooks. */
public class RecursionRoot {
    public static int baseRecursive(int n) {
        return new RecursiveBase().sum(n);
    }

    public static int childRecursive(int n) {
        RecursiveBase receiver = new RecursiveChild();
        return receiver.sum(n);
    }

    public static int grandRecursive(int n) {
        RecursiveBase receiver = new RecursiveGrand();
        return receiver.sum(n);
    }

    public static int alternatingBounce(int n) {
        RecursiveBase base = new RecursiveBase();
        RecursiveBase child = new RecursiveChild();
        return base.bounce(child, n);
    }

    public static int reverseBounce(int n) {
        RecursiveBase base = new RecursiveBase();
        RecursiveBase child = new RecursiveChild();
        return child.bounce(base, n);
    }

    public static int recursiveReferenceReturn(int n) {
        RecursiveBase base = new RecursiveBase();
        RecursiveBase child = new RecursiveChild();
        return base.choose(child, n).weight();
    }
}

class RecursiveBase {
    int weight() { return 1; }

    int sum(int n) {
        if (n == 0) return weight();
        return weight() + sum(n - 1);
    }

    int bounce(RecursiveBase other, int n) {
        if (n == 0) return weight();
        return other.bounce(this, n - 1) + weight();
    }

    RecursiveBase choose(RecursiveBase other, int n) {
        if (n == 0) return this;
        return other.choose(this, n - 1);
    }
}

class RecursiveChild extends RecursiveBase {
    int weight() { return 5; }
}

class RecursiveGrand extends RecursiveChild {
    int weight() { return 9; }
}
