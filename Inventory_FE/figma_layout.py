"""Apply the Figma-aligned presentation to the generated Nexacro forms.

The data and event scripts remain in build_frontend.py. This module changes only
layout, the small set of fields that are absent from the reference modals, and
the visual theme.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import re


def a(value):
    return escape(str(value), {'"': '&quot;'})


def c(kind, name, x, y, w, h, text=None, css=None, event=None, **extra):
    attrs = dict(id=name, left=x, top=y, width=w, height=h)
    if text is not None:
        attrs['text'] = text
    if css:
        attrs['cssclass'] = css
    if event:
        attrs['onclick'] = event
    attrs.update(extra)
    return '<' + kind + ' ' + ' '.join(f'{key}="{a(value)}"' for key, value in attrs.items()) + '/>'


def shell(active, search=False):
    parts = [c('Static','staSidebarBg',0,0,280,960,'','sidebar'),
             c('Static','staTopbarBg',280,0,1160,100,'','topbar'),
             c('Static','staLogoMark',36,28,32,42,'K','logoMark'),
             c('Static','staBrand',76,31,170,40,'KANBAN','brand'),
             c('Static','staBell',1330,29,35,42,'♧','topIcon'),
             c('Static','staAvatar',1380,30,38,38,'●','avatar')]
    nav = [('Dashboard',135,'⌂  Dashboard',None),('InventoryList',202,'▧  Inventory','InventoryList'),
           ('Reports',269,'▥  Reports',None),('SupplierList',336,'◎  Suppliers','SupplierList'),
           ('Orders',403,'▤  Orders',None),('ManageStore',470,'▣  Manage Store',None)]
    for key,y,label,dest in nav:
        handler = 'onNav'+dest if dest else 'onComingSoon'
        parts.append(c('Button','btn'+key,32,y,218,48,label,'navActive' if active == key else 'nav',handler))
    parts += [c('Button','btnSettings',32,816,218,48,'⚙  Settings','nav','onComingSoon'),
              c('Button','btnLogout',32,882,218,48,'⇥  Log Out','nav','onLogout')]
    if search:
        parts += [c('Edit','edtSearch',318,29,318,42,None,'globalSearch',None,displaynulltext='Search product, supplier, order'),
                  c('Button','btnSearch',642,29,78,42,'Search','topSearchButton','onSearch')]
    else:
        parts += [c('Static','staSearchPlaceholder',318,29,324,42,'⌕  Search product, supplier, order','globalSearchText')]
    return parts


def grid_from(path, grid_id, x, y, w, h):
    source = path.read_text(encoding='utf-8')
    match = re.search(r'<Grid id="'+re.escape(grid_id)+r'".*?</Grid>', source, re.S)
    if not match:
        raise ValueError(f'Missing grid {grid_id} in {path}')
    grid = match.group(0)
    for key,value in [('left',x),('top',y),('width',w),('height',h)]:
        grid = re.sub(r'\b'+key+r'="[^"]*"', f'{key}="{value}"', grid, count=1)
    return grid


def replace_layout(path, widgets, width=1440, height=960):
    source = path.read_text(encoding='utf-8')
    source = re.sub(r'(<Form\b[^>]*\bwidth=")[^"]*', r'\g<1>'+str(width), source, count=1)
    source = re.sub(r'(<Form\b[^>]*\bheight=")[^"]*', r'\g<1>'+str(height), source, count=1)
    layout = f'<Layouts><Layout width="{width}" height="{height}">\n' + '\n'.join(widgets) + '\n</Layout></Layouts>'
    source, count = re.subn(r'<Layouts><Layout[^>]*>.*?</Layout></Layouts>', lambda _: layout, source, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f'Could not replace layout of {path}')
    path.write_text(source, encoding='utf-8')


def auth(root, signup=False):
    form = root / 'forms' / ('SignUp.xfdl' if signup else 'Login.xfdl')
    parts = [c('Static','staAuthCanvas',0,0,1440,960,'','authCanvas'),
             c('Static','staLogoMark',320,355,150,160,'K','authLogoMark'),
             c('Static','staBrandLarge',270,520,280,65,'KANBAN','authBrand'),
             c('Static','staSmallMark',993,254 if signup else 277,48,51,'K','smallLogo')]
    if signup:
        parts += [c('Static','staTitle',825,325,440,55,'Create an account','authTitle'),
                  c('Static','staHint',825,376,440,28,'Start your 30-day free trial.','muted')]
        fields = [('Name','Name*',425,False),('Email','Email*',510,False),('Password','Password*',595,True),('Confirm','Confirm password*',710,True)]
        for key,label,y,pw in fields:
            parts += [c('Static','sta'+key,825,y,360,23,label,'fieldLabel'),
                      c('Edit','edt'+key,825,y+28,360,45,None,'field',None,password='true' if pw else 'false',displaynulltext='Enter '+label.lower().strip('*'))]
        parts += [c('Static','staPasswordHelp',825,671,360,18,'Must be at least 8 characters.','hint'),
                  c('Button','btnCreate',825,810,360,46,'Get started','primary','onCreate'),
                  c('Static','staBackHint',888,869,230,25,'Already have an account?','muted'),
                  c('Button','btnBack',1095,869,85,25,'Log in','link','onBack')]
    else:
        parts += [c('Static','staHello',825,340,440,55,'Log in to your account','authTitle'),
                  c('Static','staHint',825,391,440,28,'Welcome back! Please enter your details.','muted'),
                  c('Static','staEmail',825,442,360,23,'Email','fieldLabel'),
                  c('Edit','edtEmail',825,470,360,45,None,'field',None,displaynulltext='Enter your email'),
                  c('Static','staPassword',825,535,360,23,'Password','fieldLabel'),
                  c('Edit','edtPassword',825,563,360,45,None,'field',None,password='true'),
                  c('CheckBox','chkRemember',825,632,218,28,'Remember for 30 days'),
                  c('Button','btnForgot',1050,632,135,28,'Forgot password','link','onForgot'),
                  c('Button','btnLogin',825,684,360,46,'Sign in','primary','onLogin'),
                  c('Static','staSignUpHint',883,747,225,25,"Don't have an account?",'muted'),
                  c('Button','btnSignUp',1082,747,103,25,'Sign up','link','onSignUp')]
    replace_layout(form, parts)


def inventory(root):
    path = root/'forms'/'InventoryList.xfdl'
    parts = shell('InventoryList',True)
    parts += [c('Static','staOverallCard',312,124,1096,186,'','card'),
              c('Static','staOverallTitle',330,140,400,34,'Overall Inventory','sectionTitle')]
    labels = [('Categories','staCategories',330,'0','Product categories'),
              ('Total Products','staTotal',600,'0','Products in inventory'),
              ('Top Selling','staTopSelling',870,'—','No sales data is recorded'),
              ('Low Stocks','staLow',1140,'0','At or below threshold')]
    for label,key,x,value,note in labels:
        parts += [c('Static','lab'+key,x,195,225,24,label,'metricLabel'),
                  c('Static',key,x,222,135,40,value,'metric'),
                  c('Static','note'+key,x,267,220,22,note,'hint')]
    parts += [c('Static','staOut',1300,240,85,28,'0 out','muted'),
              c('Static','staProductsCard',312,330,1096,581,'','card'),
              c('Static','staProductsTitle',330,349,300,37,'Products','sectionTitle'),
              c('Button','btnAdd',1020,345,130,42,'Add Product','primary','onAdd'),
              c('Button','btnFilter',1160,345,105,42,'☷  Filters','secondary','onFilter'),
              c('Button','btnDownload',1274,345,118,42,'Download all','secondary','onDownload'),
              grid_from(path,'grdProducts',330,401,1062,452),
              c('Button','btnPrev',330,865,92,35,'Previous','secondary','onPrev'),
              c('Static','staPage',805,868,365,28,'','pageLabel'),
              c('Button','btnNext',1300,865,92,35,'Next','secondary','onNext')]
    replace_layout(path, parts)
    source=path.read_text(encoding='utf-8')
    source=source.replace('this.staTotal.set_text(String(rows.length));', 'this.staCategories.set_text(String((function(){var seen={};for(var n=0;n<rows.length;n++)seen[rows[n].Category]=true;return Object.keys(seen).length;})())); this.staTotal.set_text(String(rows.length));')
    source=source.replace('this.gfnPopup("ProductForm", 700, 720, "onProductSaved")', 'this.gfnPopup("ProductForm", 500, 800, "onProductSaved")')
    source=source.replace('this.onNavInventoryList = function() {};', 'this.onNavInventoryList = function() {};\nthis.onComingSoon = function() { this.gfnMessage("This section is outside the current requirements."); };')
    path.write_text(source,encoding='utf-8')


def suppliers(root):
    path=root/'forms'/'SupplierList.xfdl'
    parts=shell('SupplierList',True)
    supplier_grid=grid_from(path,'grdSuppliers',330,197,1062,651).replace('<Cell col="4" text="bind:Type"/>','<Cell col="4" text="bind:Type" color="expr:Type==\'Taking return\'?\'#29A46B\':\'#D56B6B\'"/>')
    parts += [c('Static','staSuppliersCard',312,124,1096,787,'','card'),
              c('Static','staSuppliersTitle',330,143,400,37,'Suppliers','sectionTitle'),
              c('Button','btnAdd',1020,140,130,42,'Add Supplier','primary','onAdd'),
              c('Button','btnFilter',1160,140,105,42,'☷  Filters','secondary','onFilter'),
              c('Button','btnDownload',1274,140,118,42,'Download all','secondary','onDownload'),
              supplier_grid,
              c('Button','btnPrev',330,865,92,35,'Previous','secondary','onPrev'),
              c('Static','staCount',805,868,365,28,'','pageLabel'),
              c('Button','btnNext',1300,865,92,35,'Next','secondary','onNext')]
    replace_layout(path,parts)
    source=path.read_text(encoding='utf-8')
    source=source.replace('this.query=""; this.typeFilter="";', 'this.query=""; this.typeFilter=""; this.page=0; this.pageSize=12;')
    source=re.sub(r'this.refresh = function\(\) \{.*?\n\};\nthis.onSearch', '''this.refresh = function() {
  this.dsSuppliers.clearData();
  var rows=nexacro.getApplication().inventorySuppliers, filtered=[];
  for(var i=0;i<rows.length;i++) {
    var s=rows[i];
    if(this.query && (s.SupplierName+" "+s.Product).toLowerCase().indexOf(this.query)<0)continue;
    if(this.typeFilter && s.Type!=this.typeFilter)continue;
    filtered.push(s);
  }
  this.filteredCount=filtered.length;
  var pages=Math.max(1,Math.ceil(filtered.length/this.pageSize));
  if(this.page>=pages)this.page=pages-1;
  for(var j=this.page*this.pageSize;j<Math.min(filtered.length,(this.page+1)*this.pageSize);j++) {
    var row=this.dsSuppliers.addRow(), item=filtered[j];
    for(var k in item)if(this.dsSuppliers.getColumnInfo(k))this.dsSuppliers.setColumn(row,k,item[k]);
  }
  this.staCount.set_text("Page "+(this.page+1)+" of "+pages);
};
this.onSearch''',source,count=1,flags=re.S)
    source=source.replace('this.query=String(this.edtSearch.value||"").toLowerCase();this.refresh();', 'this.query=String(this.edtSearch.value||"").toLowerCase();this.page=0;this.refresh();')
    source=source.replace('this.btnFilter.set_text(this.typeFilter||"Filter");this.refresh();', 'this.btnFilter.set_text(this.typeFilter||"Filters");this.page=0;this.refresh();')
    source=source.replace('this.onNavSupplierList = function() {};', 'this.onNavSupplierList = function() {};\nthis.onComingSoon = function() { this.gfnMessage("This section is outside the current requirements."); };\nthis.onDownload = function() { this.gfnMessage("Export will be connected when the supplier API is ready."); };\nthis.onPrev = function() { if(this.page>0){this.page--;this.refresh();} };\nthis.onNext = function() { if((this.page+1)*this.pageSize<this.filteredCount){this.page++;this.refresh();} };')
    source=source.replace('this.gfnPopup("SupplierForm",700,680,"onSupplierSaved")','this.gfnPopup("SupplierForm",500,730,"onSupplierSaved")')
    path.write_text(source,encoding='utf-8')


def popup(root, supplier=False):
    name='SupplierForm' if supplier else 'ProductForm'
    path=root/'forms'/(name+'.xfdl')
    height=730 if supplier else 800
    parts=[c('Static','staFormTitle',28,23,440,40,'New Supplier' if supplier else 'New Product','popupTitle'),
           c('Static','staImageBox',140,70,90,84,'','uploadBox'),
           c('Static','staImageGlyph',162,83,48,55,'+' ,'uploadGlyph'),
           c('Static','staImage',240,82,220,50,'Drag image here\nor Browse image','uploadHint'),
           c('FileUpload','uplImage',240,126,218,30,None,'uploadPicker')]
    fields = ([('SupplierName','Supplier Name'),('Product','Product'),('Category','Category'),('BuyingPrice','Buying Price'),('Contact','Contact Number'),('Type','Type')]
              if supplier else [('ProductName','Product Name'),('ProductID','Product ID'),('Category','Category'),('BuyingPrice','Buying Price'),('Quantity','Quantity'),('Unit','Unit'),('ExpiryDate','Expiry Date'),('Threshold','Threshold Value')])
    first=185 if supplier else 172
    step=72 if supplier else 67
    for i,(key,label) in enumerate(fields):
        y=first+i*step
        parts.append(c('Static','sta'+key,28,y,150,40,label,'modalLabel'))
        if key in ('Category','Unit','Type'):
            parts.append(c('Combo','edt'+key,188,y,280,42,None,'modalField',None,innerdataset='ds'+key,codecolumn='Code',datacolumn='Label'))
        else:
            parts.append(c('Edit','edt'+key,188,y,280,42,None,'modalField',None,displaynulltext='Enter '+label.lower()))
    parts += [c('Button','btnCancel',267,height-65,94,40,'Discard','secondary','onCancel'),
              c('Button','btnSave',370,height-65,98,40,'Add Supplier' if supplier else 'Add Product','primary','onSave')]
    replace_layout(path,parts,500,height)
    source=path.read_text(encoding='utf-8')
    if supplier:
        source=source.replace('<Objects>', '<Objects><Dataset id="dsCategory"><ColumnInfo><Column id="Code" type="STRING" size="64"/><Column id="Label" type="STRING" size="64"/></ColumnInfo><Rows><Row><Col id="Code">Electronics</Col><Col id="Label">Electronics</Col></Row><Row><Col id="Code">Office</Col><Col id="Label">Office</Col></Row><Row><Col id="Code">Stationery</Col><Col id="Label">Stationery</Col></Row><Row><Col id="Code">Other</Col><Col id="Label">Other</Col></Row></Rows></Dataset>',1)
        source=source.replace('var supplier={SupplierID:"SUP"+new Date().getTime()}; var fields=["SupplierName","Product","Category","BuyingPrice","Contact","Email","Type","OnTheWay"];', 'var supplier={SupplierID:"SUP"+new Date().getTime(),Email:"",OnTheWay:"0"}; var fields=["SupplierName","Product","Category","BuyingPrice","Contact","Type"];')
        source=source.replace('  if(!this.gfnEmail(supplier.Email))return this.gfnMessage("Enter a valid email address.");\n','')
        source=source.replace('!this.gfnNumber(supplier.BuyingPrice)||!this.gfnNumber(supplier.OnTheWay)', '!this.gfnNumber(supplier.BuyingPrice)')
    else:
        source=source.replace('"ExpiryDate","Threshold","Supplier"]','"ExpiryDate","Threshold"]')
        source=source.replace('  this.close(JSON.stringify(product));', '  product.Supplier=""; this.close(JSON.stringify(product));')
    path.write_text(source,encoding='utf-8')


def detail(root):
    path=root/'forms'/'ProductDetail.xfdl'
    parts=shell('InventoryList',False)
    parts += [c('Static','staDetailCard',312,124,1096,787,'','card'),
              c('Static','staName',330,140,475,42,'','sectionTitle'),
              c('Button','btnEdit',1210,141,80,38,'✎  Edit','secondary','onEdit'),
              c('Button','btnDownload',1299,141,93,38,'Download','secondary','onDownload')]
    for i,(key,label) in enumerate([('Overview','Overview'),('Purchases','Purchases'),('Adjustments','Adjustments'),('History','History')]):
        parts.append(c('Button','btn'+key,330+i*147,190,138,44,label,'tabActive' if i==0 else 'tab','onTab'))
    parts += [c('Static','staDetailsTitle',354,255,430,32,'Primary Details','sectionTitleSmall'),
              c('Static','staId',354,307,520,32,'','detailBody'),
              c('Static','staInfo',354,350,545,190,'','detailBody'),
              c('Static','staSupplierTitle',354,560,430,35,'Supplier Details','sectionTitleSmall'),
              c('Static','staSupplier',354,605,580,85,'','detailBody'),
              c('Static','staStockTitle',354,720,430,35,'Stock Locations','sectionTitleSmall'),
              c('Static','staStock',354,762,610,95,'Location data will be available from the API.','stockTable'),
              c('ImageViewer','staImage',1150,266,170,190,'','imagePlaceholder',image=''),
              c('Static','staStatus',1040,490,260,35,'','status'),
              c('Static','staTab',980,540,360,90,'Product overview','muted'),
              c('Button','btnBack',330,865,160,35,'← Back to inventory','secondary','onBack')]
    replace_layout(path,parts)
    source=path.read_text(encoding='utf-8')
    source=source.replace('this.onBack=function(){this.gfnNavigate("InventoryList");};', 'this.onBack=function(){this.gfnNavigate("InventoryList");};\nthis.onComingSoon=function(){this.gfnMessage("This section is outside the current requirements.");};\nthis.onEdit=function(){this.gfnMessage("Editing will be connected to the product API.");};\nthis.onDownload=function(){this.gfnMessage("Download will be connected to the product API.");};')
    path.write_text(source,encoding='utf-8')


def apply(root):
    root=Path(root)
    auth(root,False); auth(root,True)
    inventory(root); suppliers(root)
    popup(root,False); popup(root,True)
    detail(root)
    app=root/'Application.xadl'
    source=app.read_text(encoding='utf-8').replace('width="1440" height="800" titletext="Invento | Inventory Management"','width="1440" height="960" titletext="KANBAN | Inventory Management"')
    app.write_text(source,encoding='utf-8')
    (root/'_resource_'/'_xcss_'/'inventory.xcss').write_text('''<?xml version="1.0" encoding="utf-8"?>
<XCSS version="1.1"><CSSData><![CDATA[
.Form { background:#F0F1F3; color:#202329; font:14px "Segoe UI"; }
.Static.authCanvas { background:#FFFFFF; }
.Static.sidebar { background:#FFFFFF; -nexa-border:0px none; }
.Static.topbar { background:#FFFFFF; -nexa-border:0px none; }
.Static.logoMark { background:#0BA8D7; color:#FFFFFF; -nexa-text-align:center; font:700 28px "Segoe UI"; border-radius:7px; }
.Static.authLogoMark { background:#0BA8D7; color:#FFFFFF; -nexa-text-align:center; font:700 110px "Segoe UI"; border-radius:20px; }
.Static.smallLogo { background:#0BA8D7; color:#FFFFFF; -nexa-text-align:center; font:700 34px "Segoe UI"; border-radius:7px; }
.Static.brand { color:#1598CC; font:700 25px "Segoe UI"; }
.Static.authBrand { color:#1598CC; -nexa-text-align:center; font:700 52px "Segoe UI"; }
.Button.nav, .Button.nav[status=focused] { background:transparent; color:#727C89; -nexa-border:0px none; -nexa-text-align:left; -nexa-text-padding:0px 14px; font:14px "Segoe UI"; }
.Button.navActive, .Button.navActive[status=focused] { background:#F4F9FF; color:#2475D6; -nexa-border:0px none; -nexa-text-align:left; -nexa-text-padding:0px 14px; font:600 14px "Segoe UI"; }
.Static.globalSearchText { background:#F9FAFC; color:#A1A8B3; -nexa-border:1px solid #E9EBF0; -nexa-padding:0px 14px; font:13px "Segoe UI"; }
.Edit.globalSearch { background:#F9FAFC; color:#A1A8B3; -nexa-border:1px solid #E9EBF0; -nexa-padding:0px 14px; font:13px "Segoe UI"; }
.Button.topSearchButton { background:#F9FAFC; color:#3578C9; -nexa-border:1px solid #E9EBF0; font:12px "Segoe UI"; }
.Static.topIcon { color:#88919E; font:24px "Segoe UI"; }
.Static.avatar { color:#576675; font:25px "Segoe UI"; }
.Static.card { background:#FFFFFF; -nexa-border:1px solid #EBEDF0; border-radius:8px; }
.Static.sectionTitle { color:#313842; font:600 20px "Segoe UI"; }
.Static.sectionTitleSmall { color:#414852; font:600 16px "Segoe UI"; }
.Static.metricLabel { color:#497DD0; font:600 14px "Segoe UI"; }
.Static.metric { color:#353B45; font:600 19px "Segoe UI"; }
.Static.hint, .Static.muted { color:#9CA4AF; font:12px "Segoe UI"; }
.Static.pageLabel { color:#727C89; -nexa-text-align:center; font:13px "Segoe UI"; }
.Button.primary, .Button.primary[status=focused] { background:#1E6FD9; color:#FFFFFF; -nexa-border:1px solid #1E6FD9; border-radius:4px; font:600 13px "Segoe UI"; }
.Button.secondary, .Button.secondary[status=focused] { background:#FFFFFF; color:#78818D; -nexa-border:1px solid #E0E4E9; border-radius:4px; font:13px "Segoe UI"; }
.Button.link { background:transparent; color:#1E6FD9; -nexa-border:0px none; font:600 12px "Segoe UI"; }
.Grid.dataGrid { background:#FFFFFF; -nexa-border:0px none; color:#444C57; font:13px "Segoe UI"; }
.Static.authTitle { color:#20252D; -nexa-text-align:center; font:700 30px "Segoe UI"; }
.Static.fieldLabel { color:#565E69; font:13px "Segoe UI"; }
.Edit.field, .Combo.field { background:#FFFFFF; -nexa-border:1px solid #DDE2E8; border-radius:5px; -nexa-padding:0px 12px; color:#303943; font:14px "Segoe UI"; }
.Static.popupTitle { color:#262D36; font:600 22px "Segoe UI"; }
.Static.modalLabel { color:#454D58; font:13px "Segoe UI"; }
.Edit.modalField, .Combo.modalField { background:#FFFFFF; -nexa-border:1px solid #DDE2E8; border-radius:5px; -nexa-padding:0px 10px; color:#303943; font:13px "Segoe UI"; }
.Static.uploadBox { background:#FFFFFF; -nexa-border:1px dashed #DDE2E8; border-radius:6px; }
.Static.uploadGlyph { color:#A2ADB9; -nexa-text-align:center; font:36px "Segoe UI"; }
.Static.uploadHint { color:#9CA4AF; font:12px "Segoe UI"; }
.FileUpload.uploadPicker { color:#1E6FD9; font:12px "Segoe UI"; }
.Static.detailBody { color:#626C78; font:14px "Segoe UI"; }
.Static.stockTable { background:#F8F9FB; color:#626C78; -nexa-border:1px solid #EEF0F2; font:13px "Segoe UI"; }
.ImageViewer.imagePlaceholder { background:#F7F8FA; -nexa-border:1px dashed #DDE2E8; }
.Static.status { color:#29A46B; font:14px "Segoe UI"; }
.Button.tab { background:#FFFFFF; color:#7D8793; -nexa-border:0px none; font:14px "Segoe UI"; }
.Button.tabActive { background:#FFFFFF; color:#2C6EB6; -nexa-border:0px none; font:600 14px "Segoe UI"; }
]]></CSSData></XCSS>''',encoding='utf-8')


if __name__ == '__main__':
    apply(Path(__file__).resolve().parent)
