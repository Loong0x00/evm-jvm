package java.util;

/**
 * Bounded, EVM-owned EnumSet subset.
 *
 * The measured unchanged path needs exactly two behaviours: the static
 * {@code allOf(Class)} factory used by an enum's own {@code <clinit>} and the
 * {@code Iterator} handed out by {@code iterator()} on the resulting set.  The
 * universe itself is never fabricated here: {@code universe0} is an
 * interpreter-owned primitive which reads the static {@code ACC_ENUM} fields of
 * the named guest class after genuine guest initialization, in declaration
 * (ordinal) order.
 *
 * Storage and iteration are inherited from the bounded HashSet image already
 * accepted in this profile, so one append-only image covers both the set and
 * its iterator without inventing a second iterator implementation.  HashSet is
 * insertion-ordered and the set is built once by allOf and never mutated
 * afterwards, so the iterator observes a fixed snapshot.  The erased
 * descriptors declared here are exactly the ones reached by the measured host
 * Java 8 call sites; generic signatures are deliberately absent from this
 * bounded image and add no runtime behaviour.
 */
public class EnumSet extends HashSet {
    EnumSet(Object[] universe) {
        for (int i = 0; i < universe.length; ++i) {
            add(universe[i]);
        }
    }

    public static EnumSet allOf(Class elementType) {
        return new EnumSet(universe0(elementType));
    }

    private static native Object[] universe0(Class elementType);
}
