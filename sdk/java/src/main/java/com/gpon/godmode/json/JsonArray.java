package com.gpon.godmode.json;

import java.util.*;

/**
 * Lightweight, zero-dependency JSON Array representation.
 */
public class JsonArray implements Iterable<Object> {

    private final List<Object> list;

    public JsonArray() {
        this.list = new ArrayList<>();
    }

    public JsonArray(List<Object> list) {
        this.list = list != null ? new ArrayList<>(list) : new ArrayList<>();
    }

    public void add(Object value) {
        list.add(value);
    }

    public Object get(int index) {
        return list.get(index);
    }

    public String getString(int index) {
        Object val = get(index);
        return val != null ? val.toString() : null;
    }

    public Integer getInteger(int index) {
        Object val = get(index);
        if (val == null) return null;
        if (val instanceof Number) return ((Number) val).intValue();
        try {
            return Integer.parseInt(val.toString().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    public int getInt(int index, int defaultValue) {
        Integer val = getInteger(index);
        return val != null ? val : defaultValue;
    }

    public Double getDouble(int index) {
        Object val = get(index);
        if (val == null) return null;
        if (val instanceof Number) return ((Number) val).doubleValue();
        try {
            return Double.parseDouble(val.toString().trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    public Boolean getBoolean(int index) {
        Object val = get(index);
        if (val == null) return null;
        if (val instanceof Boolean) return (Boolean) val;
        return Boolean.parseBoolean(val.toString().trim());
    }

    @SuppressWarnings("unchecked")
    public JsonObject getObject(int index) {
        Object val = get(index);
        if (val == null) return null;
        if (val instanceof JsonObject) return (JsonObject) val;
        if (val instanceof Map) return new JsonObject((Map<String, Object>) val);
        return null;
    }

    @SuppressWarnings("unchecked")
    public JsonArray getArray(int index) {
        Object val = get(index);
        if (val == null) return null;
        if (val instanceof JsonArray) return (JsonArray) val;
        if (val instanceof List) return new JsonArray((List<Object>) val);
        return null;
    }

    public int size() {
        return list.size();
    }

    public boolean isEmpty() {
        return list.isEmpty();
    }

    public List<Object> asList() {
        return Collections.unmodifiableList(list);
    }

    @Override
    public Iterator<Object> iterator() {
        return list.iterator();
    }

    public String toJson() {
        return SimpleJson.stringify(this);
    }

    @Override
    public String toString() {
        return toJson();
    }
}
