"""Finalize generated Nexacro forms with the inventory Dataset and transaction contract."""
from pathlib import Path
from xml.sax.saxutils import escape
import re


PRODUCT_COLUMNS = [
    "ProductID", "ProductName", "Category", "BuyingPrice", "Quantity", "Unit",
    "ExpiryDate", "Threshold", "Supplier", "SupplierID", "ImageUrl", "Status",
]
DETAIL_COLUMNS = [
    "ProductID", "ProductIDLabel", "ProductName", "Category", "BuyingPrice", "Quantity",
    "Unit", "ExpiryDate", "Threshold", "Supplier", "SupplierInfo", "SupplierID",
    "ImageUrl", "Status", "OverviewText",
]
SUPPLIER_COLUMNS = [
    "SupplierID", "SupplierName", "Product", "Category", "BuyingPrice", "Contact",
    "Email", "Type", "OnTheWay", "ImageUrl",
]
EVENT_COLUMNS = ["EventID", "Type", "QuantityChange", "Description", "CreatedAt"]


def dataset_markup(name, columns, event=None):
    attrs = f'id="{name}"'
    if event:
        events = event.items() if isinstance(event, dict) else [("onrowsetchanged", event)]
        attrs += "".join(f' {event_name}="{handler}"' for event_name, handler in events)
    cols = "".join(f'<Column id="{escape(column)}" type="STRING" size="1024"/>' for column in columns)
    return f'<Dataset {attrs}><ColumnInfo>{cols}</ColumnInfo></Dataset>'


def replace_script(source, body):
    script = '<Script type="xscript5.1"><![CDATA[include "lib::InventoryCommon.xjs";\n' + body.strip() + '\n]]></Script>'
    return re.sub(
        r'<Script type="xscript5\.1"><!\[CDATA\[.*?\]\]></Script>',
        lambda _: script,
        source,
        count=1,
        flags=re.S,
    )


def ensure_datasets(path, datasets):
    source = path.read_text(encoding="utf-8")
    for name, columns, event in datasets:
        markup = dataset_markup(name, columns, event)
        pattern = rf'<Dataset\b[^>]*\bid="{re.escape(name)}"[^>]*>.*?</Dataset>'
        if re.search(pattern, source, flags=re.S):
            source = re.sub(pattern, markup, source, count=1, flags=re.S)
        else:
            source = source.replace("</Objects>", markup + "</Objects>", 1)
    path.write_text(source, encoding="utf-8")


def set_bindings(path, bindings):
    source = path.read_text(encoding="utf-8")
    source = re.sub(r'<BindItem\b[^>]*/>', "", source)
    source = re.sub(r'<Bind\b[^>]*>.*?</Bind>', "", source, flags=re.S)
    items = "".join(
        f'<BindItem id="bind{index}" compid="{escape(comp)}" propid="{escape(prop)}" '
        f'datasetid="{escape(dataset)}" columnid="{escape(column)}"/>'
        for index, (comp, prop, dataset, column) in enumerate(bindings)
    )
    markup = f"<Bind>{items}</Bind>" if items else ""
    source = source.replace("</Script></Form>", "</Script>" + markup + "</Form>", 1)
    path.write_text(source, encoding="utf-8")


def set_script(path, script):
    path.write_text(replace_script(path.read_text(encoding="utf-8"), script), encoding="utf-8")


def grid_markup(name, dataset, x, y, width, height, headings, ratios, field_names=None):
    field_names = headings if field_names is None else field_names
    if len(headings) != len(field_names) or len(headings) != len(ratios):
        raise ValueError(f"Grid {name} headings, fields, and width ratios must have the same length")
    total = sum(ratios)
    sizes = [int(width * ratio / total) for ratio in ratios]
    sizes[-1] += width - sum(sizes)
    columns = "".join(f'<Column size="{size}"/>' for size in sizes)
    head = "".join(f'<Cell col="{i}" text="{escape(label)}"/>' for i, label in enumerate(headings))
    body = "".join(f'<Cell col="{i}" text="bind:{escape(column)}"/>' for i, column in enumerate(field_names))
    return (
        f'<Grid id="{name}" binddataset="{dataset}" left="{x}" top="{y}" width="{width}" height="{height}" '
        'cssclass="dataGrid" autofittype="col" selecttype="row">'
        f'<Formats><Format id="default"><Columns>{columns}</Columns>'
        '<Rows><Row size="36" band="head"/><Row size="32"/></Rows>'
        f'<Band id="head">{head}</Band><Band id="body">{body}</Band>'
        '</Format></Formats></Grid>'
    )


def finalize_detail_layout(path):
    source = path.read_text(encoding="utf-8")
    stock_grid = grid_markup(
        "grdStockLocations", "dsStockLocations", 354, 762, 610, 95,
        ["Location", "Quantity", "Unit"], [48, 26, 26],
    )
    source = re.sub(r'<Static\b[^>]*\bid="staStock"[^>]*/>', stock_grid, source, count=1)
    activity_grid = grid_markup(
        "grdActivities", "dsActivity", 972, 585, 420, 270,
        ["Type", "Change", "Description", "Created at"], [18, 15, 39, 28],
        ["Type", "QuantityChange", "Description", "CreatedAt"],
    )
    title_markup = '<Static id="staActivityTitle" left="972" top="560" width="420" height="35" text="Activity" cssclass="sectionTitleSmall"/>'
    title_pattern = r'<Static\b[^>]*\bid="staActivityTitle"[^>]*/>'
    if re.search(title_pattern, source):
        source = re.sub(title_pattern, title_markup, source, count=1)
    activity_pattern = r'<Grid\b[^>]*\bid="grdActivities"[^>]*>.*?</Grid>'
    if re.search(activity_pattern, source, flags=re.S):
        source = re.sub(activity_pattern, activity_grid, source, count=1, flags=re.S)
        if title_markup not in source:
            source = source.replace(activity_grid, title_markup + activity_grid, 1)
    else:
        source = source.replace("</Layout>", title_markup + activity_grid + "</Layout>", 1)
    source = source.replace('oncelldblclick="onOpenProduct"', 'oncellclick="onOpenProduct"')
    path.write_text(source, encoding="utf-8")


