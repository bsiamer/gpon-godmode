package com.gpon.godmode.json;

import java.util.*;

/**
 * Zero-dependency, lightweight JSON tokenizer, parser and serializer.
 * Fully compatible with standard JSON specifications (RFC 8259).
 */
public final class SimpleJson {

    private SimpleJson() {}

    /**
     * Parses arbitrary JSON text into a JsonObject, JsonArray, String, Number, Boolean, or null.
     */
    public static Object parse(String json) {
        if (json == null) return null;
        Parser parser = new Parser(json);
        Object result = parser.parseValue();
        parser.skipWhitespace();
        if (parser.hasMore()) {
            // Ignore trailing whitespace/newlines; if non-whitespace remaining, throw or ignore
        }
        return result;
    }

    /**
     * Parses JSON string into a JsonObject.
     */
    public static JsonObject parseObject(String json) {
        Object val = parse(json);
        if (val instanceof JsonObject) {
            return (JsonObject) val;
        }
        if (val instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> map = (Map<String, Object>) val;
            return new JsonObject(map);
        }
        throw new IllegalArgumentException("Expected JSON object but got: " + (val == null ? "null" : val.getClass().getSimpleName()));
    }

    /**
     * Parses JSON string into a JsonArray.
     */
    public static JsonArray parseArray(String json) {
        Object val = parse(json);
        if (val instanceof JsonArray) {
            return (JsonArray) val;
        }
        if (val instanceof List) {
            @SuppressWarnings("unchecked")
            List<Object> list = (List<Object>) val;
            return new JsonArray(list);
        }
        throw new IllegalArgumentException("Expected JSON array but got: " + (val == null ? "null" : val.getClass().getSimpleName()));
    }

    /**
     * Serializes any supported Java object to JSON string.
     */
    public static String stringify(Object value) {
        StringBuilder sb = new StringBuilder();
        writeValue(sb, value);
        return sb.toString();
    }

    private static void writeValue(StringBuilder sb, Object value) {
        if (value == null) {
            sb.append("null");
        } else if (value instanceof String) {
            writeString(sb, (String) value);
        } else if (value instanceof Number || value instanceof Boolean) {
            sb.append(value);
        } else if (value instanceof JsonObject) {
            writeMap(sb, ((JsonObject) value).asMap());
        } else if (value instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> map = (Map<String, Object>) value;
            writeMap(sb, map);
        } else if (value instanceof JsonArray) {
            writeCollection(sb, ((JsonArray) value).asList());
        } else if (value instanceof Collection) {
            writeCollection(sb, (Collection<?>) value);
        } else if (value.getClass().isArray()) {
            writeArray(sb, value);
        } else {
            // Fallback: serialize as string or POJO toString
            writeString(sb, value.toString());
        }
    }

