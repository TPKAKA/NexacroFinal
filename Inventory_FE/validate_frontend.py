"""Basic structural and script checks for the generated Nexacro source."""
import pathlib
import re
import subprocess
import xml.etree.ElementTree as ET
from inventory_codegen import FRONTEND_VERSION

root = pathlib.Path(__file__).resolve().parent
forms = sorted((root / 'forms').glob('*.xfdl'))
files = forms + list((root / 'lib').glob('*.xjs')) + list(root.glob('*.xml')) + list(root.glob('*.xprj')) + list(root.glob('*.xadl')) + list((root / '_resource_' / '_xcss_').glob('*.xcss'))
errors = []
for path in files:
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        errors.append(f'{path}: {exc}')
        continue
    script_node = tree.find('.//Script')
    if script_node is not None and script_node.text:
        script = re.sub(r'^include .*?;', '', script_node.text, flags=re.M)
        check = subprocess.run(['node', '--check'], input=script, text=True,
                               encoding='utf-8', capture_output=True)
        if check.returncode:
            errors.append(f'{path}: {check.stderr.strip()}')
        if re.search(r'\beval\s*\(', script):
            errors.append(f'{path}: eval is not allowed')
        if path.suffix == '.xfdl':
            handlers = re.findall(r'\bon[a-z]+="([^"]+)"', path.read_text(encoding='utf-8'))
            for handler in handlers:
                if not re.search(r'\bthis\.' + re.escape(handler) + r'\s*=', script):
                    errors.append(f'{path}: missing {handler}')
    if path.suffix == '.xfdl':
        form = tree.getroot().find('./Form')
        if form is None:
            errors.append(f'{path}: missing Form element')
            continue
        if form.findall('./BindItem'):
            errors.append(f'{path}: BindItem must be nested under <Bind>')
        controls = {node.get('id') for node in form.findall('.//Layouts//Layout//*') if node.get('id')}
        datasets = {node.get('id'): node for node in form.findall('./Objects/Dataset') if node.get('id')}
        for binding in form.findall('./Bind/BindItem'):
            component = binding.get('compid', '').split('.')[-1]
            dataset_id = binding.get('datasetid', '')
            column_id = binding.get('columnid', '')
            if component not in controls:
                errors.append(f'{path}: binding references missing component {component}')
            dataset = datasets.get(dataset_id)
            if dataset is None:
                errors.append(f'{path}: binding references missing Dataset {dataset_id}')
            elif dataset.find(f'./ColumnInfo/Column[@id="{column_id}"]') is None:
                errors.append(f'{path}: binding references missing column {dataset_id}.{column_id}')
assert len(forms) == 8, f'Expected 8 forms, found {len(forms)}'
application = ET.parse(root / 'Application.xadl').getroot().find('./Application')
if application is None or application.get('checkversion') != 'true' or not application.get('version'):
    errors.append('Application.xadl: WRE CheckVersion/version is not configured')
elif application.get('version') != FRONTEND_VERSION:
    errors.append('Application.xadl: frontend version does not match the generator')
environment = ET.parse(root / 'environment.xml').getroot().find('./Environment')
if environment is None or environment.get('httptimeout') != '30' or environment.get('httpretry') != '0':
    errors.append('environment.xml: HTTP timeout/retry is not configured')
typedefinition = ET.parse(root / 'typedefinition.xml').getroot()
for prefix in ('theme', 'xcssrc', 'forms', 'lib'):
    service = next((node for node in typedefinition.findall('./Services/Service')
                    if node.get('prefixid') == prefix), None)
    if service is None or service.get('version') != FRONTEND_VERSION:
        errors.append(f'typedefinition.xml: {prefix} version does not match the generator')
    if prefix in ('forms', 'lib') and service is not None and service.get('cachelevel') != 'none':
        errors.append(f'typedefinition.xml: {prefix} must not cache JavaScript during development')
components = {node.get('id'): node for node in typedefinition.findall('./Components/Component')}
if 'ImageViewer' not in components:
    errors.append('typedefinition.xml: ImageViewer is not registered')
api_service = next((node for node in typedefinition.findall('./Services/Service') if node.get('prefixid') == 'api'), None)
if api_service is None or api_service.get('cachelevel') != 'none' or not api_service.get('url', '').endswith('/api/'):
    errors.append('typedefinition.xml: API service prefix/cache configuration is invalid')
detail = ET.parse(root / 'forms' / 'ProductDetail.xfdl').getroot().find('./Form')
if detail.find('.//Layouts//ImageViewer[@id="staImage"]') is None:
    errors.append('ProductDetail.xfdl: product image must use ImageViewer')
if not any(binding.get('compid') == 'staImage' and binding.get('propid') == 'image'
           for binding in detail.findall('./Bind/BindItem')):
    errors.append('ProductDetail.xfdl: product image is not Dataset-bound')
inventory = ET.parse(root / 'forms' / 'InventoryList.xfdl').getroot().find('./Form')
summary_dataset = next((dataset for dataset in inventory.findall('./Objects/Dataset')
                        if dataset.get('id') == 'dsSummary'), None)
if summary_dataset is None or summary_dataset.find('./ColumnInfo/Column[@id="FilteredProducts"]') is None:
    errors.append('InventoryList.xfdl: filtered product count is missing from dsSummary')
inventory_script = inventory.find('./Script').text or ''
if 'getColumn(0, "FilteredProducts")' not in inventory_script:
    errors.append('InventoryList.xfdl: pagination must use the filtered product count')
column_chooser = ET.parse(root / 'forms' / 'ColumnChooser.xfdl').getroot().find('./Form')
chooser_grid = column_chooser.find('.//Layouts//Grid[@id="grdColumns"]')
chooser_script = column_chooser.find('./Script').text or ''
if chooser_grid is None or chooser_grid.get('oncellclick') != 'onColumnClick':
    errors.append('ColumnChooser.xfdl: columns must be toggled by clicking a row')
if 'grid._chosenVisibleColumns = selectedColumns' not in chooser_script:
    errors.append('ColumnChooser.xfdl: selected columns must persist after resize')
common_script = (root / 'lib' / 'InventoryCommon.xjs').read_text(encoding='utf-8')
if not re.search(r'\bthis\.gfnResponsiveShell\s*=\s*function\s*\(', common_script):
    errors.append('InventoryCommon.xjs: gfnResponsiveShell is missing')
for form_name in ('InventoryList.xfdl', 'SupplierList.xfdl', 'ProductDetail.xfdl'):
    form_script = ET.parse(root / 'forms' / form_name).getroot().find('./Form/Script').text or ''
    if 'include "lib::InventoryCommon.xjs";' not in form_script:
        errors.append(f'{form_name}: shared responsive functions are not included')
if '@param' not in common_script or '@returns' not in common_script:
    errors.append('InventoryCommon.xjs: public common functions need jsDoc')
if 'loadXML(app.inventoryCodeCache, true)' not in common_script:
    errors.append('InventoryCommon.xjs: cached Dataset load must replace existing rows')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'Validated {len(forms)} forms and {len(files)} XML source files.')
