package com.psi.training.nexacro.xapi.api.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.psi.training.nexacro.xapi.api.service.AuthenticationService;
import com.psi.training.nexacro.xapi.common.ApiException;
import com.psi.training.nexacro.xapi.common.NexacroProtocol;
import com.psi.training.nexacro.xapi.common.NexacroProtocol.Table;
import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.env.Environment;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.multipart.MultipartHttpServletRequest;

@RestController
@RequestMapping("/api")
public class NexacroApiController {
    private static final Logger log = LoggerFactory.getLogger(NexacroApiController.class);
    private static final List<String> PRODUCT_COLUMNS = List.of(
        "ProductID", "ProductName", "Category", "BuyingPrice", "Quantity", "Unit",
        "ExpiryDate", "Threshold", "Supplier", "SupplierID", "ImageUrl", "Status");
    private static final List<String> DETAIL_COLUMNS = List.of(
        "ProductID", "ProductIDLabel", "ProductName", "Category", "BuyingPrice", "Quantity",
        "Unit", "ExpiryDate", "Threshold", "Supplier", "SupplierInfo", "SupplierID",
        "ImageUrl", "Status", "OverviewText");
    private static final List<String> SUPPLIER_COLUMNS = List.of(
        "SupplierID", "SupplierName", "Product", "Category", "BuyingPrice", "Contact",
        "Email", "Type", "OnTheWay", "ImageUrl");
    private static final List<String> LOCATION_COLUMNS = List.of("Location", "Quantity", "Unit", "UpdatedAt");
    private static final List<String> EVENT_COLUMNS = List.of(
        "EventID", "Type", "QuantityChange", "Description", "CreatedAt");
    private final JdbcTemplate jdbc;
    private final AuthenticationService authentication;
    private final Environment environment;

    public NexacroApiController(JdbcTemplate jdbc, AuthenticationService authentication, Environment environment) {
        this.jdbc = jdbc;
        this.authentication = authentication;
        this.environment = environment;
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        return Map.of("status", "UP", "service", "nexacro-inventory-api");
    }

    @PostMapping("/auth/signup")
    public Map<String, Object> signup(@RequestBody JsonNode payload) {
        return NexacroProtocol.success(NexacroProtocol.table(
            "dsSession", List.of("UserID", "Name", "Email", "Token", "ExpiresAt", "RememberMe"),
            List.of(authentication.register(payload))));
    }

    @PostMapping("/auth/login")
    public Map<String, Object> login(@RequestBody JsonNode payload) {
        return NexacroProtocol.success(NexacroProtocol.table(
            "dsSession", List.of("UserID", "Name", "Email", "Token", "ExpiresAt", "RememberMe"),
            List.of(authentication.login(payload))));
    }

    @PostMapping("/auth/logout")
    public Map<String, Object> logout(@RequestBody JsonNode payload) {
        authentication.revokeSession(payload);
        return NexacroProtocol.success();
    }

    @PostMapping("/auth/forgot")
    public Map<String, Object> forgotPassword(@RequestBody JsonNode payload) {
        Map<String, Object> input = NexacroProtocol.firstRow(payload, "dsForgot");
        String email = NexacroProtocol.value(input, "Email");
        if (email.isBlank()) throw new ApiException("Enter your email address.");
        return NexacroProtocol.success(NexacroProtocol.table(
            "dsResult", List.of("Message"),
            List.of(row("Message", "Contact your workspace administrator to reset your password."))));
    }

    @PostMapping("/codes/list")
    public Map<String, Object> codes() {
        List<Map<String, Object>> rows = new ArrayList<>();
        addCodes(rows, "Category", List.of("Electronics", "Office", "Stationery", "Lifestyle", "Other"));
        addCodes(rows, "Unit", List.of("pcs", "box", "kg", "litre"));
        addCodes(rows, "SupplierType", List.of("Taking return", "Not taking return"));
        return NexacroProtocol.success(NexacroProtocol.table(
            "dsCodes", List.of("CodeType", "Code", "Label"), rows));
    }

