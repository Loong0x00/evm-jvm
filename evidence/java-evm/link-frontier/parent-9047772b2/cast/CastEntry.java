// Generated-only independent cast probe. No method call follows the cast.
public final class CastEntry {
    public static int run(int mode) {
        Object value = mode == 0 ? null : new Object();
        MissingTarget target = (MissingTarget)value;
        return target == null ? 61 : 62;
    }
}
