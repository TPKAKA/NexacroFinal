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
FRONTEND_VERSION = "1.0.5"
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
  return this.gfnTransaction("common-codes", "codes/list", "dsCodes=dsCodes", "dsCodes=dsCodes", "", callback || "onCodesLoaded");
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
 * @param {Object<string, *>} [args] Values forwarded to the popup form.
 * @returns {void}
 */
this.gfnPopup = function(name, width, height, callback, args) {
  var viewWidth = this.getOffsetWidth();
  var viewHeight = this.getOffsetHeight();
  if (viewWidth > 0) width = Math.min(width, Math.max(240, viewWidth - 24));
  if (viewHeight > 0) height = Math.min(height, Math.max(300, viewHeight - 40));
  var child = new ChildFrame();
  child.init("popup" + name, 0, 0, width, height);
  child.formurl = "forms::" + name + ".xfdl";
  child.openalign = "center middle";
  child.showtitlebar = false;
  child.dragmovetype = "all";
  child.background = "#FFFFFF";
  child.border = "1px solid #DCE5E2";
  child.showModal(this.getOwnerFrame(), args || {}, this, callback);
};
/**
 * Set the position and size of a component in this Form.
 * @param {string} id Component id.
 * @param {number} left Left position in pixels.
 * @param {number} top Top position in pixels.
 * @param {number} width Component width in pixels.
 * @param {number} height Component height in pixels.
 * @returns {void}
 */
this.gfnResponsiveBounds = function(id, left, top, width, height) {
  var component = this[id];
  if (!component) return;
  component.set_left(Math.round(left));
  component.set_top(Math.round(top));
  component.set_width(Math.max(1, Math.round(width)));
  component.set_height(Math.max(1, Math.round(height)));
};
/**
 * Change a component's visibility when applying a responsive layout.
 * @param {string} id Component id.
 * @param {boolean} visible Whether the component should be visible.
 * @returns {void}
 */
this.gfnResponsiveVisible = function(id, visible) {
  var component = this[id];
  if (component) component.set_visible(!!visible);
};
/**
 * Apply the shared navigation and top-bar layout for the current Form size.
 * @param {string} active Active page name.
 * @param {boolean} hasSearch Whether this screen has an active search field.
 * @returns {Object<string, *>} Responsive viewport measurements.
 */
this.gfnResponsiveShell = function(active, hasSearch) {
  var width = Number(this.getOffsetWidth()) || 1440;
  var height = Number(this.getOffsetHeight()) || 960;
  var mobile = width < 760;
  var compact = width < 1100;
  var shortViewport = height < 760;
  var sidebarWidth = mobile ? 0 : (compact ? 220 : 280);
  var topbarHeight = mobile ? 64 : 100;
  var left = mobile ? 12 : sidebarWidth + 32;
  var contentWidth = Math.max(260, width - left - (mobile ? 12 : 32));
  var navIds = ["btnDashboard", "btnInventoryList", "btnReports", "btnSupplierList",
    "btnOrders", "btnManageStore", "btnSettings", "btnLogout"];
  var navTops = [135, 202, 269, 336, 403, 470, height - 146, height - 84];
  var navWidths = mobile ? 0 : sidebarWidth - (compact ? 32 : 64);
  var navLeft = compact ? 16 : 32;
  this.gfnResponsiveBounds("staSidebarBg", 0, 0, Math.max(1, sidebarWidth), height);
  this.gfnResponsiveVisible("staSidebarBg", !mobile);
  this.gfnResponsiveBounds("staTopbarBg", sidebarWidth, 0, Math.max(1, width - sidebarWidth), topbarHeight);
  this.gfnResponsiveVisible("staTopbarBg", true);
  this.gfnResponsiveVisible("staLogoMark", !mobile && !compact);
  this.gfnResponsiveVisible("staBrand", !mobile && !compact);
  this.gfnResponsiveVisible("staBell", !mobile);
  this.gfnResponsiveVisible("staAvatar", !mobile);
  for (var i = 0; i < navIds.length; i++) {
    var hideOnShortViewport = shortViewport && navIds[i] !== "btnInventoryList" &&
      navIds[i] !== "btnSupplierList" && navIds[i] !== "btnLogout";
    this.gfnResponsiveVisible(navIds[i], !mobile && !hideOnShortViewport);
    if (!mobile) this.gfnResponsiveBounds(navIds[i], navLeft, navTops[i], navWidths, 48);
  }
  if (!mobile && shortViewport) {
    this.gfnResponsiveBounds("btnInventoryList", navLeft, 135, navWidths, 48);
    this.gfnResponsiveBounds("btnSupplierList", navLeft, 202, navWidths, 48);
    this.gfnResponsiveBounds("btnLogout", navLeft, height - 84, navWidths, 48);
  }
  if (mobile) {
    var navWidth = Math.min(112, Math.max(78, Math.floor((width - 100) / 2)));
    this.gfnResponsiveVisible("btnInventoryList", true);
    this.gfnResponsiveVisible("btnSupplierList", true);
    this.gfnResponsiveVisible("btnLogout", true);
    this.btnInventoryList.set_text("Inventory");
    this.btnSupplierList.set_text("Suppliers");
    this.btnLogout.set_text("Log out");
    this.btnInventoryList.set_cssclass(active === "InventoryList" || active === "ProductDetail" ? "navCompactActive" : "navCompact");
    this.btnSupplierList.set_cssclass(active === "SupplierList" ? "navCompactActive" : "navCompact");
    this.btnLogout.set_cssclass("navCompact");
    this.gfnResponsiveBounds("btnInventoryList", 8, 10, navWidth, 44);
    this.gfnResponsiveBounds("btnSupplierList", 16 + navWidth, 10, navWidth, 44);
    this.gfnResponsiveBounds("btnLogout", width - 74, 10, 66, 44);
    if (hasSearch) {
      var searchWidth = Math.max(120, width - 104);
      this.gfnResponsiveVisible("edtSearch", true);
      this.gfnResponsiveVisible("btnSearch", true);
      this.edtSearch.set_cssclass("globalSearch");
      this.btnSearch.set_text("Go");
      this.gfnResponsiveBounds("edtSearch", 12, 74, searchWidth, 38);
      this.gfnResponsiveBounds("btnSearch", 20 + searchWidth, 74, Math.max(64, width - searchWidth - 32), 38);
    } else {
      this.gfnResponsiveVisible("staSearchPlaceholder", false);
    }
  } else {
    this.gfnResponsiveBounds("staLogoMark", sidebarWidth + 36, 28, 32, 42);
    this.gfnResponsiveBounds("staBrand", sidebarWidth + 76, 31, 170, 40);
    this.gfnResponsiveBounds("staBell", width - 110, 29, 35, 42);
    this.gfnResponsiveBounds("staAvatar", width - 60, 30, 38, 38);
    this.btnInventoryList.set_text("Inventory");
    this.btnSupplierList.set_text("Suppliers");
    this.btnLogout.set_text("Log out");
    this.btnInventoryList.set_cssclass(active === "InventoryList" || active === "ProductDetail" ? "navActive" : "nav");
    this.btnSupplierList.set_cssclass(active === "SupplierList" ? "navActive" : "nav");
    this.btnLogout.set_cssclass("nav");
    if (hasSearch) {
      var searchLeft = sidebarWidth + (compact ? 24 : 38);
      var searchWidthDesktop = compact
        ? Math.min(250, Math.max(120, width - sidebarWidth - 260))
        : Math.min(318, Math.max(180, width - sidebarWidth - 290));
      this.gfnResponsiveVisible("edtSearch", true);
      this.gfnResponsiveVisible("btnSearch", true);
      this.edtSearch.set_cssclass("globalSearch");
      this.btnSearch.set_text("Search");
      this.gfnResponsiveBounds("edtSearch", searchLeft, 29, searchWidthDesktop, 42);
      this.gfnResponsiveBounds("btnSearch", searchLeft + searchWidthDesktop + 8, 29, 78, 42);
    } else {
      this.gfnResponsiveVisible("staSearchPlaceholder", true);
      this.gfnResponsiveBounds("staSearchPlaceholder", sidebarWidth + (compact ? 24 : 38), 29,
        compact ? Math.min(250, Math.max(120, width - sidebarWidth - 260))
          : Math.min(324, Math.max(180, width - sidebarWidth - 290)), 42);
    }
  }
  return { width: width, height: height, mobile: mobile, compact: compact,
    sidebarWidth: sidebarWidth, contentLeft: left, contentWidth: contentWidth,
    bodyTop: mobile && hasSearch ? 124 : (mobile ? 80 : 124) };
};
/**
 * Set the Grid column visibility preset while preserving each original column width.
 * @param {nexacro.Grid} grid Grid to update.
 * @param {number[]} visibleIndexes Format-column indexes to show.
 * @returns {void}
 */