    @PostMapping("/products/search")
    public Map<String, Object> searchProducts(@RequestBody JsonNode payload) {
        authentication.requireSession(payload);
        Map<String, Object> criteria = NexacroProtocol.firstRow(payload, "dsSearch");
        String query = NexacroProtocol.value(criteria, "Search").toLowerCase(Locale.ROOT);
        String status = NexacroProtocol.value(criteria, "Status");
        int page = integer(criteria, "Page", 0, 0, 10_000);
        int pageSize = integer(criteria, "PageSize", 10, 1, 100);
        String pattern = "%" + query + "%";
        String statusExpr = "CASE WHEN p.quantity <= 0 THEN 'Out of stock' WHEN p.quantity <= p.threshold THEN 'Low stock' ELSE 'In stock' END";
        String where = " WHERE (? = '' OR LOWER(p.product_name) LIKE ? OR LOWER(p.product_id) LIKE ? OR LOWER(p.category) LIKE ?) "
            + "AND (? = '' OR " + statusExpr + " = ?)";
        String select = productSelectSql();
        List<Map<String, Object>> rows = jdbc.query(
            select + where + " ORDER BY p.product_name, p.product_id LIMIT ? OFFSET ?",
            productMapper(), query, pattern, pattern, pattern, status, status, pageSize, page * pageSize);
        Integer filteredProducts = jdbc.queryForObject(
            "SELECT COUNT(*) FROM products p" + where,
            Integer.class, query, pattern, pattern, pattern, status, status);
        Map<String, Object> summary = jdbc.queryForMap(
            "SELECT COUNT(*) AS total, COUNT(DISTINCT category) AS categories, "
                + "SUM(CASE WHEN quantity > 0 AND quantity <= threshold THEN 1 ELSE 0 END) AS low_count, "
                + "SUM(CASE WHEN quantity <= 0 THEN 1 ELSE 0 END) AS out_count FROM products");
        Map<String, Object> summaryRow = row(
            "Categories", text(summary.get("categories")),
            "TotalProducts", text(summary.get("total")),
            "FilteredProducts", String.valueOf(filteredProducts),
            "TopSelling", "—",
            "LowStocks", text(summary.get("low_count")),
            "OutOfStock", text(summary.get("out_count")),
            "TopSellingNote", "No sales data is recorded");
        return NexacroProtocol.success(
            NexacroProtocol.table("dsProducts", PRODUCT_COLUMNS, rows),
            NexacroProtocol.table("dsSummary",
                List.of("Categories", "TotalProducts", "FilteredProducts", "TopSelling", "LowStocks", "OutOfStock", "TopSellingNote"),
                List.of(summaryRow)));
    }

    @Transactional
    @PostMapping("/products/save")
    public Map<String, Object> saveProduct(@RequestBody JsonNode payload) {
        authentication.requireSession(payload);
        Map<String, Object> input = NexacroProtocol.firstRow(payload, "dsProduct");
        String id = required(input, "ProductID");
        String name = required(input, "ProductName");
        String category = required(input, "Category");
        String unit = required(input, "Unit");
        BigDecimal price = decimal(input, "BuyingPrice");
        int quantity = integer(input, "Quantity", -1, 0, 2_000_000_000);
        int threshold = integer(input, "Threshold", -1, 0, 2_000_000_000);
        LocalDate expiry = date(input, "ExpiryDate");
        String imageUrl = NexacroProtocol.value(input, "ImageUrl");
        String supplierId = NexacroProtocol.value(input, "SupplierID");
        String mode = NexacroProtocol.parameter(payload, "mode");
        if (!imageUrl.isBlank() && !(imageUrl.startsWith("http://") || imageUrl.startsWith("https://"))) {
            throw new ApiException("Image URL must be an HTTP or HTTPS URL.");
        }
        if (!supplierId.isBlank()
            && jdbc.queryForObject("SELECT COUNT(*) FROM suppliers WHERE supplier_id = ?", Integer.class, supplierId) == 0) {
            throw new ApiException("Select a valid supplier.");
        }
        if ("update".equalsIgnoreCase(mode)) {
            updateProduct(id, name, category, price, quantity, unit, expiry, threshold, supplierId, imageUrl);
        } else {
            if (jdbc.queryForObject("SELECT COUNT(*) FROM products WHERE product_id = ?", Integer.class, id) > 0) {
                throw new ApiException("Product ID already exists.");
            }
            try {
                jdbc.update("INSERT INTO products (product_id, product_name, category, buying_price, quantity, unit, "
                        + "expiry_date, threshold, supplier_id, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULLIF(?, ''), ?)",
                    id, name, category, price, quantity, unit, expiry, threshold, supplierId, emptyToNull(imageUrl));
            } catch (DuplicateKeyException duplicate) {
                throw new ApiException("Product ID already exists.");
            }
            jdbc.update("INSERT INTO stock_locations (product_id, location_name, quantity) VALUES (?, ?, ?)",
                id, "Main Warehouse", quantity);
            jdbc.update("INSERT INTO inventory_events (product_id, event_type, quantity_change, description) "
                    + "VALUES (?, 'INITIAL', ?, ?)", id, quantity, "Opening stock");
        }
        Map<String, Object> saved = findProduct(id);
        return NexacroProtocol.success(NexacroProtocol.table("dsSaved", PRODUCT_COLUMNS, List.of(saved)));
    }

