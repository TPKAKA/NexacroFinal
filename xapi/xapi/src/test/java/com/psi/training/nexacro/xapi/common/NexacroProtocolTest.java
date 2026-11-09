package com.psi.training.nexacro.xapi.common;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class NexacroProtocolTest {
    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void readsDatasetRowsAndParametersWithoutLosingValueTypes() throws Exception {
        JsonNode payload = mapper.readTree("""
            {
              "Parameters": [{"id":"sessionToken","value":"token-123"}],
              "Datasets": [{"id":"dsSearch","Rows":[
                {"Search":"  mouse  ","Page":2,"Enabled":true,"Missing":null},
                {"Search":"lamp"}
              ]}]
            }
            """);

        List<Map<String, Object>> rows = NexacroProtocol.rows(payload, "dsSearch");

        assertThat(rows).hasSize(2);
        assertThat(NexacroProtocol.value(rows.get(0), "Search")).isEqualTo("mouse");
        assertThat(rows.get(0)).containsEntry("Page", 2).containsEntry("Enabled", true).containsKey("Missing");
        assertThat(rows.get(0).get("Missing")).isNull();
        assertThat(NexacroProtocol.firstRow(payload, "missing")).isEmpty();
        assertThat(NexacroProtocol.parameter(payload, "sessionToken")).isEqualTo("token-123");
        assertThat(NexacroProtocol.parameter(payload, "absent")).isEmpty();
    }

    @Test
    void successResponseKeepsColumnLayoutWhenDatasetHasNoRows() {
        Map<String, Object> response = NexacroProtocol.success(
            NexacroProtocol.table("dsProducts", List.of("ProductID", "ProductName"), List.of()));

        assertThat(response).containsEntry("version", "1.0");
        assertThat(response.get("Parameters")).isEqualTo(List.of(
            Map.of("id", "ErrorCode", "value", 0),
            Map.of("id", "ErrorMsg", "value", "SUCCESS")));

        @SuppressWarnings("unchecked")
        Map<String, Object> dataset = (Map<String, Object>) ((List<?>) response.get("Datasets")).get(0);
        assertThat(dataset).containsEntry("id", "dsProducts").containsEntry("Rows", List.of());

        @SuppressWarnings("unchecked")
        Map<String, Object> columnInfo = (Map<String, Object>) dataset.get("ColumnInfo");
        assertThat(columnInfo.get("Column")).isEqualTo(List.of(
            Map.of("id", "ProductID", "type", "STRING", "size", "1024"),
            Map.of("id", "ProductName", "type", "STRING", "size", "1024")));
    }

    @Test
    void failureResponseUsesNexacroErrorParametersAndNoDatasets() {
        Map<String, Object> response = NexacroProtocol.failure("Invalid request");

        assertThat(response).containsEntry("version", "1.0").containsEntry("Datasets", List.of());
        assertThat(response.get("Parameters")).isEqualTo(List.of(
            Map.of("id", "ErrorCode", "value", -1),
            Map.of("id", "ErrorMsg", "value", "Invalid request")));
    }

    @Test
    void readsValuesCaseInsensitivelyAndReturnsAnEmptyStringForNull() {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("EMAIL", "  person@example.test ");
        row.put("Optional", null);

        assertThat(NexacroProtocol.value(row, "email")).isEqualTo("person@example.test");
        assertThat(NexacroProtocol.rawValue(row, "optional")).isEmpty();
    }
}