this.gfnResponsiveGridColumns = function(grid, visibleIndexes) {
  if (!grid) return;
  var count = grid.getFormatColCount();
  if (!grid._responsiveBaseColumnSizes) {
    grid._responsiveBaseColumnSizes = [];
    for (var i = 0; i < count; i++) {
      var size = Number(grid.getFormatColProperty(i, "size"));
      grid._responsiveBaseColumnSizes[i] = size > 0 ? size : 120;
    }
  }
  if (grid._chosenVisibleColumns) visibleIndexes = grid._chosenVisibleColumns;
  var visible = {};
  for (var j = 0; j < visibleIndexes.length; j++) visible[visibleIndexes[j]] = true;
  grid.set_enableredraw(false);
  for (var column = 0; column < count; column++) {
    grid.setFormatColProperty(column, "size", visible[column] ? grid._responsiveBaseColumnSizes[column] : 0);
  }
  grid.set_enableredraw(true);
};
/**
 * Resize the Login and Sign Up forms for desktop and narrow screens.
 * @param {boolean} signup True for Sign Up, false for Login.
 * @returns {void}
 */
this.gfnResponsiveAuth = function(signup) {
  var width = Number(this.getOffsetWidth()) || 1440;
  var height = Number(this.getOffsetHeight()) || 960;
  var mobile = width < 900 || height < 720;
  this.gfnResponsiveBounds("staAuthCanvas", 0, 0, width, height);
  this.gfnResponsiveVisible("staLogoMark", !mobile);
  this.gfnResponsiveVisible("staBrandLarge", !mobile);
  if (mobile) {
    var formWidth = Math.min(440, Math.max(240, width - 32));
    var left = Math.max(16, Math.floor((width - formWidth) / 2));
    var top = Math.max(16, Math.floor((height - (signup ? 650 : 540)) / 2));
    this.gfnResponsiveVisible("staSmallMark", true);
    this.gfnResponsiveBounds("staSmallMark", Math.floor((width - 48) / 2), top, 48, 48);
    if (signup) {
      this.gfnResponsiveBounds("staTitle", left, top + 54, formWidth, 42);
      this.gfnResponsiveBounds("staHint", left, top + 96, formWidth, 26);
      var signupFields = ["Name", "Email", "Password", "Confirm"];
      var signupTops = [top + 128, top + 202, top + 276, top + 350];
      for (var s = 0; s < signupFields.length; s++) {
        this.gfnResponsiveBounds("sta" + signupFields[s], left, signupTops[s], formWidth, 20);
        this.gfnResponsiveBounds("edt" + signupFields[s], left, signupTops[s] + 23, formWidth, 40);
      }
      this.gfnResponsiveBounds("staPasswordHelp", left, top + 418, formWidth, 18);
      this.gfnResponsiveBounds("btnCreate", left, top + 446, formWidth, 44);
      this.gfnResponsiveBounds("staBackHint", left, top + 506, Math.max(150, formWidth - 92), 25);
      this.gfnResponsiveBounds("btnBack", left + formWidth - 82, top + 506, 82, 25);
    } else {
      this.gfnResponsiveBounds("staHello", left, top + 58, formWidth, 44);
      this.gfnResponsiveBounds("staHint", left, top + 104, formWidth, 26);
      this.gfnResponsiveBounds("staEmail", left, top + 148, formWidth, 20);
      this.gfnResponsiveBounds("edtEmail", left, top + 172, formWidth, 40);
      this.gfnResponsiveBounds("staPassword", left, top + 228, formWidth, 20);
      this.gfnResponsiveBounds("edtPassword", left, top + 252, formWidth, 40);
      this.gfnResponsiveBounds("chkRemember", left, top + 308, Math.max(150, formWidth - 120), 28);
      this.gfnResponsiveBounds("btnForgot", left + formWidth - 128, top + 308, 128, 28);
      this.gfnResponsiveBounds("btnLogin", left, top + 354, formWidth, 44);
      this.gfnResponsiveBounds("staSignUpHint", left, top + 414, Math.max(150, formWidth - 92), 25);
      this.gfnResponsiveBounds("btnSignUp", left + formWidth - 82, top + 414, 82, 25);
    }
    return;
  }
  var formLeft = Math.max(520, Math.min(825, Math.round(width * 0.573)));
  var formWidthDesktop = Math.max(280, Math.min(360, width - formLeft - 24));
  var offsetY = Math.min(0, height - 960);
  var logoLeft = Math.round(width * 0.222);
  var logoTop = Math.max(36, Math.round((height - 250) / 2));
  this.gfnResponsiveBounds("staLogoMark", logoLeft, logoTop, 150, 160);
  this.gfnResponsiveBounds("staBrandLarge", logoLeft - 50, logoTop + 165, 280, 65);
  this.gfnResponsiveVisible("staSmallMark", true);
  this.gfnResponsiveBounds("staSmallMark", formLeft + Math.floor(formWidthDesktop / 2) - 12,
    (signup ? 254 : 277) + offsetY, 48, 51);
  if (signup) {
    this.gfnResponsiveBounds("staTitle", formLeft - 40, 325 + offsetY, formWidthDesktop + 80, 55);
    this.gfnResponsiveBounds("staHint", formLeft, 376 + offsetY, formWidthDesktop + 40, 28);
    var desktopSignupFields = ["Name", "Email", "Password", "Confirm"];
    var desktopSignupTops = [425, 510, 595, 710];
    for (var d = 0; d < desktopSignupFields.length; d++) {
      this.gfnResponsiveBounds("sta" + desktopSignupFields[d], formLeft, desktopSignupTops[d] + offsetY, formWidthDesktop, 23);
      this.gfnResponsiveBounds("edt" + desktopSignupFields[d], formLeft, desktopSignupTops[d] + 28 + offsetY, formWidthDesktop, 45);
    }
    this.gfnResponsiveBounds("staPasswordHelp", formLeft, 671 + offsetY, formWidthDesktop, 18);
    this.gfnResponsiveBounds("btnCreate", formLeft, 810 + offsetY, formWidthDesktop, 46);
    this.gfnResponsiveBounds("staBackHint", formLeft + 58, 869 + offsetY, 230, 25);
    this.gfnResponsiveBounds("btnBack", formLeft + formWidthDesktop - 90, 869 + offsetY, 85, 25);
  } else {
    this.gfnResponsiveBounds("staHello", formLeft - 40, 340 + offsetY, formWidthDesktop + 80, 55);
    this.gfnResponsiveBounds("staHint", formLeft, 391 + offsetY, formWidthDesktop + 40, 28);
    this.gfnResponsiveBounds("staEmail", formLeft, 442 + offsetY, formWidthDesktop, 23);
    this.gfnResponsiveBounds("edtEmail", formLeft, 470 + offsetY, formWidthDesktop, 45);
    this.gfnResponsiveBounds("staPassword", formLeft, 535 + offsetY, formWidthDesktop, 23);
    this.gfnResponsiveBounds("edtPassword", formLeft, 563 + offsetY, formWidthDesktop, 45);
    this.gfnResponsiveBounds("chkRemember", formLeft, 632 + offsetY, 218, 28);
    this.gfnResponsiveBounds("btnForgot", formLeft + formWidthDesktop - 135, 632 + offsetY, 135, 28);
    this.gfnResponsiveBounds("btnLogin", formLeft, 684 + offsetY, formWidthDesktop, 46);
    this.gfnResponsiveBounds("staSignUpHint", formLeft + 58, 747 + offsetY, 225, 25);
    this.gfnResponsiveBounds("btnSignUp", formLeft + formWidthDesktop - 103, 747 + offsetY, 103, 25);
  }
};
/**
 * Reflow the Inventory list, summary metrics, actions, and Grid.
 * @param {Object<string, *>} layout Measurements from gfnResponsiveShell.
 * @returns {void}
 */
