package java.util.regex;

import java.io.Serializable;

/**
 * A deliberately bounded Java 8 Pattern profile. It eagerly parses and stores
 * a deterministic token program used only by the matching/replacement subset;
 * it is not a complete java.util.regex implementation.
 */
public final class Pattern implements Serializable {
    private static final int TOKEN_MAGIC = 0x50415431; // "PAT1"
    private static final int OP_END = 0;
    private static final int OP_LITERAL = 1;
    private static final int OP_CLASS = 2;

    public static final int CASE_INSENSITIVE = 2;

    private final String pattern;
    private final int flags;
    private final int[] compiled;

    private Pattern(String regex, int matchFlags, int[] program) {
        super();
        this.pattern = regex;
        this.flags = matchFlags;
        this.compiled = program;
    }

    /** Compiles the supported literal/class grammar, or refuses unsupported syntax. */
    public static Pattern compile(String regex) {
        if (regex == null) {
            throw new NullPointerException();
        }

        int length = regex.length();
        int start = 0;
        int matchFlags = 0;
        if (startsWith(regex, "(?i)")) {
            start = 4;
            matchFlags = CASE_INSENSITIVE;
        } else if (startsWith(regex, "(?")) {
            validateOtherInlineModifier(regex);
            return refuseUnsupported();
        }

        // The program consists of a magic/version word, effective flags,
        // literal and character-class operations, then OP_END.
        int programLength = 3;
        int at = start;
        while (at < length) {
            char value = regex.charAt(at);
            if (value == '[') {
                int[] scanned = scanClass(regex, at, null, 0);
                int pairs = scanned[2];
                if (pairs > (Integer.MAX_VALUE - programLength - 3) / 2) {
                    throw new OutOfMemoryError();
                }
                programLength += 3 + 2 * pairs;
                at = scanned[0];
            } else if (value == '\\') {
                literalValue(regex, at);
                if (programLength > Integer.MAX_VALUE - 2) {
                    throw new OutOfMemoryError();
                }
                programLength += 2;
                at = at + 2;
            } else if (isRegexOperator(value)) {
                return refuseUnsupported();
            } else {
                if (programLength > Integer.MAX_VALUE - 2) {
                    throw new OutOfMemoryError();
                }
                programLength += 2;
                at++;
            }
        }

        int[] program = new int[programLength];
        program[0] = TOKEN_MAGIC;
        program[1] = matchFlags;
        int out = 2;
        at = start;
        while (at < length) {
            char value = regex.charAt(at);
            if (value == '[') {
                int[] scanned = scanClass(regex, at, program, out + 3);
                program[out++] = OP_CLASS;
                program[out++] = scanned[1];
                program[out++] = scanned[2];
                out += 2 * scanned[2];
                at = scanned[0];
            } else {
                int literal = value;
                if (value == '\\') {
                    literal = literalValue(regex, at);
                    at += 2;
                } else {
                    at++;
                }
                program[out++] = OP_LITERAL;
                program[out++] = literal;
            }
        }
        program[out] = OP_END;
        return new Pattern(regex, matchFlags, program);
    }

    /** Creates a bounded Matcher for the admitted literal/class token grammar. */
    public Matcher matcher(CharSequence input) {
        if (input == null) {
            throw new NullPointerException();
        }
        requireBmpMatcherText(input);
        return new Matcher(this, input);
    }

    /**
     * The bounded matcher operates on Java char units. Java 8 Pattern treats
     * supplementary code points specially in classes and several literal
     * paths, so conservatively refuse any surrogate-bearing pattern or input.
     */
    private void requireBmpMatcherText(CharSequence input) {
        int at = 0;
        while (at < pattern.length()) {
            if (isSurrogate(pattern.charAt(at))) {
                unsupportedBranch();
            }
            at++;
        }
        at = 0;
        while (at < input.length()) {
            if (isSurrogate(input.charAt(at))) {
                unsupportedBranch();
            }
            at++;
        }
    }

    private static boolean isSurrogate(char value) {
        return value >= 0xd800 && value <= 0xdfff;
    }

