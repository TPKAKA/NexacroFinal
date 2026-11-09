"""Generate the Nexacro inventory frontend source forms.

Run from the repository root: python Inventory_FE/build_frontend.py
"""
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
(ROOT / "forms").mkdir(exist_ok=True)
(ROOT / "lib").mkdir(exist_ok=True)
(ROOT / "_resource_" / "_xcss_").mkdir(parents=True, exist_ok=True)


def attr(value):
    return escape(str(value), {'"': '&quot;'})


def control(kind, name, x, y, w, h, text=None, css=None, event=None, **props):
    values = dict(id=name, left=x, top=y, width=w, height=h)
    if text is not None:
        values["text"] = text
    if css:
        values["cssclass"] = css
    if event:
        values["onclick"] = event
    values.update(props)
    return f'<{kind} ' + ' '.join(f'{k}="{attr(v)}"' for k, v in values.items()) + '/>'


def title(text, subtitle):
    return [control('Static', 'staTitle', 280, 35, 750, 47, text, 'title'),
            control('Static', 'staSubtitle', 280, 82, 800, 28, subtitle, 'muted')]


def sidebar(active):
    items = [control('Static', 'staBrand', 28, 35, 192, 48, '◧  Invento', 'brand'),
             control('Static', 'staMenu', 28, 124, 190, 24, 'WORKSPACE', 'sideCaption')]
    for y, label, dest in [(168, '▦  Inventory', 'InventoryList'),
                           (220, '▤  Suppliers', 'SupplierList')]:
        items.append(control('Button', 'btn' + dest, 22, y, 210, 44, label,
                             'navActive' if dest == active else 'nav',
                             'onNav' + dest))
    items += [control('Static', 'staHelp', 28, 658, 190, 38, 'Inventory Management\nNexacro frontend', 'sideFoot'),
              control('Button', 'btnLogout', 22, 704, 210, 42, 'Sign out', 'nav', 'onLogout')]
    return items


def frame(name, widgets, script, datasets='', binds='', width=1440, height=800, shell=True):
    items = []
    if shell:
        items.append(control('Static', 'staSidebarBg', 0, 0, 252, height, '', 'sidebar'))
        items += sidebar(name)
    items += widgets
    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<FDL version="2.1"><Form id="{name}" width="{width}" height="{height}" titletext="{name}" onload="onLoad">