COMMON_SCRIPT = r"""
/**
 * Check whether a value is empty after trimming whitespace.
 * @param {*} value Value to inspect.
 * @returns {boolean} True when the value is null, undefined, or blank.
 */
this.gfnEmpty = function(value) {
  return value === null || value === undefined || String(value).replace(/^\s+|\s+$/g, "") === "";
};
/**
 * Check the basic structure of an email address before submission.
 * @param {*} value Address to validate.
 * @returns {boolean} True when the address has a local part and domain.
 */
this.gfnEmail = function(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || ""));
};
/**
 * Validate a non-negative numeric input.
 * @param {*} value Value to validate.
 * @returns {boolean} True when value is present and numeric.
 */
this.gfnNumber = function(value) {
  return !this.gfnEmpty(value) && !isNaN(Number(value)) && Number(value) >= 0;
};
/**
 * Validate a real calendar date formatted as YYYY-MM-DD.
 * @param {*} value Date string to validate.
 * @returns {boolean} True when the date exists in the Gregorian calendar.
 */
this.gfnDate = function(value) {
  var text = String(value || "").replace(/^\s+|\s+$/g, "");
  var match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  if (!match) return false;
  var year = Number(match[1]);
  var month = Number(match[2]);
  var day = Number(match[3]);
  if (year < 1 || month < 1 || month > 12) return false;
  var leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  var daysByMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return day >= 1 && day <= daysByMonth[month - 1];
};
/**
 * Show a Nexacro alert message.
 * @param {string} message Text displayed to the user.
 * @returns {void}
 */
this.gfnMessage = function(message) { this.alert(message); };
/**
 * Navigate the current owner frame to a registered form.
 * @param {string} name Form service name without the .xfdl suffix.
 * @returns {void}
 */
this.gfnNavigate = function(name) {
  this.getOwnerFrame().set_formurl("forms::" + name + ".xfdl");
};
/**
 * Set a Dataset's first row from a plain object, adding a row if needed.
 * Only columns defined by the Dataset are copied.
 * @param {nexacro.Dataset} dataset Target Dataset.
 * @param {Object<string, *>} values Values keyed by Dataset column id.
 * @returns {number} Row index updated.
 */
this.gfnBindRecord = function(dataset, values) {
  var row = dataset.rowcount ? 0 : dataset.addRow();
  for (var key in values) {
    if (values.hasOwnProperty(key) && dataset.getColumnInfo(key)) dataset.setColumn(row, key, values[key]);
  }
  dataset.rowposition = row;
  return row;
};
/**
 * Load shared codes into this form's dsCodes Dataset.
 * Successful responses are cached in memory for the current application session.
 * @param {string} callback Form callback name.
 * @returns {*} Transaction handle, or null when the cached Dataset is used.
 */
this.gfnLoadCodes = function(callback) {
  var app = nexacro.getApplication();
  if (app.inventoryCodeCache && this.dsCodes) {
    this.dsCodes.loadXML(app.inventoryCodeCache, true);
    var handler = callback || "onCodesLoaded";
    if (typeof this[handler] === "function") this[handler]("common-codes-cache", 0, "");
    return null;
  }
  return this.gfnTransaction("common-codes", "codes/list", "", "dsCodes=dsCodes", "", callback || "onCodesLoaded");
};
/**
 * Cache a non-empty common-code Dataset for this application session.
 * @returns {boolean} True when a Dataset was stored.
 */
this.gfnCacheCodes = function() {
  if (!this.dsCodes || this.dsCodes.rowcount < 1) return false;
  nexacro.getApplication().inventoryCodeCache = this.dsCodes.saveXML();
  return true;
};
/**
 * Send one Nexacro Dataset transaction to the API service.
 * Dataset JSON is used with bCompress=false; this setting is compression only and does not encrypt traffic.
 * @param {string} id Unique transaction id.
 * @param {string} path API path relative to api::.
 * @param {string} input Input Dataset mapping.
 * @param {string} output Output Dataset mapping.
 * @param {string} args Nexacro transaction arguments.
 * @param {string} callback Form callback name.
 * @returns {*} Nexacro transaction handle.
 */
this.gfnTransaction = function(id, path, input, output, args, callback) {
  var app = nexacro.getApplication();
  var parameters = String(args || "");
  if (app.sessionToken && parameters.indexOf("sessionToken=") < 0) {
    parameters += (parameters ? " " : "") + "sessionToken=" + app.sessionToken;
  }
  return this.transaction(id, "api::" + path, input || "", output || "", parameters,
                          callback || "onTransaction", true, 3, false);
};
/**
 * Open a modal child form from the forms service.
 * @param {string} name Form service name.
 * @param {number} width Popup width in pixels.
 * @param {number} height Popup height in pixels.
 * @param {string} callback Parent form callback name.
 * @returns {void}
 */
this.gfnPopup = function(name, width, height, callback) {
  var child = new ChildFrame("popup" + name, 0, 0, width, height);
  child.formurl = "forms::" + name + ".xfdl";
  child.openalign = "center middle";
  child.showtitlebar = false;
  child.dragmovetype = "all";
  child.showModal(this.getOwnerFrame(), {}, this, callback);
};
/**
 * Download a protected file through a Nexacro FileDownTransfer.
 * @param {string} path API path relative to api::.
 * @param {string} filename Local filename.
 * @param {Object<string, string>} parameters Additional POST parameters.
 * @returns {void}
 */
this.gfnDownload = function(path, filename, parameters) {
  var app = nexacro.getApplication();
  if (!app.sessionToken) {
    this.gfnMessage("Your session has expired. Sign in again.");
    this.gfnNavigate("Login");
    return;
  }
  if (!this._inventoryFileDownTransfer) {
    this._inventoryFileDownTransfer = new nexacro.FileDownTransfer("inventoryFileDownTransfer", this);
    this.addChild("inventoryFileDownTransfer", this._inventoryFileDownTransfer);
  }
  var transfer = this._inventoryFileDownTransfer;
  transfer.downloadfilename = filename;
  transfer.clearPostDataList();
  transfer.setPostData("sessionToken", app.sessionToken);
  if (parameters) {
    for (var key in parameters) {
      if (parameters.hasOwnProperty(key)) transfer.setPostData(key, parameters[key]);
    }
  }
  transfer.download("api::" + path);
};
/**
 * Display an API error and return to login when the session has expired.
 * @param {number} errorCode Nexacro transaction error code.
 * @param {string} errorMessage Server-provided error message.
 * @returns {void}
 */
this.gfnHandleApiError = function(errorCode, errorMessage) {
  var message = String(errorMessage || "The request could not be completed.");
  this.gfnMessage(message);
  if (message.toLowerCase().indexOf("session has expired") >= 0) {
    var app = nexacro.getApplication();
    app.sessionToken = "";
    app.currentUserName = "";
    app.inventoryCodeCache = "";
    this.gfnNavigate("Login");
  }
};
/**
 * Close the server session and clear the application session state.
 * @returns {*} Transaction handle, or undefined when no session exists.
 */
this.gfnLogout = function() {
  var app = nexacro.getApplication();
  if (!app.sessionToken) {
    this.onLogoutResult("auth-logout", 0, "");
    return;
  }
  this.dsLogout.clearData();
  var row = this.dsLogout.addRow();
  this.dsLogout.setColumn(row, "SessionToken", app.sessionToken);
  this.gfnTransaction("auth-logout", "auth/logout", "dsLogout=dsLogout", "", "", "onLogoutResult");
};
this.onLogoutResult = function(serviceId, errorCode, errorMessage) {
  var app = nexacro.getApplication();
  if (errorCode < 0 && String(errorMessage || "").toLowerCase().indexOf("session has expired") < 0) {
    this.gfnMessage(errorMessage || "The session could not be closed on the server.");
    return;
  }
  app.sessionToken = "";
  app.currentUserName = "";
  app.inventoryCodeCache = "";
  app.selectedProductId = "";
  app.editProductId = "";
  this.gfnNavigate("Login");
};
"""


