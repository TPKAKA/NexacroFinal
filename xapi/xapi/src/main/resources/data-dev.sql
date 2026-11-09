INSERT INTO suppliers (supplier_id, supplier_name, product_name, category, buying_price, contact, email, supplier_type, on_the_way)
SELECT 'SUP-001', 'Tech Supplies', 'Wireless Mouse', 'Electronics', 24.00, '0900000101', 'sales@tech.test', 'Taking return', 20
WHERE NOT EXISTS (SELECT 1 FROM suppliers WHERE supplier_id = 'SUP-001');
INSERT INTO suppliers (supplier_id, supplier_name, product_name, category, buying_price, contact, email, supplier_type, on_the_way)
SELECT 'SUP-002', 'Nova Trading', 'USB-C Hub', 'Electronics', 38.50, '0900000102', 'hello@nova.test', 'Not taking return', 12
WHERE NOT EXISTS (SELECT 1 FROM suppliers WHERE supplier_id = 'SUP-002');
INSERT INTO suppliers (supplier_id, supplier_name, product_name, category, buying_price, contact, email, supplier_type, on_the_way)
SELECT 'SUP-003', 'Bright Goods', 'Desk Lamp', 'Office', 42.00, '0900000103', 'contact@bright.test', 'Taking return', 0
WHERE NOT EXISTS (SELECT 1 FROM suppliers WHERE supplier_id = 'SUP-003');

INSERT INTO products (product_id, product_name, category, buying_price, quantity, unit, expiry_date, threshold, image_url)
SELECT 'PRD-001', 'Wireless Mouse', 'Electronics', 24.00, 120, 'pcs', DATE '2027-12-31', 20, NULL
WHERE NOT EXISTS (SELECT 1 FROM products WHERE product_id = 'PRD-001');
INSERT INTO products (product_id, product_name, category, buying_price, quantity, unit, expiry_date, threshold, image_url)
SELECT 'PRD-002', 'USB-C Hub', 'Electronics', 38.50, 8, 'pcs', DATE '2027-12-31', 15, NULL
WHERE NOT EXISTS (SELECT 1 FROM products WHERE product_id = 'PRD-002');
INSERT INTO products (product_id, product_name, category, buying_price, quantity, unit, expiry_date, threshold, image_url)
SELECT 'PRD-003', 'Desk Lamp', 'Office', 42.00, 0, 'pcs', DATE '2028-06-30', 10, NULL
WHERE NOT EXISTS (SELECT 1 FROM products WHERE product_id = 'PRD-003');
INSERT INTO products (product_id, product_name, category, buying_price, quantity, unit, expiry_date, threshold, image_url)
SELECT 'PRD-004', 'Notebook A5', 'Stationery', 3.20, 220, 'pcs', DATE '2028-12-31', 40, NULL
WHERE NOT EXISTS (SELECT 1 FROM products WHERE product_id = 'PRD-004');
INSERT INTO products (product_id, product_name, category, buying_price, quantity, unit, expiry_date, threshold, image_url)
SELECT 'PRD-005', 'Water Bottle', 'Lifestyle', 9.90, 65, 'pcs', DATE '2027-08-30', 18, NULL
WHERE NOT EXISTS (SELECT 1 FROM products WHERE product_id = 'PRD-005');

UPDATE products SET supplier_id = 'SUP-001' WHERE product_id = 'PRD-001' AND supplier_id IS NULL;
UPDATE products SET supplier_id = 'SUP-002' WHERE product_id = 'PRD-002' AND supplier_id IS NULL;
UPDATE products SET supplier_id = 'SUP-003' WHERE product_id = 'PRD-003' AND supplier_id IS NULL;

INSERT INTO stock_locations (product_id, location_name, quantity)
SELECT 'PRD-001', 'Main Warehouse', 120 WHERE NOT EXISTS
    (SELECT 1 FROM stock_locations WHERE product_id = 'PRD-001' AND location_name = 'Main Warehouse');
INSERT INTO stock_locations (product_id, location_name, quantity)
SELECT 'PRD-002', 'Main Warehouse', 8 WHERE NOT EXISTS
    (SELECT 1 FROM stock_locations WHERE product_id = 'PRD-002' AND location_name = 'Main Warehouse');
INSERT INTO stock_locations (product_id, location_name, quantity)
SELECT 'PRD-003', 'Main Warehouse', 0 WHERE NOT EXISTS
    (SELECT 1 FROM stock_locations WHERE product_id = 'PRD-003' AND location_name = 'Main Warehouse');
INSERT INTO stock_locations (product_id, location_name, quantity)
SELECT 'PRD-004', 'Main Warehouse', 220 WHERE NOT EXISTS
    (SELECT 1 FROM stock_locations WHERE product_id = 'PRD-004' AND location_name = 'Main Warehouse');
INSERT INTO stock_locations (product_id, location_name, quantity)
SELECT 'PRD-005', 'Main Warehouse', 65 WHERE NOT EXISTS
    (SELECT 1 FROM stock_locations WHERE product_id = 'PRD-005' AND location_name = 'Main Warehouse');

INSERT INTO inventory_events (product_id, event_type, quantity_change, description)
SELECT product_id, 'INITIAL', quantity, 'Opening stock' FROM products p
WHERE NOT EXISTS (SELECT 1 FROM inventory_events e WHERE e.product_id = p.product_id AND e.event_type = 'INITIAL');
