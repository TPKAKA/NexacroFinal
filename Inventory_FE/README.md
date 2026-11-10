# Nexacro Inventory Management

The Nexacro N 24 source project is `Inventory_FE.xprj`. Open it in Nexacro Studio and run `Application.xadl`; the initial form is `Login.xfdl`.

## Build the frontend source

Python 3 is used to regenerate the forms and apply the shared layout and inventory transaction contract:

```powershell
python build_frontend.py
python validate_frontend.py
```

The checked-in `.xfdl`, `.xjs`, `.xcss`, `.xadl`, and `.xml` files are the Nexacro source files. `build_frontend.py` recreates the eight forms from the generator and applies the common Dataset definitions, bindings, event handlers, services, and layout. Edit the generator files (`build_frontend.py`, `figma_layout.py`, and `inventory_codegen.py`) when changing generated forms, then rebuild and validate so source and generated output stay aligned.

## Run the API

The API source is in `../xapi/xapi`. Java 17 and Maven 3.6.3 or newer are required. The default `dev` profile uses a local H2 database, creates the schema, and seeds demo products and suppliers:

```powershell
cd ../xapi/xapi
mvn spring-boot:run
```

The health endpoint is `http://localhost:8080/api/health`. The demo database is stored in `xapi/xapi/data/`.

To run against PostgreSQL, create an empty database and set these environment variables before starting the API with the `prod` profile:

```powershell
$env:SPRING_PROFILES_ACTIVE = "prod"
$env:DB_URL = "jdbc:postgresql://localhost:5432/nexacro_inventory"
$env:DB_USERNAME = "postgres"
$env:DB_PASSWORD = "your-local-password"
# Public origin used in returned image URLs. Set this to the API's reachable HTTPS origin in deployment.
$env:APP_PUBLIC_BASE_URL = "http://localhost:8080"
# Comma-separated Nexacro WRE origins allowed to call the API.
$env:APP_CORS_ALLOWED_ORIGINS = "http://localhost:*,http://127.0.0.1:*"
mvn spring-boot:run
```

`schema.sql` creates the required tables and indexes. The `prod` profile does not insert demo records. PostgreSQL connections initialize their session timezone to UTC; the pool connection timeout is 10 seconds and SQL statements time out after 25 seconds. Nexacro transactions wait up to 30 seconds and do not automatically retry, preventing an uncertain write from being replayed. PostgreSQL credentials belong in environment variables and must not be committed.

## Connect the Nexacro project

`Inventory_FE/typedefinition.xml` defines the `api` service at `http://localhost:8080/api/`. Start the API before previewing the app in Nexacro Studio. If the API is hosted elsewhere, update the service URL in `typedefinition.xml`. The Application enables `checkversion` and starts at version `1.0.0`; increment the Application and `theme`, `xcssrc`, `forms`, and `lib` service versions together when publishing changed frontend assets so WRE clients fetch the new files. The API service uses `cachelevel="none"` because its data changes during normal use. Shared code values are cached in memory for one application session and cleared when the session ends.

The frontend sends Nexacro Dataset JSON through `Form.transaction` with data type `3`. The API returns Nexacro JSON envelopes with `ErrorCode`, `ErrorMsg`, and stable Dataset `ColumnInfo` layouts. Shared code in `lib/InventoryCommon.xjs` provides validation, Dataset binding, common codes, messages, navigation, popups, transactions, file transfer, error handling, and logout.

The API supports account registration/login/logout, shared code retrieval, product search/save/detail, supplier search/save, CSV downloads, and image upload. Passwords are stored as PBKDF2 hashes; session tokens are random and stored in the database as SHA-256 hashes. Normal sessions expire after 8 hours and “Remember me” sessions after 30 days.

Images are limited to 5 MB and PNG, JPG, GIF, or WebP. Files are stored under `uploads/` by default and served from `/uploads/`.

## Run checks

```powershell
python Inventory_FE/validate_frontend.py
cd xapi/xapi
mvn test
```

The protocol unit tests cover Nexacro Dataset parsing, case-insensitive values, and success/error response layouts, including empty Datasets. The backend integration tests use an isolated in-memory H2 database and exercise authentication, Dataset JSON, product/supplier transactions, filtering, details, export, upload, validation, and logout.

Password recovery currently returns instructions to contact the workspace administrator; no mail delivery service is configured.