    private static void writeString(StringBuilder sb, String str) {
        sb.append('"');
        for (int i = 0; i < str.length(); i++) {
            char c = str.charAt(i);
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\b': sb.append("\\b"); break;
                case '\f': sb.append("\\f"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 32 || c >= 127 && c <= 159) {
                        sb.append(String.format("\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        sb.append('"');
    }

    private static void writeMap(StringBuilder sb, Map<?, ?> map) {
        sb.append('{');
        boolean first = true;
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            if (!first) sb.append(',');
            first = false;
            writeString(sb, String.valueOf(entry.getKey()));
            sb.append(':');
            writeValue(sb, entry.getValue());
        }
        sb.append('}');
    }

    private static void writeCollection(StringBuilder sb, Collection<?> col) {
        sb.append('[');
        boolean first = true;
        for (Object item : col) {
            if (!first) sb.append(',');
            first = false;
            writeValue(sb, item);
        }
        sb.append(']');
    }

    private static void writeArray(StringBuilder sb, Object array) {
        sb.append('[');
        int length = java.lang.reflect.Array.getLength(array);
        for (int i = 0; i < length; i++) {
            if (i > 0) sb.append(',');
            writeValue(sb, java.lang.reflect.Array.get(array, i));
        }
        sb.append(']');
    }

    // -------------------------------------------------------------
    // Recursive-descent parser implementation
    // -------------------------------------------------------------

    private static final class Parser {
        private final String src;
        private final int len;
        private int pos = 0;

        Parser(String src) {
            this.src = src;
            this.len = src.length();
        }

        boolean hasMore() {
            return pos < len;
        }

        char peek() {
            return pos < len ? src.charAt(pos) : '\0';
        }

        char next() {
            return pos < len ? src.charAt(pos++) : '\0';
        }

        void skipWhitespace() {
            while (pos < len) {
                char c = src.charAt(pos);
                if (c == ' ' || c == '\t' || c == '\r' || c == '\n') {
                    pos++;
                } else {
                    break;
                }
            }
        }

        Object parseValue() {
            skipWhitespace();
            if (!hasMore()) return null;

            char c = peek();
            if (c == '{') return parseObject();
            if (c == '[') return parseArray();
            if (c == '"') return parseString();
            if (c == 't' || c == 'f') return parseBoolean();
            if (c == 'n') return parseNull();
            if (c == '-' || (c >= '0' && c <= '9')) return parseNumber();

            throw new IllegalArgumentException("Unexpected character '" + c + "' at position " + pos);
        }

        JsonObject parseObject() {
            next(); // consume '{'
            JsonObject obj = new JsonObject();
            skipWhitespace();

            if (peek() == '}') {
                next(); // empty object
                return obj;
            }

            while (hasMore()) {
                skipWhitespace();
                if (peek() != '"') {
                    throw new IllegalArgumentException("Expected string key in object at position " + pos);
                }
                String key = parseString();
                skipWhitespace();
                if (next() != ':') {
                    throw new IllegalArgumentException("Expected ':' after key at position " + pos);
                }
                Object value = parseValue();
                obj.put(key, value);

                skipWhitespace();
                char c = next();
                if (c == '}') {
                    return obj;
                } else if (c == ',') {
                    skipWhitespace();
                    if (peek() == '}') { // allow trailing comma
                        next();
                        return obj;
                    }
                } else {
                    throw new IllegalArgumentException("Expected ',' or '}' in object at position " + pos);
                }
            }
            throw new IllegalArgumentException("Unterminated object at position " + pos);
        }

        JsonArray parseArray() {
            next(); // consume '['
            JsonArray arr = new JsonArray();
            skipWhitespace();

            if (peek() == ']') {
                next(); // empty array
                return arr;
            }

            while (hasMore()) {
                Object value = parseValue();
                arr.add(value);
                skipWhitespace();
                char c = next();
                if (c == ']') {
                    return arr;
                } else if (c == ',') {
                    skipWhitespace();
                    if (peek() == ']') { // allow trailing comma
                        next();
                        return arr;
                    }
                } else {
                    throw new IllegalArgumentException("Expected ',' or ']' in array at position " + pos);
                }
            }
            throw new IllegalArgumentException("Unterminated array at position " + pos);
        }

        String parseString() {
            next(); // consume opening '"'
            StringBuilder sb = new StringBuilder();
            while (hasMore()) {
                char c = next();
                if (c == '"') {
                    return sb.toString();
                } else if (c == '\\') {
                    if (!hasMore()) break;
                    char esc = next();
                    switch (esc) {
                        case '"': sb.append('"'); break;
                        case '\\': sb.append('\\'); break;
                        case '/': sb.append('/'); break;
                        case 'b': sb.append('\b'); break;
                        case 'f': sb.append('\f'); break;
                        case 'n': sb.append('\n'); break;
                        case 'r': sb.append('\r'); break;
                        case 't': sb.append('\t'); break;
                        case 'u':
                            if (pos + 4 <= len) {
                                String hex = src.substring(pos, pos + 4);
                                pos += 4;
                                try {
                                    sb.append((char) Integer.parseInt(hex, 16));
                                } catch (NumberFormatException e) {
                                    sb.append('?');
                                }
                            }
                            break;
                        default:
                            sb.append(esc);
                    }
                } else {
                    sb.append(c);
                }
            }
            throw new IllegalArgumentException("Unterminated string at position " + pos);
        }

        Boolean parseBoolean() {
            if (src.startsWith("true", pos)) {
                pos += 4;
                return Boolean.TRUE;
            } else if (src.startsWith("false", pos)) {
                pos += 5;
                return Boolean.FALSE;
            }
            throw new IllegalArgumentException("Invalid boolean literal at position " + pos);
        }

        Object parseNull() {
            if (src.startsWith("null", pos)) {
                pos += 4;
                return null;
            }
            throw new IllegalArgumentException("Invalid null literal at position " + pos);
        }

        Number parseNumber() {
            int start = pos;
            if (peek() == '-') next();
            while (hasMore() && Character.isDigit(peek())) next();

            boolean isFloating = false;
            if (hasMore() && peek() == '.') {
                isFloating = true;
                next();
                while (hasMore() && Character.isDigit(peek())) next();
            }
            if (hasMore() && (peek() == 'e' || peek() == 'E')) {
                isFloating = true;
                next();
                if (hasMore() && (peek() == '+' || peek() == '-')) next();
                while (hasMore() && Character.isDigit(peek())) next();
            }

            String numStr = src.substring(start, pos);
            try {
                if (isFloating) {
                    return Double.parseDouble(numStr);
                }
                long l = Long.parseLong(numStr);
                if (l >= Integer.MIN_VALUE && l <= Integer.MAX_VALUE) {
                    return (int) l;
                }
                return l;
            } catch (NumberFormatException e) {
                throw new IllegalArgumentException("Invalid number '" + numStr + "' at position " + start);
            }
        }
    }
}