LOGIN_SCRIPT = r"""
this.onLoad = function() {
  this.gfnBindRecord(this.dsLogin, { Email: "", Password: "", RememberMe: "0" });
  this.gfnBindRecord(this.dsForgot, { Email: "" });
};
this.onLogin = function() {
  var row = this.dsLogin.rowposition < 0 ? 0 : this.dsLogin.rowposition;
  var email = this.dsLogin.getColumn(row, "Email");
  var password = this.dsLogin.getColumn(row, "Password");
  if (!this.gfnEmail(email) || this.gfnEmpty(password)) return this.gfnMessage("Enter a valid email and password.");
  this.gfnTransaction("auth-login", "auth/login", "dsLogin=dsLogin", "dsSession=dsSession", "", "onLoginResult");
};
this.onLoginResult = function(serviceId, errorCode, errorMessage) {
  if (errorCode < 0 || !this.dsSession.rowcount) return this.gfnHandleApiError(errorCode, errorMessage);
  var app = nexacro.getApplication();
  app.sessionToken = this.dsSession.getColumn(0, "Token");
  app.currentUserName = this.dsSession.getColumn(0, "Name");
  this.gfnNavigate("InventoryList");
};
this.onSignUp = function() { this.gfnNavigate("SignUp"); };
this.onForgot = function() {
  var row = this.dsLogin.rowposition < 0 ? 0 : this.dsLogin.rowposition;
  var email = this.dsLogin.getColumn(row, "Email");
  if (!this.gfnEmail(email)) return this.gfnMessage("Enter your account email first.");
  this.gfnBindRecord(this.dsForgot, { Email: email });
  this.gfnTransaction("auth-forgot", "auth/forgot", "dsForgot=dsForgot", "dsResult=dsResult", "", "onForgotResult");
};
this.onForgotResult = function(serviceId, errorCode, errorMessage) {
  if (errorCode < 0) return this.gfnHandleApiError(errorCode, errorMessage);
  this.gfnMessage(this.dsResult.getColumn(0, "Message"));
};
this.onLoginDatasetChanged = function(obj, e) {
  if (e.reason === nexacro.Dataset.REASON_CHANGESTATUS) this.loginInputChanged = true;
};
"""


SIGNUP_SCRIPT = r"""
this.onLoad = function() {
  this.gfnBindRecord(this.dsSignup, { Name: "", Email: "", Password: "", Confirm: "" });
};
this.onCreate = function() {
  var row = this.dsSignup.rowposition < 0 ? 0 : this.dsSignup.rowposition;
  var name = this.dsSignup.getColumn(row, "Name");
  var email = this.dsSignup.getColumn(row, "Email");
  var password = this.dsSignup.getColumn(row, "Password");
  var confirm = this.dsSignup.getColumn(row, "Confirm");
  if (this.gfnEmpty(name)) return this.gfnMessage("Name is required.");
  if (!this.gfnEmail(email)) return this.gfnMessage("Enter a valid email address.");
  if (this.gfnEmpty(password) || password.length < 8) return this.gfnMessage("Password must have at least 8 characters.");
  if (password !== confirm) return this.gfnMessage("Passwords do not match.");
  this.gfnTransaction("auth-signup", "auth/signup", "dsSignup=dsSignup", "dsSession=dsSession", "", "onSignupResult");
};
this.onSignupResult = function(serviceId, errorCode, errorMessage) {
  if (errorCode < 0 || !this.dsSession.rowcount) return this.gfnHandleApiError(errorCode, errorMessage);
  var app = nexacro.getApplication();
  app.sessionToken = this.dsSession.getColumn(0, "Token");
  app.currentUserName = this.dsSession.getColumn(0, "Name");
  this.gfnNavigate("InventoryList");
};
this.onBack = function() { this.gfnNavigate("Login"); };
this.onSignupDatasetChanged = function(obj, e) {
  if (e.reason === nexacro.Dataset.REASON_CHANGESTATUS) this.signupInputChanged = true;
};
"""