    @PostMapping("/products/detail")
    public Map<String, Object> productDetail(@RequestBody JsonNode payload) {
        authentication.requireSession(payload);
        String id = required(NexacroProtocol.firstRow(payload, "dsRequest"), "ProductID");
        Map<String, Object> product = findProduct(id);
        List<Map<String, Object>> detail = jdbc.query(
            "SELECT p.product_id AS \"ProductID\", p.product_name AS \"ProductName\", p.category AS \"Category\", "
                + "CAST(p.buying_price AS VARCHAR) AS \"BuyingPrice\", CAST(p.quantity AS VARCHAR) AS \"Quantity\", "
                + "p.unit AS \"Unit\", CAST(p.expiry_date AS VARCHAR) AS \"ExpiryDate\", "
                + "CAST(p.threshold AS VARCHAR) AS \"Threshold\", COALESCE(s.supplier_name, '') AS \"Supplier\", "
                + "COALESCE(p.supplier_id, '') AS \"SupplierID\", COALESCE(p.image_url, '') AS \"ImageUrl\", "
                + "CASE WHEN p.quantity <= 0 THEN 'Out of stock' WHEN p.quantity <= p.threshold THEN 'Low stock' "
                + "ELSE 'In stock' END AS \"Status\" "
                + "FROM products p LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id WHERE p.product_id = ?",
            productMapper(), id);
        Map<String, Object> detailRow = new LinkedHashMap<>(detail.get(0));
        String supplier = firstNonBlank(text(detailRow.get("Supplier")),
            findSupplierForProduct(text(detailRow.get("ProductName"))));
        detailRow.put("Supplier", supplier);
        detailRow.put("SupplierInfo", supplier.isBlank() ? "No supplier is linked to this product." : supplier);
        detailRow.put("ProductIDLabel", "Product ID: " + detailRow.get("ProductID") + "  •  " + detailRow.get("Category"));
        detailRow.put("OverviewText", "Buying price: " + detailRow.get("BuyingPrice")
            + "\nQuantity: " + detailRow.get("Quantity") + " " + detailRow.get("Unit")
            + "\nThreshold: " + detailRow.get("Threshold")
            + "\nExpiry date: " + detailRow.get("ExpiryDate"));
        List<Map<String, Object>> locations = jdbc.query(
            "SELECT location_name AS \"Location\", CAST(quantity AS VARCHAR) AS \"Quantity\", "
                + "(SELECT unit FROM products WHERE product_id = stock_locations.product_id) AS \"Unit\", "
                + "CAST(updated_at AS VARCHAR) AS \"UpdatedAt\" FROM stock_locations "
                + "WHERE product_id = ? ORDER BY location_name",
            (rs, row) -> readRow(rs, LOCATION_COLUMNS), id);
        List<Map<String, Object>> purchases = findEvents(id, "PURCHASE");
        List<Map<String, Object>> adjustments = findEvents(id, "ADJUSTMENT", "INITIAL");
        List<Map<String, Object>> history = findEvents(id, (String[]) null);
        List<Map<String, Object>> detailRows = List.of(detailRow);
        return NexacroProtocol.success(
            NexacroProtocol.table("dsProduct", PRODUCT_COLUMNS, List.of(product)),
            NexacroProtocol.table("dsProductDetail", DETAIL_COLUMNS, detailRows),
            NexacroProtocol.table("dsStockLocations", LOCATION_COLUMNS, locations),
            NexacroProtocol.table("dsPurchases", EVENT_COLUMNS, purchases),
            NexacroProtocol.table("dsAdjustments", EVENT_COLUMNS, adjustments),
            NexacroProtocol.table("dsHistory", EVENT_COLUMNS, history));
    }

