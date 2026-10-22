package java.util.regex;

/**
 * Minimal Java 8 Matcher profile for Pattern.replaceAll: it implements only
 * replaceAll over Pattern's admitted fixed-width literal/class token program.
 * It is not a complete Matcher or MatchResult implementation.
 */
public final class Matcher {
    private final Pattern parentPattern;
    private final CharSequence text;

    Matcher(Pattern pattern, CharSequence input) {
        super();
        if (pattern == null || input == null) {
            throw new NullPointerException();
        }
        this.parentPattern = pattern;
        this.text = input;
    }

    /** Returns true only when the bounded program consumes the entire input region. */
    public boolean matches() {
        parentPattern.requireBmpMatcherText(text);
        int length = text.length();
        int end = parentPattern.matchAt(text, 0, length);
        return end == length;
    }

    /** Performs Java's leftmost, non-overlapping replaceAll operation. */
    public String replaceAll(String replacement) {
        parentPattern.requireBmpMatcherText(text);
        int inputLength = text.length();
        int appendPosition = 0;
        int searchPosition = 0;
        boolean previousMatchWasEmpty = false;
        StringBuilder output = null;

        while (searchPosition <= inputLength) {
            if (previousMatchWasEmpty) {
                searchPosition++;
                previousMatchWasEmpty = false;
            }
            if (searchPosition > inputLength) {
                break;
            }

            int matchStart = searchPosition;
            int matchEnd = -1;
            while (matchStart <= inputLength) {
                matchEnd = parentPattern.matchAt(text, matchStart, inputLength);
                if (matchEnd >= 0) {
                    break;
                }
                matchStart++;
            }
            if (matchEnd < 0) {
                break;
            }

            if (output == null) {
                output = new StringBuilder();
            }
            appendInput(output, appendPosition, matchStart);
            appendReplacement(output, replacement, matchStart, matchEnd);
            appendPosition = matchEnd;
            searchPosition = matchEnd;
            previousMatchWasEmpty = matchStart == matchEnd;
        }

        if (output == null) {
            return text.toString();
        }
        appendInput(output, appendPosition, inputLength);
        return output.toString();
    }

    private void appendInput(StringBuilder output, int begin, int end) {
        int at = begin;
        while (at < end) {
            output.append(text.charAt(at));
            at++;
        }
    }

    /** Expands literal replacement text, escapes, and the supported $0 group. */
    private void appendReplacement(StringBuilder output, String replacement,
                                   int matchStart, int matchEnd) {
        if (replacement == null) {
            throw new NullPointerException();
        }
        int length = replacement.length();
        int at = 0;
        while (at < length) {
            char value = replacement.charAt(at);
            if (value == '\\') {
                at++;
                if (at >= length) {
                    throw new IllegalArgumentException();
                }
                output.append(replacement.charAt(at));
                at++;
            } else if (value == '$') {
                at++;
                if (at >= length) {
                    throw new IllegalArgumentException();
                }
                char first = replacement.charAt(at);
                if (first == '{') {
                    // This Pattern grammar has no capturing or named groups.
                    // Keep Java's replacement exception category and never
                    // publish a fabricated expansion for an unknown group.
                    throw new IllegalArgumentException();
                }
                int group = first - '0';
                if (group < 0 || group > 9) {
                    throw new IllegalArgumentException();
                }
                at++;
                if (group != 0) {
                    throw new IndexOutOfBoundsException();
                }
                // With groupCount()==0 Java greedily accepts only subsequent
                // digits that keep the reference equal to group zero. Thus
                // $00 is group zero and $01 is group zero followed by '1'.
                while (at < length) {
                    int digit = replacement.charAt(at) - '0';
                    if (digit < 0 || digit > 9 || digit != 0) {
                        break;
                    }
                    at++;
                }
                int groupAt = matchStart;
                while (groupAt < matchEnd) {
                    output.append(text.charAt(groupAt));
                    groupAt++;
                }
            } else {
                output.append(value);
                at++;
            }
        }
    }
}