INVENTORY_SCRIPT = r"""
this.page = 0;
this.pageSize = 10;
this.searchText = "";
this.statusFilter = "";
this.onLoad = function() {
  if (!nexacro.getApplication().sessionToken) return this.gfnNavigate("Login");
  this.refresh();
};
this.onNavInventoryList = function() {};
this.onNavSupplierList = function() { this.gfnNavigate("SupplierList"); };
this.onLogout = function() {
  this.gfnLogout();
};
this.onComingSoon = function() { this.gfnMessage("This section is not part of the inventory requirements."); };
this.refresh = function() {
  var row = this.gfnBindRecord(this.dsSearch, {});
  this.dsSearch.setColumn(row, "Search", this.searchText);
  this.dsSearch.setColumn(row, "Status", this.statusFilter);
  this.dsSearch.setColumn(row, "Page", String(this.page));
  this.dsSearch.setColumn(row, "PageSize", String(this.pageSize));
  this.gfnTransaction("products-search", "products/search", "dsSearch=dsSearch",
    "dsProducts=dsProducts dsSummary=dsSummary", "", "onProductsLoaded");
};
this.onProductsLoaded = function(serviceId, errorCode, errorMessage) {
  if (errorCode < 0) return this.gfnHandleApiError(errorCode, errorMessage);
  this.refreshPageLabel();
  this.renderSummary(this.dsSummary);
};
this.refreshPageLabel = function() {
  var count = this.dsProducts.rowcount;
  var total = this.dsSummary.rowcount ? Number(this.dsSummary.getColumn(0, "TotalProducts")) : 0;
  var start = count ? this.page * this.pageSize + 1 : 0;
  var end = this.page * this.pageSize + count;
  this.staPage.set_text("Showing " + start + "–" + end + " of " + total + " products");
};
this.onProductsChanged = function(obj, e) {
  if (e.reason === nexacro.Dataset.REASON_ASSIGN || e.reason === nexacro.Dataset.REASON_APPEND ||
      e.reason === nexacro.Dataset.REASON_MERGE) this.refreshPageLabel();
};
this.onSummaryChanged = function(obj, e) {
  if (e.reason !== nexacro.Dataset.REASON_ASSIGN && e.reason !== nexacro.Dataset.REASON_APPEND &&
      e.reason !== nexacro.Dataset.REASON_MERGE) return;
  this.renderSummary(obj);
};
this.onSummaryLoaded = function(obj, e) {
  if (e.reason !== nexacro.Dataset.REASON_LOAD && e.reason !== nexacro.Dataset.REASON_LOADCONTENT) return;
  this.renderSummary(obj);
};
this.renderSummary = function(obj) {
  if (!obj.rowcount) return;
  this.staCategories.set_text(obj.getColumn(0, "Categories"));
  this.staTotal.set_text(obj.getColumn(0, "TotalProducts"));
  this.staTopSelling.set_text(obj.getColumn(0, "TopSelling"));
  this.staLow.set_text(obj.getColumn(0, "LowStocks"));
  this.staOut.set_text(obj.getColumn(0, "OutOfStock") + " out");
  this.notestaCategories.set_text("Product categories");
  this.notestaTotal.set_text("Products in inventory");
  this.notestaTopSelling.set_text(obj.getColumn(0, "TopSellingNote"));
  this.notestaLow.set_text("At or below threshold");
};
this.onSearch = function() {
  this.searchText = String(this.edtSearch.value || "").toLowerCase();
  this.page = 0;
  this.refresh();
};
this.onFilter = function() {
  var filters = ["", "In stock", "Low stock", "Out of stock"];
  this.statusFilter = filters[(filters.indexOf(this.statusFilter) + 1) % filters.length];
  this.btnFilter.set_text(this.statusFilter || "Filters");
  this.page = 0;
  this.refresh();
};
this.onPrev = function() { if (this.page > 0) { this.page--; this.refresh(); } };
this.onNext = function() {
  var total = this.dsSummary.rowcount ? Number(this.dsSummary.getColumn(0, "TotalProducts")) : 0;
  if ((this.page + 1) * this.pageSize < total) { this.page++; this.refresh(); }
};
this.onOpenProduct = function(obj, e) {
  if (!e || e.row < 0 || e.row >= this.dsProducts.rowcount) return;
  nexacro.getApplication().selectedProductId = this.dsProducts.getColumn(e.row, "ProductID");
  this.gfnNavigate("ProductDetail");
};
this.onAdd = function() {
  nexacro.getApplication().editProductId = "";
  this.gfnPopup("ProductForm", 500, 800, "onProductSaved");
};
this.onProductSaved = function(serviceId, value) { if (value) this.refresh(); };
this.onDownload = function() {
  this.gfnDownload("products/export.csv", "products.csv",
    { search: this.searchText, status: this.statusFilter });
};
"""


SUPPLIER_LIST_SCRIPT = r"""
this.page = 0;
this.pageSize = 12;
this.query = "";
this.typeFilter = "";
this.sortField = "SupplierName";
this.sortOrder = "ASC";
this.onLoad = function() {
  if (!nexacro.getApplication().sessionToken) return this.gfnNavigate("Login");
  this.refresh();
};
this.onNavInventoryList = function() { this.gfnNavigate("InventoryList"); };
this.onNavSupplierList = function() {};
this.onLogout = function() {
  this.gfnLogout();
};
this.onComingSoon = function() { this.gfnMessage("This section is not part of the inventory requirements."); };
this.refresh = function() {
  var row = this.gfnBindRecord(this.dsSearch, {});
  this.dsSearch.setColumn(row, "Search", this.query);
  this.dsSearch.setColumn(row, "Type", this.typeFilter);
  this.dsSearch.setColumn(row, "Page", String(this.page));
  this.dsSearch.setColumn(row, "PageSize", String(this.pageSize));
  this.dsSearch.setColumn(row, "SortField", this.sortField);
  this.dsSearch.setColumn(row, "SortOrder", this.sortOrder);
  this.gfnTransaction("suppliers-search", "suppliers/search", "dsSearch=dsSearch",
    "dsSuppliers=dsSuppliers dsSupplierSummary=dsSupplierSummary", "", "onSuppliersLoaded");
};
this.onSuppliersLoaded = function(serviceId, errorCode, errorMessage) {
  if (errorCode < 0) return this.gfnHandleApiError(errorCode, errorMessage);
  this.refreshPageLabel();
};
this.refreshPageLabel = function() {
  var total = this.dsSupplierSummary.rowcount ? Number(this.dsSupplierSummary.getColumn(0, "TotalSuppliers")) : 0;
  var pages = Math.max(1, Math.ceil(total / this.pageSize));
  this.staCount.set_text(total + " suppliers · Page " + (this.page + 1) + " of " + pages);
};
this.onSuppliersChanged = function(obj, e) {
  if (e.reason === nexacro.Dataset.REASON_ASSIGN || e.reason === nexacro.Dataset.REASON_APPEND ||
      e.reason === nexacro.Dataset.REASON_MERGE) this.refreshPageLabel();
};
this.onSupplierSummaryChanged = function(obj, e) {
  if (e.reason === nexacro.Dataset.REASON_ASSIGN || e.reason === nexacro.Dataset.REASON_APPEND ||
      e.reason === nexacro.Dataset.REASON_MERGE) this.refreshPageLabel();
};
this.onSearch = function() {
  this.query = String(this.edtSearch.value || "").toLowerCase();
  this.page = 0;
  this.refresh();
};
this.onFilter = function() {
  var filters = ["", "Taking return", "Not taking return"];
  this.typeFilter = filters[(filters.indexOf(this.typeFilter) + 1) % filters.length];
  this.btnFilter.set_text(this.typeFilter || "Filters");
  this.page = 0;
  this.refresh();
};
this.onSort = function(obj, e) {
  var fields = ["SupplierName", "Product", "Contact", "Email", "Type", "OnTheWay"];
  if (!e || e.cell < 0 || !fields[e.cell]) return;
  var field = fields[e.cell];
  this.sortOrder = this.sortField === field && this.sortOrder === "ASC" ? "DESC" : "ASC";
  this.sortField = field;
  this.page = 0;
  this.refresh();
};
this.onPrev = function() { if (this.page > 0) { this.page--; this.refresh(); } };
this.onNext = function() {
  var total = this.dsSupplierSummary.rowcount ? Number(this.dsSupplierSummary.getColumn(0, "TotalSuppliers")) : 0;
  if ((this.page + 1) * this.pageSize < total) { this.page++; this.refresh(); }
};
this.onAdd = function() { this.gfnPopup("SupplierForm", 500, 730, "onSupplierSaved"); };
this.onSupplierSaved = function(serviceId, value) { if (value) this.refresh(); };
this.onDownload = function() {
  this.gfnDownload("suppliers/export.csv", "suppliers.csv", { search: this.query, type: this.typeFilter });
};
"""