    @PostMapping("/suppliers/search")
    public Map<String, Object> searchSuppliers(@RequestBody JsonNode payload) {
        authentication.requireSession(payload);
        Map<String, Object> criteria = NexacroProtocol.firstRow(payload, "dsSearch");
        String query = NexacroProtocol.value(criteria, "Search").toLowerCase(Locale.ROOT);
        String type = NexacroProtocol.value(criteria, "Type");
        int page = integer(criteria, "Page", 0, 0, 10_000);
        int pageSize = integer(criteria, "PageSize", 12, 1, 100);
        String sortField = NexacroProtocol.value(criteria, "SortField");
        String sortOrder = "DESC".equalsIgnoreCase(NexacroProtocol.value(criteria, "SortOrder")) ? "DESC" : "ASC";
        String sortColumn = switch (sortField) {
            case "Product" -> "product_name";
            case "Contact" -> "contact";
            case "Email" -> "email";
            case "Type" -> "supplier_type";
            case "OnTheWay" -> "on_the_way";
            default -> "supplier_name";
        };
        String pattern = "%" + query + "%";
        String where = " WHERE (? = '' OR LOWER(supplier_name) LIKE ? OR LOWER(product_name) LIKE ? OR LOWER(COALESCE(email, '')) LIKE ?) "
            + "AND (? = '' OR supplier_type = ?)";
        List<Map<String, Object>> rows = jdbc.query(supplierSelectSql() + where
                + " ORDER BY " + sortColumn + " " + sortOrder + ", supplier_id LIMIT ? OFFSET ?",
            supplierMapper(), query, pattern, pattern, pattern, type, type, pageSize, page * pageSize);
        Integer count = jdbc.queryForObject(
            "SELECT COUNT(*) FROM suppliers" + where,
            Integer.class, query, pattern, pattern, pattern, type, type);
        return NexacroProtocol.success(
            NexacroProtocol.table("dsSuppliers", SUPPLIER_COLUMNS, rows),
            NexacroProtocol.table("dsSupplierSummary", List.of("TotalSuppliers"),
                List.of(row("TotalSuppliers", String.valueOf(count)))));
    }

    @Transactional
    @PostMapping("/suppliers/save")
    public Map<String, Object> saveSupplier(@RequestBody JsonNode payload) {
        authentication.requireSession(payload);
        Map<String, Object> input = NexacroProtocol.firstRow(payload, "dsSupplier");
        String name = required(input, "SupplierName");
        String product = required(input, "Product");
        String category = required(input, "Category");
        BigDecimal price = decimal(input, "BuyingPrice");
        String contact = required(input, "Contact");
        String email = NexacroProtocol.value(input, "Email");
        String type = required(input, "Type");
        int onTheWay = integer(input, "OnTheWay", 0, 0, 2_000_000_000);
        String imageUrl = NexacroProtocol.value(input, "ImageUrl");
        if (!email.isBlank() && !email.matches("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")) {
            throw new ApiException("Enter a valid email address.");
        }
        if (!"Taking return".equals(type) && !"Not taking return".equals(type)) {
            throw new ApiException("Choose a valid supplier type.");
        }
        String id = "SUP-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase(Locale.ROOT);
        jdbc.update("INSERT INTO suppliers (supplier_id, supplier_name, product_name, category, buying_price, "
                + "contact, email, supplier_type, on_the_way, image_url) VALUES (?, ?, ?, ?, ?, ?, NULLIF(?, ''), ?, ?, ?)",
            id, name, product, category, price, contact, email, type, onTheWay, emptyToNull(imageUrl));
        Map<String, Object> saved = findSupplier(id);
        return NexacroProtocol.success(NexacroProtocol.table("dsSupplierResult", SUPPLIER_COLUMNS, List.of(saved)));
    }