this.gfnResponsiveInventoryList = function(layout) {
  var left = layout.contentLeft, width = layout.contentWidth, top = layout.bodyTop;
  var mobile = layout.mobile, height = layout.height;
  var compactActions = mobile || width < 560;
  var twoColumns = mobile || width < 700;
  var summaryHeight = twoColumns ? 188 : 186;
  this.gfnResponsiveBounds("staOverallCard", left, top, width, summaryHeight);
  this.gfnResponsiveBounds("staOverallTitle", left + 18, top + 14, Math.max(200, width - 36), 32);
  var metricLabels = ["Categories", "Total", "TopSelling", "Low"];
  var metricValues = ["Categories", "Total", "TopSelling", "Low"];
  var metricNotes = ["Categories", "Total", "TopSelling", "Low"];
  if (twoColumns) {
    var cellWidth = Math.max(110, Math.floor((width - 48) / 2));
    for (var i = 0; i < 4; i++) {
      var row = i < 2 ? 0 : 1;
      var column = i % 2;
      var x = left + 18 + column * (cellWidth + 12);
      var y = top + 50 + row * 68;
      this.gfnResponsiveBounds("labsta" + metricLabels[i], x, y, cellWidth, 18);
      this.gfnResponsiveBounds("sta" + metricValues[i], x, y + 20, cellWidth, 28);
      this.gfnResponsiveVisible("notesta" + metricNotes[i], false);
    }
    this.gfnResponsiveVisible("staOut", false);
  } else {
    var metricWidth = Math.floor((width - 36) / 4);
    for (var m = 0; m < 4; m++) {
      var metricX = left + 18 + m * metricWidth;
      this.gfnResponsiveBounds("labsta" + metricLabels[m], metricX, top + 71, metricWidth - 8, 24);
      this.gfnResponsiveBounds("sta" + metricValues[m], metricX, top + 98, metricWidth - 8, 40);
      this.gfnResponsiveBounds("notesta" + metricNotes[m], metricX, top + 143, metricWidth - 8, 22);
      this.gfnResponsiveVisible("notesta" + metricNotes[m], true);
    }
    this.gfnResponsiveBounds("staOut", left + width - 108, top + 116, 85, 28);
    this.gfnResponsiveVisible("staOut", true);
  }
  var productTop = top + summaryHeight + (twoColumns ? 14 : 20);
  var cardHeight = Math.max(360, height - productTop - 49);
  this.gfnResponsiveBounds("staProductsCard", left, productTop, width, cardHeight);
  this.gfnResponsiveBounds("staProductsTitle", left + 18, productTop + (mobile ? 12 : 16), Math.max(120, width - 36), 32);
  if (compactActions) {
    var actionWidth = Math.max(66, Math.floor((width - 36) / 3));
    var actionGap = 6;
    var actionLeft = left + 12;
    this.btnAdd.set_text("Add");
    this.btnFilter.set_text("Columns");
    this.btnDownload.set_text("Export");
    this.gfnResponsiveBounds("btnAdd", actionLeft, productTop + 48, actionWidth, 38);
    this.gfnResponsiveBounds("btnFilter", actionLeft + actionWidth + actionGap, productTop + 48, actionWidth, 38);
    this.gfnResponsiveBounds("btnDownload", actionLeft + (actionWidth + actionGap) * 2, productTop + 48,
      Math.max(60, width - (actionLeft - left) - (actionWidth + actionGap) * 2 - 12), 38);
  } else {
    this.btnAdd.set_text("Add Product");
    this.btnFilter.set_text("Columns");
    this.btnDownload.set_text("Download all");
    var downloadLeft = left + width - 18 - 118;
    var filterLeft = downloadLeft - 10 - 105;
    var addLeft = filterLeft - 10 - 130;
    this.gfnResponsiveBounds("btnAdd", addLeft, productTop + 15, 130, 42);
    this.gfnResponsiveBounds("btnFilter", filterLeft, productTop + 15, 105, 42);
    this.gfnResponsiveBounds("btnDownload", downloadLeft, productTop + 15, 118, 42);
  }
  var gridTop = productTop + (compactActions ? 96 : 71);
  var footerTop = productTop + cardHeight - 44;
  this.gfnResponsiveBounds("grdProducts", left + 18, gridTop, Math.max(120, width - 36),
    Math.max(120, footerTop - gridTop - 8));
  this.gfnResponsiveBounds("btnPrev", left + 18, footerTop, 92, 35);
  this.gfnResponsiveBounds("staPage", left + 116, footerTop + 2, Math.max(80, width - 232), 30);
  this.gfnResponsiveBounds("btnNext", left + width - 110, footerTop, 92, 35);
  var compactGrid = mobile || width < 760;
  if (this._responsiveGridMode !== compactGrid) {
    this.gfnResponsiveGridColumns(this.grdProducts, compactGrid ? [0, 2, 5] : [0, 1, 2, 3, 4, 5]);
    this._responsiveGridMode = compactGrid;
  }
};
/**
 * Reflow the Supplier list and its Grid for the current viewport.
 * @param {Object<string, *>} layout Measurements from gfnResponsiveShell.
 * @returns {void}
 */
