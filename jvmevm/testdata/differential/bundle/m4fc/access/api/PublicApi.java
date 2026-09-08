package bundle.m4fc.access.api;

/** Public qualifier exposes a public field declared by its package-private parent interface. */
public interface PublicApi extends HiddenApi {
    int OWN = ApiState.mark(2, 20);
    static int call(int value) { return value + 30; }
    static int inheritedField(int value) { return PublicApi.HIDDEN + value; }
    static int ownField(int value) { return OWN + value; }
    static ApiBox make(int value) { return new ApiBox(value + 40); }
}

interface HiddenApi { int HIDDEN = ApiState.mark(1, 10); }
class ApiState { static int trace; static int mark(int digit, int value) { trace = trace * 10 + digit; return value; } }