PRODUCT_FORM_SCRIPT = r"""
this.isEditing = false;
this.imageUploaded = false;
this.onLoad = function() {
  var app = nexacro.getApplication();
  this.isEditing = !this.gfnEmpty(app.editProductId);
  this.gfnBindRecord(this.dsProduct, {
    ProductID: "", ProductName: "", Category: "Electronics", BuyingPrice: "0",
    Quantity: "0", Unit: "pcs", ExpiryDate: "2027-12-31", Threshold: "0",
    Supplier: "", SupplierID: "", ImageUrl: "", Status: ""
  });
  this.gfnBindRecord(this.dsRequest, { ProductID: app.editProductId || "" });
  this.gfnLoadCodes("onProductCodesLoaded");
  if (this.isEditing) {
    this.staFormTitle.set_text("Edit Product");
    this.btnSave.set_text("Save changes");
    this.gfnTransaction("product-edit-load", "products/detail", "dsRequest=dsRequest",
      "dsProduct=dsProduct dsProductDetail=dsProductDetail", "", "onEditProductLoaded");
  }
};
this.onProductCodesLoaded = function(serviceId, errorCode, errorMessage) {
  if (errorCode < 0) return this.gfnHandleApiError(errorCode, errorMessage);
  this.gfnCacheCodes();
  this.dsCategory.clearData();
  this.dsUnit.clearData();
  for (var i = 0; i < this.dsCodes.rowcount; i++) {
    var type = this.dsCodes.getColumn(i, "CodeType");
    var value = this.dsCodes.getColumn(i, "Code");
    var target = type === "Category" ? this.dsCategory : (type === "Unit" ? this.dsUnit : null);
    if (target) {
      var row = target.addRow();
      target.setColumn(row, "Code", value);
      target.setColumn(row, "Label", value);
    }
  }
};
this.onEditProductLoaded = function(serviceId, errorCode, errorMessage) {
  if (errorCode < 0 || !this.dsProduct.rowcount) return this.gfnHandleApiError(errorCode, errorMessage);
};
this.onImageChanged = function() { this.imageUploaded = false; };
this.onSave = function() {
  var row = this.dsProduct.rowposition < 0 ? 0 : this.dsProduct.rowposition;
  var fields = ["ProductName", "ProductID", "Category", "BuyingPrice", "Quantity", "Unit", "ExpiryDate", "Threshold"];
  for (var i = 0; i < fields.length; i++) {
    if (this.gfnEmpty(this.dsProduct.getColumn(row, fields[i]))) return this.gfnMessage(fields[i] + " is required.");
  }
  if (!this.gfnNumber(this.dsProduct.getColumn(row, "BuyingPrice")) ||
      !this.gfnNumber(this.dsProduct.getColumn(row, "Quantity")) ||
      !this.gfnNumber(this.dsProduct.getColumn(row, "Threshold"))) {
    return this.gfnMessage("Price, quantity and threshold must be non-negative numbers.");
  }
  if (!this.gfnDate(this.dsProduct.getColumn(row, "ExpiryDate"))) return this.gfnMessage("Expiry date must be YYYY-MM-DD.");
  if (this.uplImage.getItemCount(true) > 0 && !this.imageUploaded) {
    var token = nexacro.getApplication().sessionToken;
    if (!token) return this.gfnHandleApiError(-1, "Your session has expired. Sign in again.");
    this.uplImage.upload("api::uploads/image?sessionToken=" + token);
    return;
  }
  this.submitProduct();
};
this.onImageUploadSuccess = function(obj, e) {
  var uploaded = e && e.datasets;
  var result = null;
  if (uploaded && uploaded.length) result = uploaded[0];
  else if (uploaded && uploaded.getCount && uploaded.getCount() > 0) result = uploaded.getItem(0);
  if (!result || !result.rowcount) return this.gfnMessage("The image upload returned no image URL.");
  var url = result.getColumn(0, "ImageUrl");
  if (this.gfnEmpty(url)) return this.gfnMessage("The image upload returned no image URL.");
  var row = this.dsProduct.rowposition < 0 ? 0 : this.dsProduct.rowposition;
  this.dsProduct.setColumn(row, "ImageUrl", url);
  this.imageUploaded = true;
  this.submitProduct();
};
this.onImageUploadError = function(obj, e) {
  this.gfnMessage(e && e.errormsg ? e.errormsg : "The image could not be uploaded.");
};
this.submitProduct = function() {
  var mode = this.isEditing ? "mode=update" : "";
  this.gfnTransaction("product-save", "products/save", "dsProduct=dsProduct", "dsSaved=dsSaved",
    mode, "onProductSaveResult");
};
this.onProductSaveResult = function(serviceId, errorCode, errorMessage) {
  if (errorCode < 0 || !this.dsSaved.rowcount) return this.gfnHandleApiError(errorCode, errorMessage);
  nexacro.getApplication().editProductId = "";
  this.close("saved");
};
this.onCancel = function() {
  nexacro.getApplication().editProductId = "";
  this.close("");
};
this.onProductDatasetChanged = function(obj, e) {
  if (e.reason === nexacro.Dataset.REASON_CHANGESTATUS) this.productInputChanged = true;
};
"""


