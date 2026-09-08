package bundle.m4fb.initorder;

/** Interface initialization is observed only through ordinary helper state. */
public class InitRoot {
    public static int superclassInterfaceClassOrder(int value) { new InitOrderedChild(); return InitProbe.trace * 10 + value; }
    public static int superclassOrderRepeat(int value) { new InitOrderedChild(); new InitOrderedChild(); return InitProbe.trace * 10 + value; }
    public static int parentBeforeChildInterface(int value) { new InitSimpleImpl(); return InitProbe.trace * 10 + value; }
    public static int declaredInterfaceOrder(int value) { new InitOrderedInterfaces(); return InitProbe.trace * 10 + value; }
    public static int diamondDeduplicatesParent(int value) { new InitDiamondImpl(); return InitProbe.trace * 10 + value; }
    public static int diamondRepeatAllocation(int value) { new InitDiamondImpl(); new InitDiamondImpl(); return InitProbe.trace * 10 + value; }
    public static int inheritedNonDeclarerOmitted(int value) { new InitInheritedImpl(); return InitProbe.trace * 10 + value; }
    public static int abstractOnlyOmitted(int value) { new InitAbstractImpl(); return InitProbe.trace * 10 + value; }
    public static int reabstractingInterfaceOmitted(int value) { new InitReabstractImpl(); return InitProbe.trace * 10 + value; }
    public static int classWinStillInitializesDefault(int value) { new InitClassWin(); return InitProbe.trace * 10 + value; }
    public static int superclassWinStillInitializesDefault(int value) { new InitSuperWin(); return InitProbe.trace * 10 + value; }
    public static int syntheticBridgeQualifies(int value) { new InitBridgeImpl(); return InitProbe.trace * 10 + value; }
    public static int syntheticBridgeInvocation(int value) {
        InitBridgeSource receiver = new InitBridgeImpl(); return receiver.make().value + InitProbe.trace * 10 + value;
    }
    public static int reentrantClassDuringInterfaceInit(int value) { new InitReentrantClass(); return InitProbe.trace * 100 + InitProbe.seen * 10 + value; }
    public static int reentrantRepeat(int value) { new InitReentrantClass(); new InitReentrantClass(); return InitProbe.trace * 100 + InitProbe.seen * 10 + value; }
    public static int constructorAfterPrerequisites(int value) { return new InitCtor(value).value + InitProbe.trace * 100; }
    public static int defaultCallAfterInitialization(int value) { InitSimple receiver = new InitSimpleImpl(); return receiver.run(value) + InitProbe.trace * 100; }
    public static int inheritedDefaultCall(int value) { InitInherited receiver = new InitInheritedImpl(); return receiver.run(value) + InitProbe.trace * 100; }
    public static int classWinDispatchAfterInit(int value) { InitClassFace receiver = new InitClassWin(); return receiver.run(value) + InitProbe.trace * 100; }
    public static int reabstractClassDispatch(int value) { InitReabstract receiver = new InitReabstractImpl(); return receiver.run(value) + InitProbe.trace * 100; }
    public static int twoIndependentDefaults(int value) { new InitTwoIndependent(); return InitProbe.trace * 10 + value; }
    public static int parentClassOwnInterfacesOnlyOnce(int value) { new InitParentChild(); return InitProbe.trace * 10 + value; }
    public static int unusedDefaultMetadata(int value) { return InitProbe.trace + value; }
    public static int allocationInitializesBeforeUse(int value) {
        InitSimpleImpl receiver = new InitSimpleImpl(); return InitProbe.trace * 100 + receiver.run(value);
    }
    public static int interfaceCastDoesNotReinitialize(int value) {
        Object object = new InitSimpleImpl(); InitSimple receiver = (InitSimple) object;
        return InitProbe.trace * 100 + receiver.run(value);
    }
}

class InitProbe {
    static int trace;
    static int seen;
    static int mark(int digit) { trace = trace * 10 + digit; return trace; }
    static int reenter() { mark(6); seen = InitReentrantClass.observe(); return seen; }
}
interface InitSuperFace { int TOKEN = InitProbe.mark(1); default int run(int value) { return value + 1; } }
class InitOrderedBase implements InitSuperFace { static int TOKEN = InitProbe.mark(2); }
interface InitChildFace { int TOKEN = InitProbe.mark(3); default int child(int value) { return value + 3; } }
class InitOrderedChild extends InitOrderedBase implements InitChildFace { static int TOKEN = InitProbe.mark(4); }

