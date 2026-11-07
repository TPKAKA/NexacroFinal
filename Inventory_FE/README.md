# Inventory FE (Nexacro)

Open `Inventory_FE.xprj` in Nexacro Studio. `Application.xadl` starts at `Login.xfdl`.

## Implemented forms

- `Login`, `SignUp`
- `InventoryList`, `ProductForm`, `ProductDetail`
- `SupplierList`, `SupplierForm`

The inventory and supplier lists use in-memory sample records so the screens, search, filtering, pagination, sorting, detail navigation, popups and validation can be reviewed before the backend is built. Added records remain available only while the app is open. Login accepts any valid email and non-empty password in preview mode. Sign-up validates input but does not create an account yet.

`lib/InventoryCommon.xjs` provides shared validation, messages, navigation, popups, sample data and `gfnTransaction`. The `api` service points to `http://localhost:8080/`. The supplied `xapi` project currently exposes only employee endpoints, so inventory, supplier and authentication requests have not been connected. Product/supplier image selection is present in the forms; upload and image rendering need their backend endpoints.

The Figma file is viewable in Chrome with viewer access. All seven requested screens were compared visually: this frontend does **not** yet match the Figma layout, blue KANBAN branding, white sidebar, top bar, 1440 × 960 frames or single-column overlay modals. See `../Agent.md` for the screen-by-screen findings. The Figma MCP design-context tool still returns an editor-access error, so supplied assets have not been retrieved.

Run `python validate_frontend.py` to check XML parsing, JavaScript syntax and event handlers.