SUPPLIER_FORM_SCRIPT = r"""
this.imageUploaded = false;
this.onLoad = function() {
  this.gfnBindRecord(this.dsSupplier, {
    SupplierID: "", SupplierName: "", Product: "", Category: "Electronics",
    BuyingPrice: "0", Contact: "", Email: "", Type: "Taking return",
    OnTheWay: "0", ImageUrl: ""
  });
  this.gfnLoadCodes("onSupplierCodesLoaded");
};
this.onSupplierCodesLoaded = function(serviceId, errorCode, errorMessage) {
  if (errorCode < 0) return this.gfnHandleApiError(errorCode, errorMessage);
  this.gfnCacheCodes();
  this.dsCategory.clearData();
  this.dsType.clearData();
  for (var i = 0; i < this.dsCodes.rowcount; i++) {
    var type = this.dsCodes.getColumn(i, "CodeType");
    var value = this.dsCodes.getColumn(i, "Code");
    var target = type === "Category" ? this.dsCategory : (type === "SupplierType" ? this.dsType : null);
    if (target) {
      var row = target.addRow();
      target.setColumn(row, "Code", value);
      target.setColumn(row, "Label", value);
    }
  }
};
this.onImageChanged = function() { this.imageUploaded = false; };
this.onSave = function() {
  var row = this.dsSupplier.rowposition < 0 ? 0 : this.dsSupplier.rowposition;
  var fields = ["SupplierName", "Product", "Category", "BuyingPrice", "Contact", "Type"];
  for (var i = 0; i < fields.length; i++) {
    if (this.gfnEmpty(this.dsSupplier.getColumn(row, fields[i]))) return this.gfnMessage(fields[i] + " is required.");
  }
  if (!this.gfnNumber(this.dsSupplier.getColumn(row, "BuyingPrice")) ||
      !this.gfnNumber(this.dsSupplier.getColumn(row, "OnTheWay"))) {
    return this.gfnMessage("Price and on-the-way quantity must be non-negative numbers.");
  }
  var email = this.dsSupplier.getColumn(row, "Email");
  if (!this.gfnEmpty(email) && !this.gfnEmail(email)) return this.gfnMessage("Enter a valid email address.");
  if (this.dsSupplier.getColumn(row, "Type") !== "Taking return" &&
      this.dsSupplier.getColumn(row, "Type") !== "Not taking return") {
    return this.gfnMessage("Choose a valid supplier type.");
  }
  if (this.uplImage.getItemCount(true) > 0 && !this.imageUploaded) {
    var token = nexacro.getApplication().sessionToken;
    if (!token) return this.gfnHandleApiError(-1, "Your session has expired. Sign in again.");
    this.uplImage.upload("api::uploads/image?sessionToken=" + token);
    return;
  }
  this.submitSupplier();
};
this.onImageUploadSuccess = function(obj, e) {
  var uploaded = e && e.datasets;
  var result = null;
  if (uploaded && uploaded.length) result = uploaded[0];
  else if (uploaded && uploaded.getCount && uploaded.getCount() > 0) result = uploaded.getItem(0);
  if (!result || !result.rowcount) return this.gfnMessage("The image upload returned no image URL.");
  var url = result.getColumn(0, "ImageUrl");
  if (this.gfnEmpty(url)) return this.gfnMessage("The image upload returned no image URL.");
  var row = this.dsSupplier.rowposition < 0 ? 0 : this.dsSupplier.rowposition;
  this.dsSupplier.setColumn(row, "ImageUrl", url);
  this.imageUploaded = true;
  this.submitSupplier();
};
this.onImageUploadError = function(obj, e) {
  this.gfnMessage(e && e.errormsg ? e.errormsg : "The image could not be uploaded.");
};
this.submitSupplier = function() {
  this.gfnTransaction("supplier-save", "suppliers/save", "dsSupplier=dsSupplier",
    "dsSupplierResult=dsSupplierResult", "", "onSupplierSaveResult");
};
this.onSupplierSaveResult = function(serviceId, errorCode, errorMessage) {
  if (errorCode < 0 || !this.dsSupplierResult.rowcount) return this.gfnHandleApiError(errorCode, errorMessage);
  this.close("saved");
};
this.onCancel = function() { this.close(""); };
this.onSupplierDatasetChanged = function(obj, e) {
  if (e.reason === nexacro.Dataset.REASON_CHANGESTATUS) this.supplierInputChanged = true;
};
"""