this.gfnResponsiveSupplierList = function(layout) {
  var left = layout.contentLeft, width = layout.contentWidth, top = layout.bodyTop;
  var mobile = layout.mobile, height = layout.height;
  var compactActions = mobile || width < 560;
  var cardHeight = Math.max(480, height - top - 49);
  this.gfnResponsiveBounds("staSuppliersCard", left, top, width, cardHeight);
  this.gfnResponsiveBounds("staSuppliersTitle", left + 18, top + 16, Math.max(140, width - 36), 34);
  if (compactActions) {
    var actionWidth = Math.max(66, Math.floor((width - 36) / 3));
    var actionLeft = left + 12, gap = 6;
    this.btnAdd.set_text("Add");
    this.btnFilter.set_text("Columns");
    this.btnDownload.set_text("Export");
    this.gfnResponsiveBounds("btnAdd", actionLeft, top + 50, actionWidth, 38);
    this.gfnResponsiveBounds("btnFilter", actionLeft + actionWidth + gap, top + 50, actionWidth, 38);
    this.gfnResponsiveBounds("btnDownload", actionLeft + (actionWidth + gap) * 2, top + 50,
      Math.max(60, width - (actionLeft - left) - (actionWidth + gap) * 2 - 12), 38);
  } else {
    this.btnAdd.set_text("Add Supplier");
    this.btnFilter.set_text("Columns");
    this.btnDownload.set_text("Download all");
    var downloadLeft = left + width - 18 - 118;
    var filterLeft = downloadLeft - 10 - 105;
    var addLeft = filterLeft - 10 - 130;
    this.gfnResponsiveBounds("btnAdd", addLeft, top + 15, 130, 42);
    this.gfnResponsiveBounds("btnFilter", filterLeft, top + 15, 105, 42);
    this.gfnResponsiveBounds("btnDownload", downloadLeft, top + 15, 118, 42);
  }
  var gridTop = top + (compactActions ? 100 : 73);
  var footerTop = top + cardHeight - 44;
  this.gfnResponsiveBounds("grdSuppliers", left + 18, gridTop, Math.max(120, width - 36),
    Math.max(120, footerTop - gridTop - 8));
  this.gfnResponsiveBounds("btnPrev", left + 18, footerTop, 92, 35);
  this.gfnResponsiveBounds("staCount", left + 116, footerTop + 2, Math.max(80, width - 232), 30);
  this.gfnResponsiveBounds("btnNext", left + width - 110, footerTop, 92, 35);
  var compactGrid = mobile || width < 760;
  if (this._responsiveGridMode !== compactGrid) {
    this.gfnResponsiveGridColumns(this.grdSuppliers, compactGrid ? [0, 2, 4] : [0, 1, 2, 3, 4, 5]);
    this._responsiveGridMode = compactGrid;
  }
};
/**
 * Reflow Product Detail content into a single column on narrow screens.
 * @param {Object<string, *>} layout Measurements from gfnResponsiveShell.
 * @returns {void}
 */
