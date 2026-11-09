package com.psi.training.nexacro.xapi.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class InventoryApiIntegrationTest {
    private static final Path UPLOAD_DIR = Path.of(System.getProperty("java.io.tmpdir"),
        "nexacro-final-test-uploads").toAbsolutePath().normalize();

    @Autowired private MockMvc mvc;
    @Autowired private ObjectMapper mapper;

    @DynamicPropertySource
    static void uploadDirectory(DynamicPropertyRegistry registry) {
        registry.add("app.upload-dir", UPLOAD_DIR::toString);
        registry.add("app.public-base-url", () -> "http://localhost:8080");
    }

    @AfterAll
    static void removeUploadedFiles() throws Exception {
        if (Files.exists(UPLOAD_DIR)) {
            try (var paths = Files.walk(UPLOAD_DIR)) {
                paths.sorted((left, right) -> right.compareTo(left)).forEach(path -> {
                    try { Files.deleteIfExists(path); }
                    catch (Exception exception) { throw new IllegalStateException(exception); }
                });
            }
        }
    }

    @Test
    void endToEndInventoryAndSupplierFlowUsesNexacroDatasetsAndSessionLifecycle() throws Exception {
        String nonce = UUID.randomUUID().toString().substring(0, 8);
        String email = "inventory-" + nonce + "@example.test";
        String password = "  Stock room! " ;

        JsonNode signup = postDataset("/api/auth/signup", "dsSignup", row(
            "Name", "Inventory Tester", "Email", email, "Password", password));
        assertSuccess(signup);
        String token = datasetRow(signup, "dsSession").path("Token").asText();
        assertThat(token).isNotBlank();

        JsonNode duplicate = postDataset("/api/auth/signup", "dsSignup", row(
            "Name", "Inventory Tester", "Email", email, "Password", password));
        assertFailure(duplicate, "already exists");

        JsonNode login = postDataset("/api/auth/login", "dsLogin", row(
            "Email", email.toUpperCase(), "Password", password, "RememberMe", "1"));
        assertSuccess(login);
        token = datasetRow(login, "dsSession").path("Token").asText();
        assertThat(datasetRow(login, "dsSession").path("RememberMe").asText()).isEqualTo("1");

        JsonNode codes = postDataset("/api/codes/list", null, Map.of());
        assertSuccess(codes);
        assertThat(datasetRow(codes, "dsCodes")).isNotNull();
        assertThat(datasetRows(codes, "dsCodes")).hasSizeGreaterThanOrEqualTo(10);

        Map<String, String> search = row("Search", "", "Status", "", "Page", "0", "PageSize", "10");
        JsonNode products = postDataset("/api/products/search", "dsSearch", search, token);
        assertSuccess(products);
        assertThat(datasetRows(products, "dsProducts")).hasSize(5);
        assertThat(datasetRow(products, "dsSummary").path("TotalProducts").asText()).isEqualTo("5");
        assertThat(datasetRow(products, "dsSummary").path("FilteredProducts").asText()).isEqualTo("5");
        assertThat(datasetRow(products, "dsSummary").path("LowStocks").asText()).isEqualTo("1");

        JsonNode secondProductPage = postDataset("/api/products/search", "dsSearch",
            row("Search", "", "Status", "", "Page", "1", "PageSize", "2"), token);
        assertSuccess(secondProductPage);
        assertThat(datasetRows(secondProductPage, "dsProducts")).hasSize(2);
        assertThat(datasetRow(secondProductPage, "dsSummary").path("FilteredProducts").asText()).isEqualTo("5");

        JsonNode detail = postDataset("/api/products/detail", "dsRequest", row("ProductID", "PRD-002"), token);
        assertSuccess(detail);
        assertThat(datasetRow(detail, "dsProductDetail").path("Status").asText()).isEqualTo("Low stock");
        assertThat(datasetRows(detail, "dsStockLocations")).hasSize(1);
        assertThat(datasetRows(detail, "dsPurchases")).isEmpty();
        assertThat(datasetRows(detail, "dsHistory")).isNotEmpty();

        String productId = "TEST-" + nonce.toUpperCase();
        Map<String, String> newProduct = row(
            "ProductID", productId, "ProductName", "Test Cable", "Category", "Electronics",
            "BuyingPrice", "4.25", "Quantity", "6", "Unit", "pcs", "ExpiryDate", "2028-12-31",
            "Threshold", "5", "Supplier", "", "SupplierID", "", "ImageUrl", "");
        JsonNode savedProduct = postDataset("/api/products/save", "dsProduct", newProduct, token);
        assertSuccess(savedProduct);
        assertThat(datasetRow(savedProduct, "dsSaved").path("ProductID").asText()).isEqualTo(productId);

        Map<String, String> update = new LinkedHashMap<>(newProduct);
        update.put("Quantity", "4");
        JsonNode updatedProduct = postDataset("/api/products/save", "dsProduct", update, token,
            Map.of("mode", "update"));
        assertSuccess(updatedProduct);
        assertThat(datasetRow(updatedProduct, "dsSaved").path("Status").asText()).isEqualTo("Low stock");

        JsonNode filtered = postDataset("/api/products/search", "dsSearch",
            row("Search", "test cable", "Status", "Low stock", "Page", "0", "PageSize", "10"), token);
        assertSuccess(filtered);
        assertThat(datasetRows(filtered, "dsProducts")).hasSize(1);
        assertThat(datasetRow(filtered, "dsProducts").path("ProductID").asText()).isEqualTo(productId);
        assertThat(datasetRow(filtered, "dsSummary").path("FilteredProducts").asText()).isEqualTo("1");

        JsonNode filteredPastEnd = postDataset("/api/products/search", "dsSearch",
            row("Search", "test cable", "Status", "Low stock", "Page", "1", "PageSize", "10"), token);
        assertSuccess(filteredPastEnd);
        assertThat(datasetRows(filteredPastEnd, "dsProducts")).isEmpty();
        assertThat(datasetRow(filteredPastEnd, "dsSummary").path("FilteredProducts").asText()).isEqualTo("1");

        Map<String, String> newSupplier = row(
            "SupplierName", "Test Source " + nonce, "Product", "Test Cable", "Category", "Electronics",
            "BuyingPrice", "4.25", "Contact", "0900000000", "Email", "supply-" + nonce + "@example.test",
            "Type", "Taking return", "OnTheWay", "12", "ImageUrl", "");
        JsonNode savedSupplier = postDataset("/api/suppliers/save", "dsSupplier", newSupplier, token);
        assertSuccess(savedSupplier);
        String supplierId = datasetRow(savedSupplier, "dsSupplierResult").path("SupplierID").asText();
        assertThat(supplierId).startsWith("SUP-");

        JsonNode suppliers = postDataset("/api/suppliers/search", "dsSearch",
            row("Search", "Test Source " + nonce, "Type", "Taking return", "Page", "0",
                "PageSize", "12", "SortField", "SupplierName", "SortOrder", "ASC"), token);
        assertSuccess(suppliers);
        assertThat(datasetRows(suppliers, "dsSuppliers")).hasSize(1);
        assertThat(datasetRow(suppliers, "dsSupplierSummary").path("TotalSuppliers").asText()).isEqualTo("1");

        MvcResult uploadResult = mvc.perform(multipart("/api/uploads/image")
                .file(new MockMultipartFile("image", "test.png", "image/png", new byte[] {1, 2, 3, 4}))
                .param("sessionToken", token))
            .andExpect(status().isOk()).andReturn();
        JsonNode uploaded = mapper.readTree(uploadResult.getResponse().getContentAsString());
        assertSuccess(uploaded);
        String imageUrl = datasetRow(uploaded, "dsUpload").path("ImageUrl").asText();
        assertThat(imageUrl).contains("/uploads/").endsWith(".png");
        String savedImage = imageUrl.substring(imageUrl.lastIndexOf('/') + 1);
        assertThat(Files.exists(UPLOAD_DIR.resolve(savedImage))).isTrue();

        MvcResult exportResult = mvc.perform(get("/api/products/export.csv")
                .param("sessionToken", token).param("search", productId))
            .andExpect(status().isOk()).andReturn();
        assertThat(exportResult.getResponse().getContentAsString()).contains("ProductID", productId);

        JsonNode logout = postDataset("/api/auth/logout", "dsLogout", row("SessionToken", token), token);
        assertSuccess(logout);
        JsonNode afterLogout = postDataset("/api/products/search", "dsSearch", search, token);
        assertFailure(afterLogout, "session has expired");
    }

    @Test
    void validationFailuresUseNexacroErrorParametersAndStableEmptyDatasets() throws Exception {
        JsonNode missingDataset = postDataset("/api/auth/signup", "dsSignup", row(
            "Name", "", "Email", "not-an-email", "Password", "short"));
        assertFailure(missingDataset, "Name is required");
        assertThat(missingDataset.path("Datasets").isArray()).isTrue();
        assertThat(missingDataset.path("Datasets").size()).isZero();

        JsonNode unauthorized = postDataset("/api/products/search", "dsSearch",
            row("Search", "", "Status", "", "Page", "0", "PageSize", "10"), "invalid-token");
        assertFailure(unauthorized, "session has expired");
    }

    private JsonNode postDataset(String path, String datasetId, Map<String, String> row) throws Exception {
        return postDataset(path, datasetId, row, "", Map.of());
    }

    private JsonNode postDataset(String path, String datasetId, Map<String, String> row, String token) throws Exception {
        return postDataset(path, datasetId, row, token, Map.of());
    }

    private JsonNode postDataset(String path, String datasetId, Map<String, String> row,
                                 String token, Map<String, String> parameters) throws Exception {
        Map<String, String> values = new LinkedHashMap<>(parameters);
        if (!token.isBlank()) values.put("sessionToken", token);
        String body = payload(datasetId, row, values);
        MvcResult result = mvc.perform(post(path).contentType(MediaType.APPLICATION_JSON).content(body))
            .andExpect(status().isOk()).andReturn();
        return mapper.readTree(result.getResponse().getContentAsString());
    }

    private String payload(String datasetId, Map<String, String> row, Map<String, String> parameters) throws Exception {
        ObjectNode root = mapper.createObjectNode().put("version", "1.0");
        ArrayNode parameterArray = root.putArray("Parameters");
        parameters.forEach((key, value) -> parameterArray.addObject().put("id", key).put("value", value));
        ArrayNode datasets = root.putArray("Datasets");
        if (datasetId != null) {
            ObjectNode dataset = datasets.addObject().put("id", datasetId);
            ObjectNode columnInfo = dataset.putObject("ColumnInfo");
            ArrayNode columns = columnInfo.putArray("Column");
            row.keySet().forEach(key -> columns.addObject().put("id", key).put("type", "STRING").put("size", "1024"));
            ObjectNode dataRow = dataset.putArray("Rows").addObject().put("_RowType_", "N");
            row.forEach(dataRow::put);
        }
        return mapper.writeValueAsString(root);
    }

    private Map<String, String> row(String... values) {
        Map<String, String> result = new LinkedHashMap<>();
        for (int i = 0; i < values.length; i += 2) result.put(values[i], values[i + 1]);
        return result;
    }

    private JsonNode datasetRow(JsonNode response, String id) {
        return datasetRows(response, id).get(0);
    }

    private java.util.List<JsonNode> datasetRows(JsonNode response, String id) {
        for (JsonNode dataset : response.path("Datasets")) {
            if (id.equals(dataset.path("id").asText())) {
                java.util.List<JsonNode> result = new java.util.ArrayList<>();
                dataset.path("Rows").forEach(result::add);
                return result;
            }
        }
        throw new AssertionError("Missing Nexacro dataset: " + id);
    }

    private void assertSuccess(JsonNode response) {
        assertThat(response.path("version").asText()).isEqualTo("1.0");
        assertThat(parameter(response, "ErrorCode").asInt()).isZero();
    }

    private void assertFailure(JsonNode response, String messagePart) {
        assertThat(response.path("version").asText()).isEqualTo("1.0");
        assertThat(parameter(response, "ErrorCode").asInt()).isNegative();
        assertThat(parameter(response, "ErrorMsg").asText().toLowerCase())
            .contains(messagePart.toLowerCase());
    }

    private JsonNode parameter(JsonNode response, String id) {
        for (JsonNode item : response.path("Parameters")) {
            if (id.equals(item.path("id").asText())) return item.path("value");
        }
        throw new AssertionError("Missing Nexacro parameter: " + id);
    }
}
