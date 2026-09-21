package java.lang;
public final class StackTraceElement {
    private final String declaringClass;
    private final String methodName;
    private StackTraceElement(String declaringClass, String methodName) {
        this.declaringClass = declaringClass;
        this.methodName = methodName;
    }
    public String getClassName() { return declaringClass; }
    public String getMethodName() { return methodName; }
    public boolean isNativeMethod() { return false; }
}
