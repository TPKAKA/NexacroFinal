"""Basic structural and script checks for the generated Nexacro source."""
import pathlib
import re
import subprocess
import xml.etree.ElementTree as ET

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
        check = subprocess.run(['node', '--check'], input=script, text=True, capture_output=True)
        if check.returncode:
            errors.append(f'{path}: {check.stderr.strip()}')
        if path.suffix == '.xfdl':
            handlers = re.findall(r'\b(?:onclick|onload|oncelldblclick)="([^"]+)"', path.read_text(encoding='utf-8'))
            for handler in handlers:
                if not re.search(r'\bthis\.' + re.escape(handler) + r'\s*=', script):
                    errors.append(f'{path}: missing {handler}')
assert len(forms) == 7, f'Expected 7 forms, found {len(forms)}'
if errors:
    raise SystemExit('\n'.join(errors))
print(f'Validated {len(forms)} forms and {len(files)} XML source files.')
