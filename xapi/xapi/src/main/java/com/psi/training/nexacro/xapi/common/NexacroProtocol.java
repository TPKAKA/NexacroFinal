package com.psi.training.nexacro.xapi.common;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class NexacroProtocol {
    public record Table(String id, List<String> columns, List<Map<String, Object>> rows) {}

    private NexacroProtocol() {}

    public static List<Map<String, Object>> rows(JsonNode payload, String datasetId) {
        List<Map<String, Object>> result = new ArrayList<>();
        JsonNode datasets = payload.path("Datasets");
        if (!datasets.isArray()) return result;
        for (JsonNode dataset : datasets) {
            if (!datasetId.equals(dataset.path("id").asText())) continue;
            JsonNode rows = dataset.path("Rows");
            if (!rows.isArray()) return result;
            for (JsonNode source : rows) {
                Map<String, Object> row = new LinkedHashMap<>();
                source.fields().forEachRemaining(entry -> {
                    JsonNode value = entry.getValue();
                    if (value.isNull()) row.put(entry.getKey(), null);
                    else if (value.isTextual()) row.put(entry.getKey(), value.asText());
                    else if (value.isNumber()) row.put(entry.getKey(), value.numberValue());
                    else if (value.isBoolean()) row.put(entry.getKey(), value.asBoolean());
                    else row.put(entry.getKey(), value.toString());
                });
                result.add(row);
            }
        }
        return result;
    }

    public static Map<String, Object> firstRow(JsonNode payload, String datasetId) {
        List<Map<String, Object>> rows = rows(payload, datasetId);
        return rows.isEmpty() ? new LinkedHashMap<>() : rows.get(0);
    }

    public static String parameter(JsonNode payload, String id) {
        JsonNode parameters = payload.path("Parameters");
        if (!parameters.isArray()) return "";
        for (JsonNode item : parameters) {
            if (id.equals(item.path("id").asText())) {
                JsonNode value = item.get("value");
                return value == null || value.isNull() ? "" : value.asText();
            }
        }
        return "";
    }

    public static String value(Map<String, Object> row, String name) {
        return rawValue(row, name).trim();
    }

    public static String rawValue(Map<String, Object> row, String name) {
        Object exact = row.get(name);
        if (exact != null) return String.valueOf(exact);
        for (Map.Entry<String, Object> entry : row.entrySet()) {
            if (entry.getKey().equalsIgnoreCase(name) && entry.getValue() != null) {
                return String.valueOf(entry.getValue());
            }
        }
        return "";
    }

    public static Map<String, Object> success(Table... tables) {
        List<Map<String, Object>> datasets = new ArrayList<>();
        for (Table table : tables) {
            List<Map<String, Object>> columns = new ArrayList<>();
            for (String column : table.columns()) {
                Map<String, Object> info = new LinkedHashMap<>();
                info.put("id", column);
                info.put("type", "STRING");
                info.put("size", "1024");
                columns.add(info);
            }
            Map<String, Object> columnInfo = new LinkedHashMap<>();
            columnInfo.put("Column", columns);
            Map<String, Object> dataset = new LinkedHashMap<>();
            dataset.put("id", table.id());
            dataset.put("ColumnInfo", columnInfo);
            dataset.put("Rows", table.rows());
            datasets.add(dataset);
        }
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("version", "1.0");
        response.put("Parameters", List.of(
            Map.of("id", "ErrorCode", "value", 0),
            Map.of("id", "ErrorMsg", "value", "SUCCESS")
        ));
        response.put("Datasets", datasets);
        return response;
    }

    public static Map<String, Object> failure(String message) {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("version", "1.0");
        response.put("Parameters", List.of(
            Map.of("id", "ErrorCode", "value", -1),
            Map.of("id", "ErrorMsg", "value", message == null ? "Request failed" : message)
        ));
        response.put("Datasets", List.of());
        return response;
    }

    public static Table table(String id, List<String> columns, List<Map<String, Object>> rows) {
        return new Table(id, columns, rows);
    }
}