    @RequestMapping(value = "/products/export.csv", method = {RequestMethod.GET, RequestMethod.POST}, produces = "text/csv")
    public ResponseEntity<String> exportProducts(@RequestParam(name = "sessionToken", required = false) String token,
                                                 @RequestParam(name = "search", defaultValue = "") String search,
                                                 @RequestParam(name = "status", defaultValue = "") String status) {
        authentication.requireSession(token);
        String query = search.toLowerCase(Locale.ROOT);
        String pattern = "%" + query + "%";
        String expression = "CASE WHEN p.quantity <= 0 THEN 'Out of stock' WHEN p.quantity <= p.threshold THEN 'Low stock' ELSE 'In stock' END";
        String sql = productSelectSql() + " WHERE (? = '' OR LOWER(p.product_name) LIKE ? OR LOWER(p.product_id) LIKE ? OR LOWER(p.category) LIKE ?) "
            + "AND (? = '' OR " + expression + " = ?) ORDER BY p.product_name, p.product_id";
        List<Map<String, Object>> rows = jdbc.query(sql, productMapper(), query, pattern, pattern, pattern, status, status);
        String csv = csv(PRODUCT_COLUMNS, rows);
        return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"products.csv\"")
            .contentType(MediaType.parseMediaType("text/csv;charset=UTF-8")).body(csv);
    }

    @RequestMapping(value = "/suppliers/export.csv", method = {RequestMethod.GET, RequestMethod.POST}, produces = "text/csv")
    public ResponseEntity<String> exportSuppliers(@RequestParam(name = "sessionToken", required = false) String token,
                                                  @RequestParam(name = "search", defaultValue = "") String search,
                                                  @RequestParam(name = "type", defaultValue = "") String type) {
        authentication.requireSession(token);
        String query = search.toLowerCase(Locale.ROOT);
        String pattern = "%" + query + "%";
        List<Map<String, Object>> rows = jdbc.query(supplierSelectSql()
                + " WHERE (? = '' OR LOWER(supplier_name) LIKE ? OR LOWER(product_name) LIKE ? OR LOWER(COALESCE(email, '')) LIKE ?) "
                + "AND (? = '' OR supplier_type = ?) ORDER BY supplier_name",
            supplierMapper(), query, pattern, pattern, pattern, type, type);
        return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"suppliers.csv\"")
            .contentType(MediaType.parseMediaType("text/csv;charset=UTF-8")).body(csv(SUPPLIER_COLUMNS, rows));
    }

    @PostMapping(value = "/uploads/image", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Map<String, Object> uploadImage(MultipartHttpServletRequest request) throws Exception {
        authentication.requireSession(request.getParameter("sessionToken"));
        MultipartFile image = request.getFileMap().values().stream()
            .filter(file -> !file.isEmpty() && file.getOriginalFilename() != null)
            .findFirst().orElseThrow(() -> new ApiException("Choose an image file first."));
        if (image.getSize() > 5L * 1024 * 1024) throw new ApiException("Image size must be 5 MB or less.");
        String original = Path.of(image.getOriginalFilename()).getFileName().toString();
        String extension = extension(original);
        String contentType = image.getContentType() == null ? "" : image.getContentType().toLowerCase(Locale.ROOT);
        if (!List.of(".png", ".jpg", ".jpeg", ".gif", ".webp").contains(extension)
            || !contentType.startsWith("image/")) {
            throw new ApiException("Choose a PNG, JPG, GIF, or WebP image.");
        }
        Path directory = Path.of(environment.getProperty("app.upload-dir", "./uploads")).toAbsolutePath().normalize();
        Files.createDirectories(directory);
        String storedName = UUID.randomUUID() + extension;
        Path destination = directory.resolve(storedName).normalize();
        if (!destination.getParent().equals(directory)) throw new ApiException("Invalid image path.");
        try (InputStream stream = image.getInputStream()) {
            Files.copy(stream, destination);
        }
        String baseUrl = environment.getProperty("app.public-base-url", "http://localhost:8080");
        Map<String, Object> row = row("FileName", original, "ImageUrl", baseUrl + "/uploads/" + storedName);
        return NexacroProtocol.success(NexacroProtocol.table(
            "dsUpload", List.of("FileName", "ImageUrl"), List.of(row)));
    }

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<Map<String, Object>> handleExpected(ApiException exception) {
        return ResponseEntity.ok(NexacroProtocol.failure(exception.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleUnexpected(Exception exception) {
        log.error("Inventory request failed", exception);
        return ResponseEntity.ok(NexacroProtocol.failure("The request could not be completed."));
    }

    private void updateProduct(String id, String name, String category, BigDecimal price, int quantity,
                               String unit, LocalDate expiry, int threshold, String supplierId, String imageUrl) {
        List<Integer> previous = jdbc.query(
            "SELECT quantity FROM products WHERE product_id = ?", (rs, row) -> rs.getInt(1), id);
        if (previous.isEmpty()) throw new ApiException("The selected product no longer exists.");
        int delta = quantity - previous.get(0);
        jdbc.update("UPDATE products SET product_name = ?, category = ?, buying_price = ?, quantity = ?, unit = ?, "
                + "expiry_date = ?, threshold = ?, supplier_id = NULLIF(?, ''), image_url = ?, updated_at = CURRENT_TIMESTAMP "
                + "WHERE product_id = ?",
            name, category, price, quantity, unit, expiry, threshold, supplierId, emptyToNull(imageUrl), id);
        jdbc.update("UPDATE stock_locations SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ?",
            quantity, id);
        if (delta != 0) {
            jdbc.update("INSERT INTO inventory_events (product_id, event_type, quantity_change, description) "
                    + "VALUES (?, 'ADJUSTMENT', ?, ?)", id, delta, "Product detail updated");
        }
    }

    private Map<String, Object> findProduct(String id) {
        List<Map<String, Object>> result = jdbc.query(productSelectSql() + " WHERE p.product_id = ?",
            productMapper(), id);
        if (result.isEmpty()) throw new ApiException("Product was not found.");
        return result.get(0);
    }

    private List<Map<String, Object>> findEvents(String id, String... types) {
        String filter = "";
        Object[] args = new Object[1];
        args[0] = id;
        if (types != null && types.length > 0 && types[0] != null) {
            filter = " AND event_type IN (" + String.join(",", Arrays.stream(types).map(type -> "?").toList()) + ")";
            args = new Object[types.length + 1];
            args[0] = id;
            System.arraycopy(types, 0, args, 1, types.length);
        }
        return jdbc.query("SELECT CAST(event_id AS VARCHAR) AS \"EventID\", event_type AS \"Type\", "
                + "CAST(quantity_change AS VARCHAR) AS \"QuantityChange\", description AS \"Description\", "
                + "CAST(created_at AS VARCHAR) AS \"CreatedAt\" FROM inventory_events "
                + "WHERE product_id = ?" + filter + " ORDER BY event_id DESC",
            (rs, row) -> readRow(rs, EVENT_COLUMNS), args);
    }

    private String findSupplierForProduct(String productName) {
        List<String> names = jdbc.query(
            "SELECT supplier_name FROM suppliers WHERE LOWER(TRIM(product_name)) = LOWER(TRIM(?)) "
                + "ORDER BY supplier_name LIMIT 1",
            (rs, row) -> rs.getString(1), productName);
        return names.isEmpty() ? "" : names.get(0);
    }

    private Map<String, Object> findSupplier(String id) {
        List<Map<String, Object>> result = jdbc.query(supplierSelectSql() + " WHERE supplier_id = ?",
            supplierMapper(), id);
        if (result.isEmpty()) throw new ApiException("Supplier was not found.");
        return result.get(0);
    }

    private String productSelectSql() {
        return "SELECT p.product_id AS \"ProductID\", p.product_name AS \"ProductName\", p.category AS \"Category\", "
            + "CAST(p.buying_price AS VARCHAR) AS \"BuyingPrice\", CAST(p.quantity AS VARCHAR) AS \"Quantity\", "
            + "p.unit AS \"Unit\", CAST(p.expiry_date AS VARCHAR) AS \"ExpiryDate\", "
            + "CAST(p.threshold AS VARCHAR) AS \"Threshold\", "
            + "COALESCE(s.supplier_name, (SELECT MIN(s2.supplier_name) FROM suppliers s2 "
            + "WHERE LOWER(TRIM(s2.product_name)) = LOWER(TRIM(p.product_name))), '') AS \"Supplier\", "
            + "COALESCE(p.supplier_id, '') AS \"SupplierID\", COALESCE(p.image_url, '') AS \"ImageUrl\", "
            + "CASE WHEN p.quantity <= 0 THEN 'Out of stock' WHEN p.quantity <= p.threshold "
            + "THEN 'Low stock' ELSE 'In stock' END AS \"Status\" "
            + "FROM products p LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id";
    }

    private String supplierSelectSql() {
        return "SELECT supplier_id AS \"SupplierID\", supplier_name AS \"SupplierName\", "
            + "product_name AS \"Product\", category AS \"Category\", CAST(buying_price AS VARCHAR) AS \"BuyingPrice\", "
            + "contact AS \"Contact\", COALESCE(email, '') AS \"Email\", supplier_type AS \"Type\", "
            + "CAST(on_the_way AS VARCHAR) AS \"OnTheWay\", COALESCE(image_url, '') AS \"ImageUrl\" FROM suppliers";
    }

    private RowMapper<Map<String, Object>> productMapper() {
        return (rs, row) -> readRow(rs, PRODUCT_COLUMNS);
    }

    private RowMapper<Map<String, Object>> supplierMapper() {
        return (rs, row) -> readRow(rs, SUPPLIER_COLUMNS);
    }

    private Map<String, Object> readRow(ResultSet rs, List<String> columns) throws SQLException {
        Map<String, Object> result = new LinkedHashMap<>();
        for (String column : columns) result.put(column, rs.getObject(column));
        return result;
    }

    private String required(Map<String, Object> row, String name) {
        String value = NexacroProtocol.value(row, name);
        if (value.isBlank()) throw new ApiException(name + " is required.");
        return value;
    }

    private BigDecimal decimal(Map<String, Object> row, String name) {
        String value = required(row, name);
        try {
            BigDecimal parsed = new BigDecimal(value);
            if (parsed.signum() < 0 || parsed.scale() > 2) throw new NumberFormatException();
            return parsed;
        } catch (NumberFormatException exception) {
            throw new ApiException(name + " must be a non-negative amount with at most two decimal places.");
        }
    }

    private int integer(Map<String, Object> row, String name, int fallback, int minimum, int maximum) {
        String value = NexacroProtocol.value(row, name);
        if (value.isBlank() && fallback >= 0) return fallback;
        try {
            int parsed = Integer.parseInt(value);
            if (parsed < minimum || parsed > maximum) throw new NumberFormatException();
            return parsed;
        } catch (NumberFormatException exception) {
            throw new ApiException(name + " must be a whole number between " + minimum + " and " + maximum + ".");
        }
    }

    private LocalDate date(Map<String, Object> row, String name) {
        try {
            return LocalDate.parse(required(row, name));
        } catch (RuntimeException exception) {
            throw new ApiException(name + " must use YYYY-MM-DD format.");
        }
    }

    private String csv(List<String> columns, List<Map<String, Object>> rows) {
        List<String> lines = new ArrayList<>();
        lines.add(columns.stream().map(this::csvCell).collect(Collectors.joining(",")));
        for (Map<String, Object> row : rows) {
            lines.add(columns.stream().map(column -> csvCell(text(row.get(column)))).collect(Collectors.joining(",")));
        }
        return "\uFEFF" + String.join("\r\n", lines) + "\r\n";
    }

    private String csvCell(String value) {
        return "\"" + value.replace("\"", "\"\"") + "\"";
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private String firstNonBlank(String first, String second) {
        return first == null || first.isBlank() ? second : first;
    }

    private String emptyToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }

    private String extension(String name) {
        int dot = name.lastIndexOf('.');
        return dot < 0 ? "" : name.substring(dot).toLowerCase(Locale.ROOT);
    }

    private void addCodes(List<Map<String, Object>> rows, String type, List<String> values) {
        for (String value : values) rows.add(row("CodeType", type, "Code", value, "Label", value));
    }

    private Map<String, Object> row(Object... values) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (int i = 0; i < values.length; i += 2) result.put(String.valueOf(values[i]), values[i + 1]);
        return result;
    }
}