DETAIL_SCRIPT = r"""
this.currentTab = "Overview";
this.onLoad = function() {
  if (!nexacro.getApplication().sessionToken) return this.gfnNavigate("Login");
  var id = nexacro.getApplication().selectedProductId;
  if (this.gfnEmpty(id)) return this.gfnNavigate("InventoryList");
  this.gfnBindRecord(this.dsRequest, { ProductID: id });
  this.gfnTransaction("product-detail", "products/detail", "dsRequest=dsRequest",
    "dsProduct=dsProduct dsProductDetail=dsProductDetail dsStockLocations=dsStockLocations "
      + "dsPurchases=dsPurchases dsAdjustments=dsAdjustments dsHistory=dsHistory",
    "", "onProductDetailLoaded");
};
this.onProductDetailLoaded = function(serviceId, errorCode, errorMessage) {
  if (errorCode < 0 || !this.dsProductDetail.rowcount) return this.gfnHandleApiError(errorCode, errorMessage);
  this.showTab("Overview");
};
this.onProductDetailChanged = function(obj, e) {
  if (e.reason !== nexacro.Dataset.REASON_ASSIGN && e.reason !== nexacro.Dataset.REASON_APPEND &&
      e.reason !== nexacro.Dataset.REASON_MERGE) return;
  this.showTab(this.currentTab || "Overview");
};
this.showTab = function(name) {
  this.currentTab = name;
  this.staTab.set_text(name);
  var tabs = ["Overview", "Purchases", "Adjustments", "History"];
  for (var i = 0; i < tabs.length; i++) {
    this["btn" + tabs[i]].set_cssclass(tabs[i] === name ? "tabActive" : "tab");
  }
  var source = name === "Purchases" ? this.dsPurchases
    : (name === "Adjustments" ? this.dsAdjustments : this.dsHistory);
  if (name === "Overview") source = this.dsHistory;
  this.dsActivity.copyData(source);
};
this.onTab = function(obj) {
  var name = String(obj.id || "").replace("btn", "");
  this.showTab(name || "Overview");
};
this.onNavInventoryList = function() { this.gfnNavigate("InventoryList"); };
this.onNavSupplierList = function() { this.gfnNavigate("SupplierList"); };
this.onLogout = function() {
  this.gfnLogout();
};
this.onComingSoon = function() { this.gfnMessage("This section is not part of the inventory requirements."); };
this.onBack = function() { this.gfnNavigate("InventoryList"); };
this.onEdit = function() {
  if (!this.dsProductDetail.rowcount) return;
  nexacro.getApplication().editProductId = this.dsProductDetail.getColumn(0, "ProductID");
  this.gfnPopup("ProductForm", 500, 800, "onProductSaved");
};
this.onProductSaved = function(serviceId, value) { if (value) this.onLoad(); };
this.onDownload = function() {
  if (!this.dsProductDetail.rowcount) return;
  this.gfnDownload("products/export.csv", "product.csv",
    { search: this.dsProductDetail.getColumn(0, "ProductID") });
};
this.onActivityChanged = function(obj, e) {
  if (e.reason === nexacro.Dataset.REASON_ASSIGN || e.reason === nexacro.Dataset.REASON_APPEND ||
      e.reason === nexacro.Dataset.REASON_MERGE) this.activityLoaded = true;
};
"""


def configure_controls(path):
    source = path.read_text(encoding="utf-8")
    if path.name == "InventoryList.xfdl":
        source = source.replace('oncelldblclick="onOpenProduct"', 'oncellclick="onOpenProduct"')
    if path.name in ("ProductForm.xfdl", "SupplierForm.xfdl"):
        pattern = r'<FileUpload\b([^>]*\bid="uplImage"[^>]*)/>'
        def add_upload_events(match):
            tag = re.sub(r'\s+onsuccess="[^"]*"|\s+onerror="[^"]*"|\s+onitemchanged="[^"]*"', "", match.group(0))
            return tag[:-2] + ' onitemchanged="onImageChanged" onsuccess="onImageUploadSuccess" onerror="onImageUploadError"/>'
        source = re.sub(pattern, add_upload_events, source, count=1)
    if path.name == "Login.xfdl":
        source = re.sub(r'<CheckBox\b[^>]*\bid="chkRemember"[^>]*/>',
            lambda match: match.group(0)[:-2] + ' truevalue="1" falsevalue="0"/>', source, count=1)
    path.write_text(source, encoding="utf-8")


def make_common(path):
    path.write_text(
        '<Script version="1.0" type="xscript5.1"><![CDATA[' + COMMON_SCRIPT.strip() + '\n]]></Script>',
        encoding="utf-8",
    )