this.gfnResponsiveDetail = function(layout) {
  var left = layout.contentLeft, width = layout.contentWidth, top = layout.bodyTop;
  var height = layout.height;
  var singleColumn = layout.mobile || width < 920;
  var cardHeight = singleColumn ? Math.max(900, height - top - 24) : Math.max(640, height - top - 49);
  this.gfnResponsiveBounds("staDetailCard", left, top, width, cardHeight);
  if (singleColumn) {
    var innerLeft = left + 16, innerWidth = Math.max(220, width - 32);
    this.gfnResponsiveBounds("staName", innerLeft, top + 14, innerWidth, 42);
    this.gfnResponsiveBounds("btnEdit", innerLeft, top + 60, 82, 36);
    this.gfnResponsiveBounds("btnDownload", innerLeft + 90, top + 60, 94, 36);
    var tabNames = ["Overview", "Purchases", "Adjustments", "History"];
    var tabShort = ["Overview", "Purchases", "Adjust.", "History"];
    var tabWidth = Math.floor(innerWidth / 4);
    for (var t = 0; t < 4; t++) {
      var tab = this["btn" + tabNames[t]];
      if (tab) tab.set_text(layout.mobile ? tabShort[t] : tabNames[t]);
      this.gfnResponsiveBounds("btn" + tabNames[t], innerLeft + t * tabWidth, top + 106, tabWidth, 38);
    }
    this.gfnResponsiveBounds("staDetailsTitle", innerLeft, top + 154, innerWidth, 28);
    this.gfnResponsiveBounds("staId", innerLeft, top + 186, innerWidth, 28);
    this.gfnResponsiveBounds("staInfo", innerLeft, top + 220, innerWidth, 108);
    this.gfnResponsiveBounds("staSupplierTitle", innerLeft, top + 336, innerWidth, 28);
    this.gfnResponsiveBounds("staSupplier", innerLeft, top + 366, innerWidth, 54);
    this.gfnResponsiveBounds("staStockTitle", innerLeft, top + 424, innerWidth, 28);
    this.gfnResponsiveBounds("grdStockLocations", innerLeft, top + 456, innerWidth, 92);
    this.gfnResponsiveBounds("staImage", innerLeft, top + 562, 80, 80);
    this.gfnResponsiveBounds("staStatus", innerLeft + 92, top + 560, Math.max(100, innerWidth - 92), 30);
    this.gfnResponsiveBounds("staTab", innerLeft + 92, top + 594, Math.max(100, innerWidth - 92), 50);
    this.gfnResponsiveBounds("staActivityTitle", innerLeft, top + 650, innerWidth, 28);
    this.gfnResponsiveBounds("grdActivities", innerLeft, top + 682, innerWidth, 188);
    this.gfnResponsiveBounds("btnBack", innerLeft, top + cardHeight - 48, 150, 36);
    return;
  }
  var bodyLeft = left + 42;
  var activityLeft = left + width - 436;
  this.gfnResponsiveBounds("staName", left + 18, top + 16, width - 234, 42);
  this.gfnResponsiveBounds("btnEdit", left + width - 198, top + 17, 80, 38);
  this.gfnResponsiveBounds("btnDownload", left + width - 109, top + 17, 93, 38);
  var tabNamesWide = ["Overview", "Purchases", "Adjustments", "History"];
  for (var wide = 0; wide < 4; wide++) {
    this["btn" + tabNamesWide[wide]].set_text(tabNamesWide[wide]);
    this.gfnResponsiveBounds("btn" + tabNamesWide[wide], left + 18 + wide * 147, top + 66, 138, 44);
  }
  this.gfnResponsiveBounds("staDetailsTitle", bodyLeft, top + 131, 430, 32);
  this.gfnResponsiveBounds("staId", bodyLeft, top + 183, 520, 32);
  this.gfnResponsiveBounds("staInfo", bodyLeft, top + 226, activityLeft - bodyLeft - 48, 190);
  this.gfnResponsiveBounds("staSupplierTitle", bodyLeft, top + 436, 430, 35);
  this.gfnResponsiveBounds("staSupplier", bodyLeft, top + 481, Math.min(580, activityLeft - bodyLeft - 48), 85);
  this.gfnResponsiveBounds("staStockTitle", bodyLeft, top + 596, 430, 35);
  this.gfnResponsiveBounds("grdStockLocations", bodyLeft, top + 638, Math.min(610, activityLeft - bodyLeft - 48), 95);
  this.gfnResponsiveBounds("staImage", left + width - 258, top + 142, 170, 190);
  this.gfnResponsiveBounds("staStatus", left + width - 368, top + 366, 260, 35);
  this.gfnResponsiveBounds("staTab", left + width - 428, top + 416, 360, 75);
  this.gfnResponsiveBounds("staActivityTitle", activityLeft, top + 436, 420, 35);
  this.gfnResponsiveBounds("grdActivities", activityLeft, top + 461, Math.max(200, left + width - activityLeft - 18),
    Math.max(180, cardHeight - 490));
  this.gfnResponsiveBounds("btnBack", left + 18, top + cardHeight - 48, 160, 35);
};
/**
 * Reflow Product and Supplier entry popup forms for narrow windows.
 * @param {boolean} supplier True when resizing the Supplier form.
 * @returns {void}
 */