interface InitSimpleParent { int TOKEN = InitProbe.mark(1); default int parent(int value) { return value + 1; } }
interface InitSimple extends InitSimpleParent { int TOKEN = InitProbe.mark(2); default int run(int value) { return value + 2; } }
class InitSimpleImpl implements InitSimple { static int TOKEN = InitProbe.mark(3); }

interface InitFirst { int TOKEN = InitProbe.mark(1); default int first() { return 1; } }
interface InitSecond { int TOKEN = InitProbe.mark(2); default int second() { return 2; } }
class InitOrderedInterfaces implements InitFirst, InitSecond { static int TOKEN = InitProbe.mark(3); }

interface InitDiamondParent { int TOKEN = InitProbe.mark(1); default int run(int value) { return value; } }
interface InitDiamondLeft extends InitDiamondParent { int TOKEN = InitProbe.mark(2); default int left() { return 2; } }
interface InitDiamondRight extends InitDiamondParent { int TOKEN = InitProbe.mark(3); default int right() { return 3; } }
interface InitDiamondLeaf extends InitDiamondLeft, InitDiamondRight { int TOKEN = InitProbe.mark(4); default int leaf() { return 4; } }
class InitDiamondImpl implements InitDiamondLeaf { static int TOKEN = InitProbe.mark(5); }

interface InitDeclaring { int TOKEN = InitProbe.mark(1); default int run(int value) { return value + 1; } }
interface InitInherited extends InitDeclaring { int SHOULD_NOT_RUN = InitProbe.mark(2); }
class InitInheritedImpl implements InitInherited { static int TOKEN = InitProbe.mark(3); }

interface InitAbstractOnly { int SHOULD_NOT_RUN = InitProbe.mark(8); int run(int value); }
class InitAbstractImpl implements InitAbstractOnly { static int TOKEN = InitProbe.mark(3); public int run(int value) { return value; } }

interface InitReabstractParent { int TOKEN = InitProbe.mark(1); default int run(int value) { return value + 1; } }
interface InitReabstract extends InitReabstractParent { int SHOULD_NOT_RUN = InitProbe.mark(2); int run(int value); }
class InitReabstractImpl implements InitReabstract { static int TOKEN = InitProbe.mark(3); public int run(int value) { return value + 3; } }

interface InitClassFace { int TOKEN = InitProbe.mark(1); default int run(int value) { return value + 1; } }
class InitClassWin implements InitClassFace { static int TOKEN = InitProbe.mark(2); public int run(int value) { return value + 4; } }
class InitWinningBase { public int run(int value) { return value + 5; } }
class InitSuperWin extends InitWinningBase implements InitClassFace { static int TOKEN = InitProbe.mark(2); }

class InitToken { int value; InitToken(int value) { this.value = value; } }
interface InitBridgeParent<T> { T make(); }
interface InitBridgeSource extends InitBridgeParent<InitToken> {
    int TOKEN = InitProbe.mark(4);
    InitToken make();
}
class InitBridgeImpl implements InitBridgeSource {
    static int TOKEN = InitProbe.mark(5);
    public InitToken make() { return new InitToken(7); }
}

interface InitReentrantFace { int TOKEN = InitProbe.reenter(); default int run(int value) { return value + 1; } }
class InitReentrantClass implements InitReentrantFace {
    static int TOKEN = InitProbe.mark(7);
    static int observe() { return InitProbe.trace; }
}
interface InitCtorFace { int TOKEN = InitProbe.mark(1); default int run(int value) { return value; } }
class InitCtor implements InitCtorFace {
    static int TOKEN = InitProbe.mark(2);
    int value;
    InitCtor(int value) { this.value = value + InitProbe.trace; }
}
interface InitIndependentA { int TOKEN = InitProbe.mark(1); default int a() { return 1; } }
interface InitIndependentB { int TOKEN = InitProbe.mark(2); default int b() { return 2; } }
class InitTwoIndependent implements InitIndependentA, InitIndependentB { static int TOKEN = InitProbe.mark(3); }
interface InitParentOwnedFace { int TOKEN = InitProbe.mark(1); default int run(int value) { return value; } }
class InitParentClass implements InitParentOwnedFace { static int TOKEN = InitProbe.mark(2); }
interface InitChildOwnedFace { int TOKEN = InitProbe.mark(3); default int child(int value) { return value; } }
class InitParentChild extends InitParentClass implements InitParentOwnedFace, InitChildOwnedFace { static int TOKEN = InitProbe.mark(4); }
interface InitUnusedFace { int TOKEN = InitProbe.mark(9); default int run(int value) { return value; } }
class InitUnusedImpl implements InitUnusedFace {}
