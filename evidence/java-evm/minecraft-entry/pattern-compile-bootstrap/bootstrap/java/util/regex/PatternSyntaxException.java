package java.util.regex;

/** Guest Java 8 syntax exception used by Pattern.compile(String). */
public class PatternSyntaxException extends IllegalArgumentException {
    private static final long serialVersionUID = -3864639126226059218L;

    private final String desc;
    private final String pattern;
    private final int index;

    public PatternSyntaxException(String description, String regex, int errorIndex) {
        super();
        this.desc = description;
        this.pattern = regex;
        this.index = errorIndex;
    }

    public int getIndex() {
        return index;
    }

    public String getDescription() {
        return desc;
    }

    public String getPattern() {
        return pattern;
    }

    @Override
    public String getMessage() {
        StringBuilder message = new StringBuilder();
        message.append(desc);
        if (index >= 0) {
            message.append(" near index ");
            message.append(index);
        }
        message.append('\n');
        message.append(pattern);
        if (index >= 0) {
            message.append('\n');
            int i = 0;
            while (i < index) {
                message.append(' ');
                i++;
            }
            message.append('^');
        }
        return message.toString();
    }
}