this.gfnResponsiveModal = function(supplier) {
  var width = Number(this.getOffsetWidth()) || 500;
  var height = Number(this.getOffsetHeight()) || (supplier ? 730 : 800);
  var mobile = width < 460;
  if (mobile) {
    var contentWidth = Math.max(220, width - 32);
    this.gfnResponsiveBounds("staFormTitle", 16, 14, width - 32, 36);
    this.gfnResponsiveBounds("staImageBox", 16, 58, 54, 48);
    this.gfnResponsiveBounds("staImageGlyph", 16, 58, 54, 48);
    this.gfnResponsiveBounds("staImage", 78, 58, Math.max(120, width - 94), 24);
    this.gfnResponsiveBounds("uplImage", 78, 86, Math.max(120, width - 94), 30);
    var fields = supplier ? ["SupplierName", "Product", "Category", "BuyingPrice", "Contact", "Type"] :
      ["ProductName", "ProductID", "Category", "BuyingPrice", "Quantity", "Unit", "ExpiryDate", "Threshold"];
    var start = 130, step = 62;
    for (var i = 0; i < fields.length; i++) {
      var y = start + i * step;
      this.gfnResponsiveBounds("sta" + fields[i], 16, y, contentWidth, 20);
      this.gfnResponsiveBounds("edt" + fields[i], 16, y + 21, contentWidth, 36);
    }
    var footerTop = Math.max(start + fields.length * step + 10, height - 50);
    var buttonWidth = Math.max(86, Math.floor((width - 48) / 2));
    this.gfnResponsiveBounds("btnCancel", 16, footerTop, buttonWidth, 36);
    this.gfnResponsiveBounds("btnSave", 32 + buttonWidth, footerTop, buttonWidth, 36);
    return;
  }
  this.gfnResponsiveBounds("staFormTitle", 28, 23, width - 56, 40);
  this.gfnResponsiveBounds("staImageBox", Math.round(width * 0.28), 70, 90, 84);
  this.gfnResponsiveBounds("staImageGlyph", Math.round(width * 0.28) + 22, 83, 48, 55);
  this.gfnResponsiveBounds("staImage", Math.round(width * 0.48), 82, width * 0.44, 50);
  this.gfnResponsiveBounds("uplImage", Math.round(width * 0.48), 126, width * 0.44, 30);
  var modalFields = supplier ? ["SupplierName", "Product", "Category", "BuyingPrice", "Contact", "Type"] :
    ["ProductName", "ProductID", "Category", "BuyingPrice", "Quantity", "Unit", "ExpiryDate", "Threshold"];
  var modalStart = supplier ? 185 : 172, modalStep = supplier ? 72 : 67;
  for (var j = 0; j < modalFields.length; j++) {
    var modalY = modalStart + j * modalStep;
    this.gfnResponsiveBounds("sta" + modalFields[j], 28, modalY, 150, 40);
    this.gfnResponsiveBounds("edt" + modalFields[j], 188, modalY, Math.max(180, width - 220), 42);
  }
  var lastFieldTop = modalStart + (modalFields.length - 1) * modalStep;
  var desktopFooter = Math.max(lastFieldTop + 54, height - 65);
  this.gfnResponsiveBounds("btnCancel", width - 233, desktopFooter, 94, 40);
  this.gfnResponsiveBounds("btnSave", width - 130, desktopFooter, 98, 40);
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
  this.onResponsiveSize();
};
this.onResponsiveSize = function() {
  if (typeof this.gfnResponsiveAuth === "function") this.gfnResponsiveAuth(false);
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
  this.onResponsiveSize();
};
this.onResponsiveSize = function() {
  if (typeof this.gfnResponsiveAuth === "function") this.gfnResponsiveAuth(true);
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
  this.onResponsiveSize();
  if (!nexacro.getApplication().sessionToken) return this.gfnNavigate("Login");
  this.refresh();
};
this.onResponsiveSize = function() {
  this.gfnResponsiveInventoryList(this.gfnResponsiveShell("InventoryList", true));
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
  var total = this.dsSummary.rowcount ? Number(this.dsSummary.getColumn(0, "FilteredProducts")) : 0;
  var start = count ? this.page * this.pageSize + 1 : 0;
  var end = this.page * this.pageSize + count;
  this.staPage.set_text(this.getOffsetWidth() < 760 ? start + "–" + end + " / " + total :
    "Showing " + start + "–" + end + " of " + total + " products");
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
  this.gfnPopup("ColumnChooser", 360, 480, "onColumnChooserClosed", { pvGrid: this.grdProducts });
};
this.onColumnChooserClosed = function(serviceId, value) {};
this.onPrev = function() { if (this.page > 0) { this.page--; this.refresh(); } };
this.onNext = function() {
  var total = this.dsSummary.rowcount ? Number(this.dsSummary.getColumn(0, "FilteredProducts")) : 0;
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
  this.onResponsiveSize();
  if (!nexacro.getApplication().sessionToken) return this.gfnNavigate("Login");
  this.refresh();
};
this.onResponsiveSize = function() {
  this.gfnResponsiveSupplierList(this.gfnResponsiveShell("SupplierList", true));
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
  this.staCount.set_text(this.getOffsetWidth() < 760 ? (this.page + 1) + "/" + pages + " · " + total :
    total + " suppliers · Page " + (this.page + 1) + " of " + pages);
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
  this.gfnPopup("ColumnChooser", 360, 480, "onColumnChooserClosed", { pvGrid: this.grdSuppliers });
};
this.onColumnChooserClosed = function(serviceId, value) {};
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
  var ownerFrame = this.getOwnerFrame();
  var popupArgs = ownerFrame && ownerFrame.arguments || {};
  var productId = popupArgs.productId || app.editProductId || "";
  this.isEditing = !this.gfnEmpty(productId);
  this.staFormTitle.set_text(this.isEditing ? "Edit Product" : "New Product");
  this.btnSave.set_text(this.isEditing ? "Save changes" : "Add Product");
  this.gfnBindRecord(this.dsProduct, {
    ProductID: "", ProductName: "", Category: "Electronics", BuyingPrice: "0",
    Quantity: "0", Unit: "pcs", ExpiryDate: "2027-12-31", Threshold: "0",
    Supplier: "", SupplierID: "", ImageUrl: "", Status: ""
  });
  this.gfnBindRecord(this.dsRequest, { ProductID: productId });
  this.gfnLoadCodes("onProductCodesLoaded");
  if (this.isEditing) {
    this.gfnTransaction("product-edit-load", "products/detail", "dsRequest=dsRequest",
      "dsProduct=dsProduct dsProductDetail=dsProductDetail", "", "onEditProductLoaded");
  }
  this.onResponsiveSize();
};
this.onResponsiveSize = function() {
  if (typeof this.gfnResponsiveModal === "function") this.gfnResponsiveModal(false);
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
  this.onResponsiveSize();
  this.gfnBindRecord(this.dsSupplier, {
    SupplierID: "", SupplierName: "", Product: "", Category: "Electronics",
    BuyingPrice: "0", Contact: "", Email: "", Type: "Taking return",
    OnTheWay: "0", ImageUrl: ""
  });
  this.gfnLoadCodes("onSupplierCodesLoaded");
};
this.onResponsiveSize = function() { this.gfnResponsiveModal(true); };
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
  this.onResponsiveSize();
  if (!nexacro.getApplication().sessionToken) return this.gfnNavigate("Login");
  var id = nexacro.getApplication().selectedProductId;
  if (this.gfnEmpty(id)) return this.gfnNavigate("InventoryList");
  this.gfnBindRecord(this.dsRequest, { ProductID: id });
  this.gfnTransaction("product-detail", "products/detail", "dsRequest=dsRequest",
    "dsProduct=dsProduct dsProductDetail=dsProductDetail dsStockLocations=dsStockLocations "
      + "dsPurchases=dsPurchases dsAdjustments=dsAdjustments dsHistory=dsHistory",
    "", "onProductDetailLoaded");
};
this.onResponsiveSize = function() {
  this.gfnResponsiveDetail(this.gfnResponsiveShell("ProductDetail", false));
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
  var compact = this.getOffsetWidth() < 920;
  var labels = compact ? ["Overview", "Purchases", "Adjust.", "History"] : tabs;
  for (var i = 0; i < tabs.length; i++) {
    this["btn" + tabs[i]].set_text(labels[i]);
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
  var productId = this.dsProductDetail.getColumn(0, "ProductID");
  nexacro.getApplication().editProductId = productId;
  this.gfnPopup("ProductForm", 500, 800, "onProductSaved", { productId: productId });
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


COLUMN_CHOOSER_SCRIPT = r"""
this.targetGrid = null;
this.onLoad = function() {
  this.targetGrid = this.getOwnerFrame().pvGrid;
  if (!this.targetGrid) {
    this.alert("The Grid to configure is unavailable.");
    this.close(false);
    return;
  }
  var grid = this.targetGrid;
  var count = grid.getFormatColCount();
  if (!grid._responsiveBaseColumnSizes) {
    grid._responsiveBaseColumnSizes = [];
    for (var i = 0; i < count; i++) {
      var baseSize = Number(grid.getFormatColProperty(i, "size"));
      grid._responsiveBaseColumnSizes[i] = baseSize > 0 ? baseSize : 120;
    }
  }
  this.dsColumns.clearData();
  for (var column = 0; column < count; column++) {
    var title = "Column " + (column + 1);
    for (var cell = 0; cell < grid.getCellCount("head"); cell++) {
      if (Number(grid.getCellProperty("head", cell, "col")) === column) {
        title = String(grid.getCellProperty("head", cell, "text") || title);
        break;
      }
    }
    var row = this.dsColumns.addRow();
    this.dsColumns.setColumn(row, "Title", title);
    this.dsColumns.setColumn(row, "ColumnIndex", String(column));
    var selected = grid._chosenVisibleColumns
      ? grid._chosenVisibleColumns.indexOf(column) >= 0
      : Number(grid.getFormatColProperty(column, "size")) > 0;
    this.dsColumns.setColumn(row, "Visible", selected ? "1" : "0");
    this.dsColumns.setColumn(row, "ToggleLabel", selected ? "☑" : "□");
  }
  this.onResponsiveSize();
};
this.onColumnClick = function(obj, e) {
  if (!e || e.row < 0 || e.row >= this.dsColumns.rowcount) return;
  var selected = String(this.dsColumns.getColumn(e.row, "Visible")) !== "1";
  this.dsColumns.setColumn(e.row, "Visible", selected ? "1" : "0");
  this.dsColumns.setColumn(e.row, "ToggleLabel", selected ? "☑" : "□");
};
this.onResponsiveSize = function() {
  var width = Number(this.getOffsetWidth()) || 360;
  var height = Number(this.getOffsetHeight()) || 480;
  this.staTitle.set_left(16);
  this.staTitle.set_top(14);
  this.staTitle.set_width(Math.max(200, width - 32));
  this.staHint.set_left(16);
  this.staHint.set_top(48);
  this.staHint.set_width(Math.max(200, width - 32));
  this.grdColumns.set_left(12);
  this.grdColumns.set_top(78);
  this.grdColumns.set_width(Math.max(220, width - 24));
  this.grdColumns.set_height(Math.max(120, height - 138));
  this.grdColumns.setFormatColProperty(0, "size", Math.min(72, Math.max(48, Math.round(width * 0.19))));
  this.grdColumns.setFormatColProperty(1, "size", Math.max(120, width - this.grdColumns.getFormatColProperty(0, "size") - 36));
  this.btnCancel.set_left(Math.max(12, width - 190));
  this.btnCancel.set_top(height - 48);
  this.btnApply.set_left(Math.max(12, width - 100));
  this.btnApply.set_top(height - 48);
};
this.onApply = function() {
  var grid = this.targetGrid;
  if (!grid) return this.close(false);
  var selectedColumns = [];
  for (var i = 0; i < this.dsColumns.rowcount; i++) {
    if (String(this.dsColumns.getColumn(i, "Visible")) === "1")
      selectedColumns.push(Number(this.dsColumns.getColumn(i, "ColumnIndex")));
  }
  if (!selectedColumns.length) return this.alert("Keep at least one Grid column visible.");
  grid._chosenVisibleColumns = selectedColumns;
  grid.set_enableredraw(false);
  for (var row = 0; row < this.dsColumns.rowcount; row++) {
    var columnIndex = Number(this.dsColumns.getColumn(row, "ColumnIndex"));
    var isVisible = String(this.dsColumns.getColumn(row, "Visible")) === "1";
    var originalSize = grid._responsiveBaseColumnSizes[columnIndex] || 120;
    grid.setFormatColProperty(columnIndex, "size", isVisible ? originalSize : 0);
  }
  grid.set_enableredraw(true);
  this.close(true);
};
this.onCancel = function() { this.close(false); };
"""


def write_column_chooser(root):
    path = Path(root) / "forms" / "ColumnChooser.xfdl"
    source = '''<?xml version="1.0" encoding="utf-8"?>
<FDL version="2.1"><Form id="ColumnChooser" width="360" height="480" titletext="Choose Grid columns" onload="onLoad" onsize="onResponsiveSize">
<Layouts><Layout width="360" height="480">
<Static id="staTitle" left="16" top="14" width="328" height="30" text="Choose visible columns" cssclass="popupTitle"/>
<Static id="staHint" left="16" top="48" width="328" height="22" text="Check the columns to display." cssclass="muted"/>
<Grid id="grdColumns" left="12" top="78" width="336" height="342" binddataset="dsColumns" cssclass="dataGrid" autofittype="col" selecttype="row" oncellclick="onColumnClick"><Formats><Format id="default"><Columns><Column size="56"/><Column size="280"/></Columns><Rows><Row size="34" band="head"/><Row size="38"/></Rows><Band id="head"><Cell col="0" text="Show"/><Cell col="1" text="Column"/></Band><Band id="body"><Cell col="0" text="bind:ToggleLabel" textAlign="center"/><Cell col="1" text="bind:Title"/></Band></Format></Formats></Grid>
<Button id="btnCancel" left="170" top="432" width="82" height="34" text="Cancel" cssclass="secondary" onclick="onCancel"/>
<Button id="btnApply" left="260" top="432" width="88" height="34" text="Apply" cssclass="primary" onclick="onApply"/>
</Layout></Layouts>
<Objects><Dataset id="dsColumns"><ColumnInfo><Column id="Title" type="STRING" size="256"/><Column id="ColumnIndex" type="STRING" size="16"/><Column id="Visible" type="STRING" size="1"/><Column id="ToggleLabel" type="STRING" size="4"/></ColumnInfo></Dataset></Objects>
<Script type="xscript5.1"><![CDATA[''' + COLUMN_CHOOSER_SCRIPT.strip() + '''
]]></Script></Form></FDL>'''
    path.write_text(source, encoding="utf-8")


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
    write_column_chooser(root)
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
          ("dsSummary", ["Categories", "TotalProducts", "FilteredProducts", "TopSelling", "LowStocks", "OutOfStock", "TopSellingNote"],
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
        normalized = normalized[:-1] + f' checkversion="true" version="{FRONTEND_VERSION}">'
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
            rf'\g<1>{FRONTEND_VERSION}\2', config,
        )
    for prefix in ("forms", "lib"):
        config = re.sub(
            rf'(<Service\b(?=[^>]*\bprefixid="{prefix}")[^>]*\bcachelevel=")[^"]*(")',
            r'\g<1>none\2', config,
        )
    config = re.sub(
        r'(<Service\b(?=[^>]*\bprefixid="api")[^>]*\bversion=")[^"]*(")',
        r'\g<1>0\2', config,
    )
    typedefinition.write_text(config, encoding="utf-8")


if __name__ == "__main__":
    finalize(Path(__file__).resolve().parent)
