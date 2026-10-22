package java.util.function;
/** Minimal Java 8 functional interface profile: only the abstract SAM is linked. */
public interface Function<T, R> { R apply(T value); }
