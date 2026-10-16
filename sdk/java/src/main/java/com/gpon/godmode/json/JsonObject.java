package com.gpon.godmode.json;

import java.util.*;

/**
 * Lightweight, zero-dependency JSON Object representation.
 * Provides safe type getters with case-insensitive / snake_case fallbacks.
 */
public class JsonObject implements Iterable<Map.Entry<String, Object>> {

    private final Map<String, Object> map;

    public JsonObject() {
        this.map = new LinkedHashMap<>();
    }

    public JsonObject(Map<String, Object> map) {
        this.map = map != null ? new LinkedHashMap<>(map) : new LinkedHashMap<>();
    }

    public void put(String key, Object value) {
        map.put(key, value);
    }

    public boolean containsKey(String key) {
        if (map.containsKey(key)) return true;
        for (String k : map.keySet()) {
            if (k.equalsIgnoreCase(key) || normalize(k).equals(normalize(key))) {
                return true;
            }
        }
        return false;
    }

    public Object get(String... keys) {
        for (String key : keys) {
            if (map.containsKey(key)) {
                return map.get(key);
            }
            // Check snake_case and case-insensitive alternatives
            String norm = normalize(key);
            for (Map.Entry<String, Object> entry : map.entrySet()) {
                if (normalize(entry.getKey()).equals(norm)) {
                    return entry.getValue();
                }
            }
        }
        return null;
    }

    public String getString(String... keys) {
        Object val = get(keys);
        if (val == null) return null;
        return val.toString();
    }

    public String getString(String defaultValue, String... keys) {
        String val = getString(keys);
        return val != null ? val : defaultValue;
    }

    public Integer getInteger(String... keys) {
        Object val = get(keys);
        if (val == null) return null;
        if (val instanceof Number) return ((Number) val).intValue();
        try {
            return Integer.parseInt(val.toString().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    public int getInt(int defaultValue, String... keys) {
        Integer val = getInteger(keys);
        return val != null ? val : defaultValue;
    }

    public Long getLongVal(String... keys) {
        Object val = get(keys);
        if (val == null) return null;
        if (val instanceof Number) return ((Number) val).longValue();
        try {
            return Long.parseLong(val.toString().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    public long getLong(long defaultValue, String... keys) {
        Long val = getLongVal(keys);
        return val != null ? val : defaultValue;
    }

    public Double getDoubleVal(String... keys) {
        Object val = get(keys);
        if (val == null) return null;
        if (val instanceof Number) return ((Number) val).doubleValue();
        try {
            return Double.parseDouble(val.toString().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    public double getDouble(double defaultValue, String... keys) {
        Double val = getDoubleVal(keys);
        return val != null ? val : defaultValue;
    }

    public Boolean getBooleanVal(String... keys) {
        Object val = get(keys);
        if (val == null) return null;
        if (val instanceof Boolean) return (Boolean) val;
        String str = val.toString().trim().toLowerCase(Locale.ROOT);
        if ("true".equals(str) || "1".equals(str) || "yes".equals(str)) return true;
        if ("false".equals(str) || "0".equals(str) || "no".equals(str)) return false;
        return null;
    }

    public boolean getBoolean(boolean defaultValue, String... keys) {
        Boolean val = getBooleanVal(keys);
        return val != null ? val : defaultValue;
    }

    @SuppressWarnings("unchecked")
    public JsonObject getObject(String... keys) {
        Object val = get(keys);
        if (val == null) return null;
        if (val instanceof JsonObject) return (JsonObject) val;
        if (val instanceof Map) return new JsonObject((Map<String, Object>) val);
        return null;
    }

    @SuppressWarnings("unchecked")
    public JsonArray getArray(String... keys) {
        Object val = get(keys);
        if (val == null) return null;
        if (val instanceof JsonArray) return (JsonArray) val;
        if (val instanceof List) return new JsonArray((List<Object>) val);
        return null;
    }

    public Map<String, Object> asMap() {
        return Collections.unmodifiableMap(map);
    }

    public Set<String> keySet() {
        return map.keySet();
    }

    public boolean isEmpty() {
        return map.isEmpty();
    }

    public int size() {
        return map.size();
    }

    @Override
    public Iterator<Map.Entry<String, Object>> iterator() {
        return map.entrySet().iterator();
    }

    private static String normalize(String s) {
        if (s == null) return "";
        return s.replace("_", "").replace("-", "").toLowerCase(Locale.ROOT);
    }

    public String toJson() {
        return SimpleJson.stringify(this);
    }

    @Override
    public String toString() {
        return toJson();
    }
}