    /**
     * Returns the token-program end at start, or -1 if no token sequence matches.
     * This package helper keeps the compiled array private and immutable to users.
     */
    int matchAt(CharSequence input, int start, int inputLength) {
        if (start < 0 || start > inputLength) {
            return -1;
        }
        int token = 2;
        int cursor = start;
        while (true) {
            int operation = compiled[token++];
            if (operation == OP_END) {
                return cursor;
            }
            if (operation == OP_LITERAL) {
                int expected = compiled[token++];
                if (cursor >= inputLength) {
                    return -1;
                }
                int actual = input.charAt(cursor);
                if (!literalMatches(actual, expected, compiled[1])) {
                    return -1;
                }
                cursor++;
            } else if (operation == OP_CLASS) {
                int negated = compiled[token++];
                int ranges = compiled[token++];
                if (cursor >= inputLength) {
                    return -1;
                }
                int actual = input.charAt(cursor);
                boolean inClass = false;
                int at = token;
                int end = token + ranges * 2;
                while (at < end) {
                    int low = compiled[at++];
                    int high = compiled[at++];
                    if (actual >= low && actual <= high) {
                        inClass = true;
                    }
                    if ((compiled[1] & CASE_INSENSITIVE) != 0
                        && actual >= 'A' && actual <= 'Z'
                        && actual + ('a' - 'A') >= low && actual + ('a' - 'A') <= high) {
                        inClass = true;
                    } else if ((compiled[1] & CASE_INSENSITIVE) != 0
                        && actual >= 'a' && actual <= 'z'
                        && actual - ('a' - 'A') >= low && actual - ('a' - 'A') <= high) {
                        inClass = true;
                    }
                }
                if (negated == 0 ? !inClass : inClass) {
                    return -1;
                }
                token = end;
                cursor++;
            } else {
                // The eagerly compiled program is private and verified; an
                // impossible opcode is a typed profile refusal, not a match.
                return -1;
            }
        }
    }

    private static boolean literalMatches(int actual, int expected, int matchFlags) {
        if (actual == expected) {
            return true;
        }
        if ((matchFlags & CASE_INSENSITIVE) == 0) {
            return false;
        }
        if (actual >= 'A' && actual <= 'Z') {
            actual += 'a' - 'A';
        }
        if (expected >= 'A' && expected <= 'Z') {
            expected += 'a' - 'A';
        }
        return actual == expected;
    }

    /** Returns the exact source expression, including any inline modifier. */
    public String pattern() {
        return pattern;
    }

    /** Returns the effective supported match flags (currently ASCII CASE_INSENSITIVE). */
    public int flags() {
        return flags;
    }

    @Override
    public String toString() {
        return pattern;
    }

    private static boolean startsWith(String value, String prefix) {
        if (value.length() < prefix.length()) {
            return false;
        }
        int i = 0;
        while (i < prefix.length()) {
            if (value.charAt(i) != prefix.charAt(i)) {
                return false;
            }
            i++;
        }
        return true;
    }

    private static boolean isRegexOperator(char value) {
        return value == '.' || value == '^' || value == '$' || value == '|'
            || value == '?' || value == '*' || value == '+' || value == '('
            || value == ')' || value == '{' || value == '}';
    }

    private static boolean isAsciiAlphaNumeric(char value) {
        return (value >= 'a' && value <= 'z') || (value >= 'A' && value <= 'Z')
            || (value >= '0' && value <= '9');
    }

    /** A backslash may quote punctuation in this grammar; regex letter escapes are outside it. */
    private static int literalValue(String regex, int slash) {
        if (slash + 1 >= regex.length()) {
            throw syntax("Trailing backslash", regex, slash);
        }
        char escaped = regex.charAt(slash + 1);
        if (isAsciiAlphaNumeric(escaped)) {
            refuseUnsupported();
            throw new IllegalArgumentException();
        }
        return escaped;
    }