<Layouts><Layout width="{width}" height="{height}">\n{chr(10).join(items)}\n</Layout></Layouts>
<Objects>{datasets}</Objects>
<Script type="xscript5.1"><![CDATA[include "lib::InventoryCommon.xjs";
{script}
]]></Script>{binds}</Form></FDL>'''
    (ROOT / 'forms' / (name + '.xfdl')).write_text(xml, encoding='utf-8')


def dataset(name, columns):
    return '<Dataset id="' + name + '"><ColumnInfo>' + ''.join(
        f'<Column id="{c}" type="STRING" size="256"/>' for c in columns) + '</ColumnInfo></Dataset>'


def grid(name, dataset_name, headings, cols, x=280, y=320, width=1120, height=400, event=None, head_event=None):
    sizes = [int(width * w / sum(cols)) for w in cols]
    sizes[-1] += width - sum(sizes)
    cells_h = ''.join(f'<Cell col="{i}" text="{attr(label)}"/>' for i, label in enumerate(headings))
    cells_b = ''.join(f'<Cell col="{i}" text="bind:{attr(key)}"' + (' color="expr:Status==\'Out of stock\'?\'#C44C4C\':Status==\'Low stock\'?\'#D49B27\':\'#2D765E\'"' if key == 'Status' else '') + '/>' for i, key in enumerate(headings.keys())) if isinstance(headings, dict) else ''
    if isinstance(headings, dict):
        cells_h = ''.join(f'<Cell col="{i}" text="{attr(label)}"/>' for i, label in enumerate(headings.values()))
    extra = f' oncelldblclick="{event}"' if event else ''
    extra += f' onheadclick="{head_event}"' if head_event else ''
    return f'''<Grid id="{name}" binddataset="{dataset_name}" left="{x}" top="{y}" width="{width}" height="{height}" cssclass="dataGrid" autofittype="col" selecttype="row"{extra}><Formats><Format id="default"><Columns>{''.join(f'<Column size="{s}"/>' for s in sizes)}</Columns><Rows><Row size="44" band="head"/><Row size="48"/></Rows><Band id="head">{cells_h}</Band><Band id="body">{cells_b}</Band></Format></Formats></Grid>'''


def auth_field(label, field, y, password=False):
    return [control('Static', 'sta' + field, 580, y, 310, 23, label, 'fieldLabel'),
            control('Edit', 'edt' + field, 580, y + 28, 320, 44, None, 'field', None,
                    password='true' if password else 'false')]


login = [control('Static', 'staAuthBg', 0, 0, 520, 800, '', 'authPanel'),
         control('Static', 'staLogo', 75, 84, 340, 58, '◧  Invento', 'authBrand'),
         control('Static', 'staPitch', 75, 258, 370, 110, 'Inventory made\nsimple.', 'authPitch'),
         control('Static', 'staPitchSub', 75, 394, 350, 64, 'Manage products and suppliers\nin one workspace.', 'authSub'),
         control('Static', 'staHello', 580, 178, 510, 55, 'Welcome back', 'authTitle'),
         control('Static', 'staHint', 580, 235, 450, 30, 'Please enter your details to sign in.', 'muted')]
login += auth_field('Email address', 'Email', 300)
login += auth_field('Password', 'Password', 396, True)
login += [control('CheckBox', 'chkRemember', 580, 492, 150, 30, 'Remember me'),
          control('Button', 'btnForgot', 770, 492, 130, 30, 'Forgot password?', 'link', 'onForgot'),
          control('Button', 'btnLogin', 580, 544, 320, 48, 'Sign in', 'primary', 'onLogin'),
          control('Static', 'staSignUpHint', 602, 618, 210, 28, "Don't have an account?", 'muted'),
          control('Button', 'btnSignUp', 802, 618, 98, 28, 'Sign up', 'link', 'onSignUp'),
          control('Static', 'staDemo', 580, 680, 460, 36, 'Preview mode: enter any valid email and password.', 'hint')]
frame('Login', login, '''
this.onLoad = function() {};
this.onLogin = function() {
  var email = this.edtEmail.value, password = this.edtPassword.value;
  if (!this.gfnEmail(email)) return this.gfnMessage("Enter a valid email address.");
  if (this.gfnEmpty(password)) return this.gfnMessage("Password is required.");
  nexacro.getApplication().inventoryEmail = email;
  this.gfnNavigate("InventoryList");
};
this.onSignUp = function() { this.gfnNavigate("SignUp"); };
this.onForgot = function() { this.gfnMessage("Password recovery will be available with the authentication API."); };
''', shell=False)

signup = [control('Static', 'staAuthBg', 0, 0, 520, 800, '', 'authPanel'),
          control('Static', 'staLogo', 75, 84, 340, 58, '◧  Invento', 'authBrand'),
          control('Static', 'staPitch', 75, 258, 370, 110, 'Start organizing\nyour stock.', 'authPitch'),
          control('Static', 'staTitle', 580, 70, 500, 56, 'Create an account', 'authTitle'),
          control('Static', 'staHint', 580, 130, 450, 28, 'Get started with inventory management.', 'muted')]
for label, field, y, pw in [('Full name','Name',185,False),('Email address','Email',275,False),('Password','Password',365,True),('Confirm password','Confirm',455,True)]:
    signup += auth_field(label, field, y, pw)
signup += [control('Button','btnCreate',580,565,320,48,'Create account','primary','onCreate'),
           control('Static','staBackHint',608,634,180,28,'Already have an account?','muted'),
           control('Button','btnBack',795,634,105,28,'Sign in','link','onBack')]
frame('SignUp', signup, '''
this.onLoad = function() {};
this.onCreate = function() {
  var name = this.edtName.value, email = this.edtEmail.value;
  var password = this.edtPassword.value, confirm = this.edtConfirm.value;
  if (this.gfnEmpty(name)) return this.gfnMessage("Name is required.");
  if (!this.gfnEmail(email)) return this.gfnMessage("Enter a valid email address.");
  if (this.gfnEmpty(password) || password.length < 8) return this.gfnMessage("Password must have at least 8 characters.");
  if (password != confirm) return this.gfnMessage("Passwords do not match.");
  this.gfnMessage("Account creation requires the authentication API. The frontend validation is ready.");
};
this.onBack = function() { this.gfnNavigate("Login"); };
''', shell=False)

products = ['ProductID','ProductName','Category','BuyingPrice','Quantity','Unit','Threshold','ExpiryDate','Supplier','Status']
inventory = title('Inventory', 'Track, search and manage every product in your stock.')
inventory += [control('Static','card1',280,130,350,120,'','card'),
              control('Static','card2',650,130,350,120,'','card'),
              control('Static','card3',1020,130,380,120,'','card'),
              control('Static','staTotalLabel',302,147,280,28,'Total products','cardLabel'),
              control('Static','staTotal',302,180,250,50,'0','metric'),
              control('Static','staLowLabel',672,147,280,28,'Low stock','cardLabel'),
              control('Static','staLow',672,180,250,50,'0','metric'),
              control('Static','staOutLabel',1042,147,280,28,'Out of stock','cardLabel'),
              control('Static','staOut',1042,180,250,50,'0','metric'),
              control('Edit','edtSearch',280,274,425,42,None,'field',None,displaynulltext='Search products...'),
              control('Button','btnSearch',715,274,96,42,'Search','secondary','onSearch'),
              control('Button','btnFilter',822,274,110,42,'Filter','secondary','onFilter'),
              control('Button','btnDownload',1038,274,145,42,'Download','secondary','onDownload'),
              control('Button','btnAdd',1195,274,205,42,'+ Add product','primary','onAdd')]
inventory.append(grid('grdProducts','dsProducts',{'ProductName':'Product name','BuyingPrice':'Buying price','Quantity':'Quantity','Threshold':'Threshold','ExpiryDate':'Expiry date','Status':'Status'},[29,16,12,13,16,14],event='onOpenProduct'))
inventory += [control('Static','staPage',280,737,450,30,'','muted'),
              control('Button','btnPrev',1250,733,66,32,'‹','secondary','onPrev'),
              control('Button','btnNext',1330,733,66,32,'›','secondary','onNext')]
frame('InventoryList', inventory, '''
this.page = 0; this.pageSize = 7; this.searchText = ""; this.statusFilter = "";
this.onLoad = function() { this.gfnSeed(); this.refresh(); };
this.onNavInventoryList = function() {};
this.onNavSupplierList = function() { this.gfnNavigate("SupplierList"); };
this.onLogout = function() { this.gfnNavigate("Login"); };
this.refresh = function() {
  var rows = nexacro.getApplication().inventoryProducts, shown = [], low = 0, out = 0;
  this.dsProducts.clearData();
  for (var i=0; i<rows.length; i++) {
    var item = rows[i], q = Number(item.Quantity), t = Number(item.Threshold);
    item.Status = q <= 0 ? "Out of stock" : (q <= t ? "Low stock" : "In stock");
    if (q <= 0) out++; else if (q <= t) low++;
    if (this.searchText && (item.ProductName + " " + item.ProductID).toLowerCase().indexOf(this.searchText) < 0) continue;
    if (this.statusFilter && item.Status != this.statusFilter) continue;
    shown.push(item);
  }
  var pages = Math.max(1, Math.ceil(shown.length / this.pageSize));
  if (this.page >= pages) this.page = pages - 1;
  for (var j=this.page*this.pageSize; j<Math.min(shown.length,(this.page+1)*this.pageSize); j++) {
    var row = this.dsProducts.addRow();
    for (var k in shown[j]) if (this.dsProducts.getColumnInfo(k)) this.dsProducts.setColumn(row,k,shown[j][k]);
  }
  this.staTotal.set_text(String(rows.length)); this.staLow.set_text(String(low)); this.staOut.set_text(String(out));
  this.staPage.set_text("Showing " + (shown.length ? this.page*this.pageSize+1 : 0) + "–" + Math.min(shown.length,(this.page+1)*this.pageSize) + " of " + shown.length + " products");
};
this.onSearch = function() { this.searchText = String(this.edtSearch.value || "").toLowerCase(); this.page=0; this.refresh(); };
this.onFilter = function() { var a=["","In stock","Low stock","Out of stock"]; this.statusFilter=a[(a.indexOf(this.statusFilter)+1)%a.length]; this.btnFilter.set_text(this.statusFilter || "Filter"); this.page=0; this.refresh(); };
this.onPrev = function() { if(this.page>0) {this.page--;this.refresh();} };
this.onNext = function() { if((this.page+1)*this.pageSize<this.filteredCount()) {this.page++;this.refresh();} };
this.filteredCount = function() { var count=0, rows=nexacro.getApplication().inventoryProducts; for(var i=0;i<rows.length;i++) if((!this.searchText || (rows[i].ProductName+" "+rows[i].ProductID).toLowerCase().indexOf(this.searchText)>=0) && (!this.statusFilter || rows[i].Status==this.statusFilter)) count++; return count; };
this.onOpenProduct = function() { var r=this.dsProducts.rowposition; if(r<0)return; nexacro.getApplication().selectedProductId=this.dsProducts.getColumn(r,"ProductID"); this.gfnNavigate("ProductDetail"); };
this.onAdd = function() { this.gfnPopup("ProductForm", 700, 720, "onProductSaved"); };
this.onProductSaved = function(id, value) { if(!value)return; try { nexacro.getApplication().inventoryProducts.push(JSON.parse(value)); this.refresh(); } catch(e) { this.gfnMessage("Could not read product data."); } };
this.onDownload = function() { this.gfnMessage("Export will be connected when the product API is ready."); };
''', dataset('dsProducts',products))

suppliers_cols = ['SupplierID','SupplierName','Product','Category','BuyingPrice','Contact','Email','Type','OnTheWay']
suppliers = title('Suppliers', 'Manage supplier information and product relationships.')
suppliers += [control('Edit','edtSearch',280,155,500,42,None,'field',None,displaynulltext='Search suppliers...'),
              control('Button','btnSearch',792,155,96,42,'Search','secondary','onSearch'),
              control('Button','btnFilter',900,155,115,42,'Filter','secondary','onFilter'),
              control('Button','btnAdd',1195,155,205,42,'+ Add supplier','primary','onAdd')]
suppliers.append(grid('grdSuppliers','dsSuppliers',{'SupplierName':'Supplier name','Product':'Product','Contact':'Contact number','Email':'Email','Type':'Type','OnTheWay':'On the way'},[19,18,17,21,16,9],y=224,height=495,head_event='onSort'))
suppliers.append(control('Static','staCount',280,740,600,30,'','muted'))
frame('SupplierList', suppliers, '''
this.query=""; this.typeFilter="";
this.onLoad = function() { this.gfnSeed(); this.refresh(); };
this.onNavInventoryList = function() { this.gfnNavigate("InventoryList"); };
this.onNavSupplierList = function() {};
this.onLogout = function() { this.gfnNavigate("Login"); };
this.refresh = function() {
  this.dsSuppliers.clearData(); var rows=nexacro.getApplication().inventorySuppliers;
  for(var i=0;i<rows.length;i++) {
    var s=rows[i]; if(this.query && (s.SupplierName+" "+s.Product).toLowerCase().indexOf(this.query)<0)continue;
    if(this.typeFilter && s.Type!=this.typeFilter)continue;
    var row=this.dsSuppliers.addRow(); for(var k in s) if(this.dsSuppliers.getColumnInfo(k))this.dsSuppliers.setColumn(row,k,s[k]);
  }
  this.staCount.set_text(this.dsSuppliers.rowcount + " suppliers");
};
this.onSearch = function() { this.query=String(this.edtSearch.value||"").toLowerCase();this.refresh(); };
this.onFilter = function() { var a=["","Taking return","Not taking return"];this.typeFilter=a[(a.indexOf(this.typeFilter)+1)%a.length];this.btnFilter.set_text(this.typeFilter||"Filter");this.refresh(); };
this.onSort = function(obj,e) {
  var fields=["SupplierName","Product","Contact","Email","Type","OnTheWay"];
  var key=fields[e.cell]; if(!key)return;
  this.sortDesc=(this.sortField==key&&!this.sortDesc);
  this.sortField=key;
  this.dsSuppliers.set_keystring("S:"+(this.sortDesc?"-":"+")+key);
};
this.onAdd = function() { this.gfnPopup("SupplierForm",700,680,"onSupplierSaved"); };
this.onSupplierSaved = function(id,value) { if(!value)return;try{nexacro.getApplication().inventorySuppliers.push(JSON.parse(value));this.refresh();}catch(e){this.gfnMessage("Could not read supplier data.");} };
''', dataset('dsSuppliers',suppliers_cols))


def option_dataset(name, values):
    return '<Dataset id="' + name + '"><ColumnInfo><Column id="Code" type="STRING" size="64"/><Column id="Label" type="STRING" size="64"/></ColumnInfo><Rows>' + ''.join('<Row><Col id="Code">'+escape(value)+'</Col><Col id="Label">'+escape(value)+'</Col></Row>' for value in values) + '</Rows></Dataset>'


def form_fields(fields, button_text, combos=None):
    combos = combos or {}
    controls = [control('Static','staFormTitle',30,25,600,48,button_text,'popupTitle'),
                control('Static','staFormSub',30,75,620,28,'Complete the fields below to save the record.','muted')]
    for i,(label,key) in enumerate(fields):
        x = 30 if i%2==0 else 355
        y = 124 + (i//2)*91
        controls.append(control('Static','sta'+key,x,y,295,24,label,'fieldLabel'))
        if key in combos:
            controls.append(control('Combo','edt'+key,x,y+27,295,42,None,'field',None,
                                    innerdataset='ds'+key,codecolumn='Code',datacolumn='Label'))
        else:
            controls.append(control('Edit','edt'+key,x,y+27,295,42,None,'field'))
    controls += [control('Button','btnCancel',394,620,120,42,'Cancel','secondary','onCancel'),
                 control('Button','btnSave',528,620,142,42,'Save','primary','onSave')]
    return controls

product_fields=[('Product name','ProductName'),('Product ID','ProductID'),('Category','Category'),('Buying price','BuyingPrice'),('Quantity','Quantity'),('Unit','Unit'),('Expiry date','ExpiryDate'),('Threshold value','Threshold'),('Supplier','Supplier')]
product_form=form_fields(product_fields,'Add new product', {'Category':True,'Unit':True})
product_form += [control('FileUpload','uplImage',30,584,315,35,None,'field'),
                 control('Static','staImage',355,587,295,28,'Product image (optional)','hint')]
frame('ProductForm',product_form,'''this.onLoad=function(){};
this.onCancel=function(){this.close();};
this.onSave=function(){
  var product={}; var fields=["ProductName","ProductID","Category","BuyingPrice","Quantity","Unit","ExpiryDate","Threshold","Supplier"];
  for(var i=0;i<fields.length;i++) product[fields[i]]=this["edt"+fields[i]].value;
  for(var j=0;j<fields.length;j++) if(this.gfnEmpty(product[fields[j]]))return this.gfnMessage(fields[j]+" is required.");
  if(!this.gfnNumber(product.BuyingPrice)||!this.gfnNumber(product.Quantity)||!this.gfnNumber(product.Threshold))return this.gfnMessage("Price, quantity and threshold must be non-negative numbers.");
  if(!/^\\d{4}-\\d{2}-\\d{2}$/.test(product.ExpiryDate))return this.gfnMessage("Expiry date must be YYYY-MM-DD.");
  var rows=nexacro.getApplication().inventoryProducts;
  for(var k=0;k<rows.length;k++)if(rows[k].ProductID==product.ProductID)return this.gfnMessage("Product ID already exists.");
  this.close(JSON.stringify(product));
};''',datasets=option_dataset('dsCategory',['Electronics','Office','Stationery','Lifestyle','Other'])+option_dataset('dsUnit',['pcs','box','kg','litre']),width=700,height=700,shell=False)

supplier_fields=[('Supplier name','SupplierName'),('Product','Product'),('Category','Category'),('Buying price','BuyingPrice'),('Contact number','Contact'),('Email','Email'),('Type (Taking return / Not taking return)','Type'),('On the way','OnTheWay')]
supplier_form=form_fields(supplier_fields,'Add new supplier', {'Type':True})
supplier_form += [control('FileUpload','uplImage',30,584,315,35,None,'field'),
                  control('Static','staImage',355,587,295,28,'Supplier image (optional)','hint')]
frame('SupplierForm',supplier_form,'''this.onLoad=function(){};
this.onCancel=function(){this.close();};
this.onSave=function(){
  var supplier={SupplierID:"SUP"+new Date().getTime()}; var fields=["SupplierName","Product","Category","BuyingPrice","Contact","Email","Type","OnTheWay"];
  for(var i=0;i<fields.length;i++)supplier[fields[i]]=this["edt"+fields[i]].value;
  for(var j=0;j<fields.length;j++)if(this.gfnEmpty(supplier[fields[j]]))return this.gfnMessage(fields[j]+" is required.");
  if(!this.gfnEmail(supplier.Email))return this.gfnMessage("Enter a valid email address.");
  if(!this.gfnNumber(supplier.BuyingPrice)||!this.gfnNumber(supplier.OnTheWay))return this.gfnMessage("Price and on-the-way quantity must be non-negative numbers.");
  if(supplier.Type!="Taking return" && supplier.Type!="Not taking return")return this.gfnMessage("Type must be Taking return or Not taking return.");
  this.close(JSON.stringify(supplier));
};''',datasets=option_dataset('dsType',['Taking return','Not taking return']),width=700,height=700,shell=False)

detail = title('Product information', 'Overview, supplier and stock details for the selected product.')
detail += [control('Button','btnBack',280,130,160,38,'← Back to inventory','secondary','onBack'),
           control('Static','staImage',280,192,280,270,'PRODUCT IMAGE','imagePlaceholder'),
           control('Static','staName',590,190,730,55,'','detailTitle'),
           control('Static','staId',590,245,650,30,'','muted'),
           control('Static','staStatus',590,293,230,36,'','status'),
           control('Static','staInfo',590,355,690,170,'','detailBody'),
           control('Static','staSupplierTitle',280,505,450,40,'Supplier information','sectionTitle'),
           control('Static','staSupplier',280,553,490,100,'','cardBody'),
           control('Static','staStockTitle',815,505,470,40,'Stock locations','sectionTitle'),
           control('Static','staStock',815,553,490,100,'Location data will be available from the API.','cardBody')]
for i,(key,label) in enumerate([('Overview','Overview'),('Purchases','Purchases'),('Adjustments','Adjustments'),('History','History')]):
    detail.append(control('Button','btn'+key,280+i*178,690,166,40,label,'tabActive' if i==0 else 'tab','onTab'))
detail.append(control('Static','staTab',280,741,980,28,'Product overview','muted'))
frame('ProductDetail',detail,'''this.onLoad=function(){
  this.gfnSeed();var id=nexacro.getApplication().selectedProductId,rows=nexacro.getApplication().inventoryProducts,p=null;
  for(var i=0;i<rows.length;i++)if(rows[i].ProductID==id){p=rows[i];break;}
  if(!p){this.gfnNavigate("InventoryList");return;}
  this.staName.set_text(p.ProductName);this.staId.set_text("Product ID: "+p.ProductID+"  •  "+p.Category);
  this.staStatus.set_text(p.Status || "In stock");
  this.staInfo.set_text("Buying price: "+p.BuyingPrice+"\\nQuantity: "+p.Quantity+" "+p.Unit+"\\nThreshold: "+p.Threshold+"\\nExpiry date: "+p.ExpiryDate);
  this.staSupplier.set_text(p.Supplier || "No supplier assigned");
};
this.onNavInventoryList=function(){this.gfnNavigate("InventoryList");};
this.onNavSupplierList=function(){this.gfnNavigate("SupplierList");};
this.onLogout=function(){this.gfnNavigate("Login");};
this.onBack=function(){this.gfnNavigate("InventoryList");};
this.onTab=function(obj){this.staTab.set_text(obj.text+" data will be available from the API.");};
''')

project_xml = '''<?xml version="1.0" encoding="utf-8"?>
<Project version="2.1" nexacrosdk="Latest Version"><EnvironmentDefinition url="environment.xml"/><TypeDefinition url="typedefinition.xml"/><AppVariables url="appvariables.xml"/><AppInfos><AppInfo url="Application.xadl"/></AppInfos></Project>'''
project_file = ROOT / 'Inventory_FE.xprj'
if not project_file.exists() or project_file.read_text(encoding='utf-8') != project_xml:
    project_file.write_text(project_xml, encoding='utf-8')
(ROOT/'Application.xadl').write_text('''<?xml version="1.0" encoding="utf-8"?>
<ADL version="2.0"><Application id="Application" screenid="Desktop_screen" checkversion="true" version="1.0.0"><Layout><MainFrame id="mainframe" width="1440" height="800" titletext="Invento | Inventory Management" showtitlebar="true"><ChildFrame id="childframe" formurl="forms::Login.xfdl" showtitlebar="false"/></MainFrame></Layout><Style url="xcssrc::inventory.xcss"/><Script type="xscript5.1"><![CDATA[]]></Script></Application></ADL>''',encoding='utf-8')
(ROOT/'typedefinition.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>
<TypeDefinition version="3.0"><Modules><Module url="CompBase.json"/><Module url="ComComp.json"/><Module url="Grid.json"/><Module url="ListView.json"/></Modules><Components><Component type="JavaScript" id="Button" classname="nexacro.Button"/><Component type="JavaScript" id="CheckBox" classname="nexacro.CheckBox"/><Component type="JavaScript" id="Static" classname="nexacro.Static"/><Component type="JavaScript" id="ImageViewer" classname="nexacro.ImageViewer"/><Component type="JavaScript" id="Edit" classname="nexacro.Edit"/><Component type="JavaScript" id="Combo" classname="nexacro.Combo"/><Component type="JavaScript" id="FileUpload" classname="nexacro.FileUpload"/><Component type="JavaScript" id="Div" classname="nexacro.Div"/><Component type="JavaScript" id="Grid" classname="nexacro.Grid"/><Component type="JavaScript" id="Dataset" classname="nexacro.NormalDataset"/></Components><Services><Service prefixid="theme" type="resource" url="./_resource_/_theme_/" version="1.0.0" cachelevel="session" include_subdir="true"/><Service prefixid="xcssrc" type="resource" url="./_resource_/_xcss_/" version="1.0.0" cachelevel="session"/><Service prefixid="forms" type="form" url="./forms/" version="1.0.0" cachelevel="session"/><Service prefixid="lib" type="js" url="./lib/" version="1.0.0" cachelevel="session"/><Service prefixid="api" type="JSP" url="http://localhost:8080/api/" version="0" cachelevel="none"/></Services><Protocols/><DeviceAdaptors/><Update/><Deploy><Os name="Windows"/></Deploy></TypeDefinition>''',encoding='utf-8')
(ROOT/'appvariables.xml').write_text('''<?xml version="1.0" encoding="utf-8"?><AppVariables version="2.0"><Datasets/><Variables/><DataObjects/></AppVariables>''',encoding='utf-8')
(ROOT/'environment.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>
<ENV version="2.1"><Environment datatyperule="2.0" filesecurelevel="all" themeid="theme::inventory" httptimeout="30" httpretry="0"><ScreenDefinition><Screen id="Desktop_screen" type="desktop" themeid="theme::inventory"/></ScreenDefinition><Variables/><Cookies/><httpheader/></Environment><Script type="xscript5.1"><![CDATA[]]></Script></ENV>''',encoding='utf-8')
(ROOT/'_resource_'/'_theme_'/'inventory').mkdir(parents=True,exist_ok=True)
(ROOT/'_resource_'/'_theme_'/'inventory'/'theme.xcss').write_text('''<?xml version="1.0" encoding="utf-8"?>
<XCSS version="1.1"><CSSData><![CDATA[
.Form { background:#FFFFFF; color:#202329; }
]]></CSSData><CSSData type="mobile_medium"><![CDATA[]]></CSSData></XCSS>''',encoding='utf-8')

(ROOT/'lib'/'InventoryCommon.xjs').write_text('''<?xml version="1.0" encoding="utf-8"?>
<Script version="1.0" type="xscript5.1"><![CDATA[
this.gfnEmpty=function(v){return v===null||v===undefined||String(v).replace(/^\\s+|\\s+$/g,"")==="";};
this.gfnEmail=function(v){return /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(String(v||""));};
this.gfnNumber=function(v){return !this.gfnEmpty(v)&&!isNaN(Number(v))&&Number(v)>=0;};
this.gfnMessage=function(message){this.alert(message);};
this.gfnNavigate=function(name){this.getOwnerFrame().set_formurl("forms::"+name+".xfdl");};
this.gfnPopup=function(name,w,h,callback){
  var child=new ChildFrame();
  child.init("popup"+name,0,0,w,h);
  child.formurl="forms::"+name+".xfdl";
  child.openalign="center middle";
  child.showtitlebar=false;
  child.dragmovetype="all";
  child.background="#FFFFFF";
  child.border="1px solid #DCE5E2";
  child.showModal(this.getOwnerFrame(),{},this,callback);
};
/* One transaction entry point for the future xapi endpoints. */
this.gfnTransaction=function(id,path,input,output,args,callback){
  this.transaction(id,"api::"+path,input||"",output||"",args||"",callback||"onTransaction",true,0,false);
};
this.gfnSeed=function(){
  var app=nexacro.getApplication();
  if(!app.inventoryProducts)app.inventoryProducts=[
    {ProductID:"PRD-001",ProductName:"Wireless Mouse",Category:"Electronics",BuyingPrice:"24.00",Quantity:"120",Unit:"pcs",Threshold:"20",ExpiryDate:"2027-12-31",Supplier:"Tech Supplies",Status:"In stock"},
    {ProductID:"PRD-002",ProductName:"USB-C Hub",Category:"Electronics",BuyingPrice:"38.50",Quantity:"8",Unit:"pcs",Threshold:"15",ExpiryDate:"2027-12-31",Supplier:"Nova Trading",Status:"Low stock"},
    {ProductID:"PRD-003",ProductName:"Desk Lamp",Category:"Office",BuyingPrice:"42.00",Quantity:"0",Unit:"pcs",Threshold:"10",ExpiryDate:"2028-06-30",Supplier:"Bright Goods",Status:"Out of stock"},
    {ProductID:"PRD-004",ProductName:"Notebook A5",Category:"Stationery",BuyingPrice:"3.20",Quantity:"220",Unit:"pcs",Threshold:"40",ExpiryDate:"2028-12-31",Supplier:"Office Market",Status:"In stock"},
    {ProductID:"PRD-005",ProductName:"Water Bottle",Category:"Lifestyle",BuyingPrice:"9.90",Quantity:"65",Unit:"pcs",Threshold:"18",ExpiryDate:"2027-08-30",Supplier:"Nova Trading",Status:"In stock"}
  ];
  if(!app.inventorySuppliers)app.inventorySuppliers=[
    {SupplierID:"SUP-001",SupplierName:"Tech Supplies",Product:"Wireless Mouse",Category:"Electronics",BuyingPrice:"24.00",Contact:"0900000101",Email:"sales@tech.test",Type:"Taking return",OnTheWay:"20"},
    {SupplierID:"SUP-002",SupplierName:"Nova Trading",Product:"USB-C Hub",Category:"Electronics",BuyingPrice:"38.50",Contact:"0900000102",Email:"hello@nova.test",Type:"Not taking return",OnTheWay:"12"},
    {SupplierID:"SUP-003",SupplierName:"Bright Goods",Product:"Desk Lamp",Category:"Office",BuyingPrice:"42.00",Contact:"0900000103",Email:"contact@bright.test",Type:"Taking return",OnTheWay:"0"}
  ];
};
]]></Script>''',encoding='utf-8')

(ROOT/'_resource_'/'_xcss_'/'inventory.xcss').write_text('''<?xml version="1.0" encoding="utf-8"?>
<XCSS version="1.1"><CSSData><![CDATA[
Form { background:#F8FAFC; color:#1B2A41; font:14px "Segoe UI"; }
.Static.sidebar { background:#17322F; }
.Static.brand { color:#FFFFFF; font:700 26px "Segoe UI"; }
.Static.sideCaption { color:#91ABA5; font:600 11px "Segoe UI"; }
.Static.sideFoot { color:#AAC3BC; font:12px "Segoe UI"; }
.Button.nav, .Button.nav[status=focused] { background:transparent; color:#DBE8E2; border:0px none; textAlign:left; padding:0px 15px; font:600 15px "Segoe UI"; }
.Button.navActive, .Button.navActive[status=focused] { background:#2F6255; color:#FFFFFF; border:0px none; borderRadius:8px; textAlign:left; padding:0px 15px; font:600 15px "Segoe UI"; }
.Static.title { color:#172B2B; font:700 32px "Segoe UI"; }
.Static.muted { color:#81918E; font:14px "Segoe UI"; }
.Static.card { background:#FFFFFF; border:1px solid #E6ECEA; borderRadius:10px; }
.Static.cardLabel { color:#718783; font:14px "Segoe UI"; }
.Static.metric { color:#1E3732; font:700 34px "Segoe UI"; }
.Edit.field { background:#FFFFFF; border:1px solid #DCE5E2; borderRadius:7px; padding:0px 12px; color:#223632; font:14px "Segoe UI"; }
.Button.primary { background:#2D765E; color:#FFFFFF; border:0px none; borderRadius:7px; font:600 14px "Segoe UI"; }
.Button.secondary { background:#FFFFFF; color:#2B544A; border:1px solid #DCE5E2; borderRadius:7px; font:600 14px "Segoe UI"; }
.Button.link { background:transparent; border:0px none; color:#2D765E; font:600 13px "Segoe UI"; }
.Grid.dataGrid { background:#FFFFFF; border:1px solid #E6ECEA; color:#243B36; font:13px "Segoe UI"; }
.Static.authPanel { background:#173C32; }
.Static.authBrand { color:#FFFFFF; font:700 32px "Segoe UI"; }
.Static.authPitch { color:#FFFFFF; font:700 44px "Segoe UI"; }
.Static.authSub { color:#C6D9D1; font:17px "Segoe UI"; }
.Static.authTitle { color:#1A2E2A; font:700 34px "Segoe UI"; }
.Static.fieldLabel { color:#354B46; font:600 13px "Segoe UI"; }
.Static.hint { color:#879D95; font:12px "Segoe UI"; }
.Static.popupTitle { color:#1A2E2A; font:700 27px "Segoe UI"; }
.Static.detailTitle { color:#1A2E2A; font:700 28px "Segoe UI"; }
.Static.detailBody { color:#354B46; font:16px "Segoe UI"; }
.Static.sectionTitle { color:#1A2E2A; font:700 20px "Segoe UI"; }
.Static.cardBody { background:#FFFFFF; border:1px solid #E6ECEA; borderRadius:8px; padding:15px; color:#354B46; }
.Static.imagePlaceholder { background:#E5EEE9; borderRadius:10px; color:#7B9C90; textAlign:center; font:600 16px "Segoe UI"; }
.Static.status { background:#DDF2E5; color:#217151; borderRadius:6px; padding:5px 12px; font:600 14px "Segoe UI"; }
.Button.tab { background:#FFFFFF; color:#738782; border:0px none; font:600 14px "Segoe UI"; }
.Button.tabActive { background:#E6F1EC; color:#2D765E; border:0px none; font:600 14px "Segoe UI"; }
]]></CSSData></XCSS>'''.replace('borderRadius:', 'border-radius:').replace('textAlign:', 'text-align:'),encoding='utf-8')

from figma_layout import apply as apply_figma_layout
apply_figma_layout(ROOT)
from inventory_codegen import finalize as finalize_inventory
finalize_inventory(ROOT)
print('Generated and finalized', len(list((ROOT/'forms').glob('*.xfdl'))), 'Nexacro inventory forms')