def finalize(root):
    root = Path(root)
    forms = root / "forms"
    datasets = {
        "Login.xfdl": [
            ("dsLogin", ["Email", "Password", "RememberMe"], "onLoginDatasetChanged"),
            ("dsSession", ["UserID", "Name", "Email", "Token", "ExpiresAt", "RememberMe"], None),
            ("dsForgot", ["Email"], None), ("dsResult", ["Message"], None),
        ],
        "SignUp.xfdl": [
            ("dsSignup", ["Name", "Email", "Password", "Confirm"], "onSignupDatasetChanged"),
            ("dsSession", ["UserID", "Name", "Email", "Token", "ExpiresAt", "RememberMe"], None),
        ],
        "InventoryList.xfdl": [
            ("dsSearch", ["Search", "Status", "Page", "PageSize"], None),
            ("dsProducts", PRODUCT_COLUMNS, "onProductsChanged"),
            ("dsLogout", ["SessionToken"], None),
          ("dsSummary", ["Categories", "TotalProducts", "TopSelling", "LowStocks", "OutOfStock", "TopSellingNote"],
           {"onrowsetchanged": "onSummaryChanged", "onload": "onSummaryLoaded"}),
        ],
        "ProductForm.xfdl": [
            ("dsProduct", PRODUCT_COLUMNS, "onProductDatasetChanged"),
            ("dsSaved", PRODUCT_COLUMNS, None),
            ("dsProductDetail", DETAIL_COLUMNS, None),
            ("dsRequest", ["ProductID"], None),
            ("dsCodes", ["CodeType", "Code", "Label"], None),
        ],
        "ProductDetail.xfdl": [
            ("dsRequest", ["ProductID"], None), ("dsProduct", PRODUCT_COLUMNS, None),
            ("dsLogout", ["SessionToken"], None),
            ("dsProductDetail", DETAIL_COLUMNS, "onProductDetailChanged"),
            ("dsStockLocations", ["Location", "Quantity", "Unit", "UpdatedAt"], None),
            ("dsPurchases", EVENT_COLUMNS, None), ("dsAdjustments", EVENT_COLUMNS, None),
            ("dsHistory", EVENT_COLUMNS, None), ("dsActivity", EVENT_COLUMNS, "onActivityChanged"),
        ],
        "SupplierList.xfdl": [
            ("dsSearch", ["Search", "Type", "Page", "PageSize", "SortField", "SortOrder"], None),
            ("dsSuppliers", SUPPLIER_COLUMNS, "onSuppliersChanged"),
            ("dsLogout", ["SessionToken"], None),
            ("dsSupplierSummary", ["TotalSuppliers"], "onSupplierSummaryChanged"),
        ],
        "SupplierForm.xfdl": [
            ("dsSupplier", SUPPLIER_COLUMNS, "onSupplierDatasetChanged"),
            ("dsSupplierResult", SUPPLIER_COLUMNS, None), ("dsCodes", ["CodeType", "Code", "Label"], None),
        ],
    }
    for form_name, entries in datasets.items():
        ensure_datasets(forms / form_name, entries)
        configure_controls(forms / form_name)
    scripts = {
        "Login.xfdl": LOGIN_SCRIPT, "SignUp.xfdl": SIGNUP_SCRIPT,
        "InventoryList.xfdl": INVENTORY_SCRIPT, "ProductForm.xfdl": PRODUCT_FORM_SCRIPT,
        "ProductDetail.xfdl": DETAIL_SCRIPT, "SupplierList.xfdl": SUPPLIER_LIST_SCRIPT,
        "SupplierForm.xfdl": SUPPLIER_FORM_SCRIPT,
    }
    for form_name, script in scripts.items():
        set_script(forms / form_name, script)

    bindings = {
        "Login.xfdl": [
            ("edtEmail", "value", "dsLogin", "Email"),
            ("edtPassword", "value", "dsLogin", "Password"),
            ("chkRemember", "value", "dsLogin", "RememberMe"),
        ],
        "SignUp.xfdl": [
            ("edtName", "value", "dsSignup", "Name"),
            ("edtEmail", "value", "dsSignup", "Email"),
            ("edtPassword", "value", "dsSignup", "Password"),
            ("edtConfirm", "value", "dsSignup", "Confirm"),
        ],
        "ProductForm.xfdl": [
            ("edtProductName", "value", "dsProduct", "ProductName"),
            ("edtProductID", "value", "dsProduct", "ProductID"),
            ("edtCategory", "value", "dsProduct", "Category"),
            ("edtBuyingPrice", "value", "dsProduct", "BuyingPrice"),
            ("edtQuantity", "value", "dsProduct", "Quantity"),
            ("edtUnit", "value", "dsProduct", "Unit"),
            ("edtExpiryDate", "value", "dsProduct", "ExpiryDate"),
            ("edtThreshold", "value", "dsProduct", "Threshold"),
        ],
        "SupplierForm.xfdl": [
            ("edtSupplierName", "value", "dsSupplier", "SupplierName"),
            ("edtProduct", "value", "dsSupplier", "Product"),
            ("edtCategory", "value", "dsSupplier", "Category"),
            ("edtBuyingPrice", "value", "dsSupplier", "BuyingPrice"),
            ("edtContact", "value", "dsSupplier", "Contact"),
            ("edtType", "value", "dsSupplier", "Type"),
        ],
        "ProductDetail.xfdl": [
            ("staName", "text", "dsProductDetail", "ProductName"),
            ("staId", "text", "dsProductDetail", "ProductIDLabel"),
            ("staStatus", "text", "dsProductDetail", "Status"),
            ("staInfo", "text", "dsProductDetail", "OverviewText"),
            ("staSupplier", "text", "dsProductDetail", "SupplierInfo"),
            ("staImage", "image", "dsProductDetail", "ImageUrl"),
        ],
    }
    for form_name, items in bindings.items():
        set_bindings(forms / form_name, items)

    finalize_detail_layout(forms / "ProductDetail.xfdl")
    make_common(root / "lib" / "InventoryCommon.xjs")
    typedefinition = root / "typedefinition.xml"
    config = typedefinition.read_text(encoding="utf-8")
    config = config.replace('url="http://localhost:8080/"', 'url="http://localhost:8080/api/"')
    typedefinition.write_text(config, encoding="utf-8")

    application = root / "Application.xadl"
    adl = application.read_text(encoding="utf-8")
    adl = adl.replace('width="1440" height="800" titletext="KANBAN | Inventory Management"',
                      'width="1440" height="960" titletext="KANBAN | Inventory Management"')
    app_script = '<Script type="xscript5.1"><![CDATA[this.sessionToken = ""; this.currentUserName = ""; '
    app_script += 'this.selectedProductId = ""; this.editProductId = ""; this.inventoryCodeCache = "";]]></Script>'
    adl = re.sub(r'<Script type="xscript5\.1"><!\[CDATA\[.*?\]\]></Script>', app_script, adl, count=1, flags=re.S)
    app_tag = re.search(r'<Application\b[^>]*>', adl)
    if app_tag:
        normalized = re.sub(r'\s+(?:checkversion|version)="[^"]*"', '', app_tag.group(0))
        normalized = normalized[:-1] + ' checkversion="true" version="1.0.0">'
        adl = adl[:app_tag.start()] + normalized + adl[app_tag.end():]
    application.write_text(adl, encoding="utf-8")

    environment = root / "environment.xml"
    env_xml = environment.read_text(encoding="utf-8")
    env_tag = re.search(r'<Environment\b[^>]*>', env_xml)
    if env_tag:
        normalized = re.sub(r'\s+(?:httptimeout|httpretry)="[^"]*"', '', env_tag.group(0))
        normalized = normalized[:-1] + ' httptimeout="30" httpretry="0">'
        env_xml = env_xml[:env_tag.start()] + normalized + env_xml[env_tag.end():]
        environment.write_text(env_xml, encoding="utf-8")

    config = typedefinition.read_text(encoding="utf-8")
    if 'id="ImageViewer"' not in config:
        config = config.replace(
            '<Component type="JavaScript" id="Static" classname="nexacro.Static"/>',
            '<Component type="JavaScript" id="Static" classname="nexacro.Static"/>'
            '<Component type="JavaScript" id="ImageViewer" classname="nexacro.ImageViewer"/>',
        )
    for prefix in ("theme", "xcssrc", "forms", "lib"):
        config = re.sub(
            rf'(<Service\b(?=[^>]*\bprefixid="{prefix}")[^>]*\bversion=")[^"]*(")',
            r'\g<1>1.0.0\2', config,
        )
    config = re.sub(
        r'(<Service\b(?=[^>]*\bprefixid="api")[^>]*\bversion=")[^"]*(")',
        r'\g<1>0\2', config,
    )
    typedefinition.write_text(config, encoding="utf-8")


if __name__ == "__main__":
    finalize(Path(__file__).resolve().parent)