    /**
     * Scans one class. Result is {first index after ']', negated, range count}.
     * If output is non-null, decoded inclusive low/high UTF-16 ranges are written
     * starting at outputAt. Class intersection and nested classes are valid but
     * outside this implementation's grammar and are atomically refused.
     */
    private static int[] scanClass(String regex, int open, int[] output, int outputAt) {
        int length = regex.length();
        int at = open + 1;
        int negated = 0;
        if (at < length && regex.charAt(at) == '^') {
            negated = 1;
            at++;
        }
        if (at < length && regex.charAt(at) == ']') {
            if (at + 1 < length && regex.charAt(at + 1) == ']') {
                refuseUnsupported();
                throw new IllegalArgumentException();
            }
            throw syntax("Unclosed character class", regex, at);
        }

        int ranges = 0;
        while (at < length) {
            char value = regex.charAt(at);
            if (value == ']') {
                if (ranges == 0) {
                    throw syntax("Unclosed character class", regex, at);
                }
                return new int[] { at + 1, negated, ranges };
            }
            if (value == '[' || (value == '&' && at + 1 < length && regex.charAt(at + 1) == '&')) {
                refuseUnsupported();
                throw new IllegalArgumentException();
            }

            int low = classLiteralValue(regex, at);
            int afterLow = at + (value == '\\' ? 2 : 1);
            int high = low;
            int afterItem = afterLow;
            if (afterLow < length && regex.charAt(afterLow) == '-'
                && afterLow + 1 < length && regex.charAt(afterLow + 1) != ']') {
                int highAt = afterLow + 1;
                if (regex.charAt(highAt) == '['
                    || (regex.charAt(highAt) == '&' && highAt + 1 < length
                        && regex.charAt(highAt + 1) == '&')) {
                    refuseUnsupported();
                    throw new IllegalArgumentException();
                }
                if (regex.charAt(highAt) == '\\' && highAt + 1 < length
                    && isAsciiAlphaNumeric(regex.charAt(highAt + 1))) {
                    throw syntax("Illegal character range", regex, highAt + 1);
                }
                high = classLiteralValue(regex, highAt);
                afterItem = highAt + (regex.charAt(highAt) == '\\' ? 2 : 1);
                if (low > high) {
                    throw syntax("Illegal character range", regex, highAt);
                }
            }
            if (output != null) {
                output[outputAt + ranges * 2] = low;
                output[outputAt + ranges * 2 + 1] = high;
            }
            ranges++;
            at = afterItem;
        }
        throw syntax("Unclosed character class", regex, length == open + 1 ? open + 1 : length);
    }

    private static int classLiteralValue(String regex, int at) {
        if (regex.charAt(at) == '\\') {
            return literalValue(regex, at);
        }
        return regex.charAt(at);
    }

    private static void validateOtherInlineModifier(String regex) {
        int length = regex.length();
        int at = 2;
        if (at < length) {
            char group = regex.charAt(at);
            if (group == ':' || group == '=' || group == '!' || group == '<'
                || group == '>' || group == '#') {
                return;
            }
        }
        boolean sawFlag = false;
        boolean sawMinus = false;
        while (at < length) {
            char value = regex.charAt(at);
            if (value == ')' || value == ':') {
                if (!sawFlag) {
                    throw syntax("Unknown inline modifier", regex, at);
                }
                return;
            }
            if (value == '-') {
                if (sawMinus) {
                    throw syntax("Unknown inline modifier", regex, at);
                }
                sawMinus = true;
            } else if (value == 'i' || value == 'd' || value == 'm' || value == 's'
                || value == 'u' || value == 'x' || value == 'U') {
                sawFlag = true;
            } else {
                throw syntax("Unknown inline modifier", regex, at);
            }
            at++;
        }
        throw syntax("Unknown inline modifier", regex, length);
    }

    private static PatternSyntaxException syntax(String description, String regex, int index) {
        return new PatternSyntaxException(description, regex, index);
    }

    private static Pattern refuseUnsupported() {
        unsupportedBranch();
        throw new IllegalArgumentException();
    }

    /** No interpreter binding exists; this private branch is an atomic profile refusal. */
    private static native void unsupportedBranch();
}
