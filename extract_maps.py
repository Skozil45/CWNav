from pathlib import Path
import json
import re
import urllib.request
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import fitz

source = Path(r'C:\Users\USER\.codex\attachments\85386070-d0e0-4a2c-9d1e-49385d48e5f1\Pasted text.txt')
output = Path(__file__).parent / 'extracted-maps'
output.mkdir(exist_ok=True)
html = source.read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')
data = json.loads(soup.find('mapplic-map')['data-json'])
(output / 'map-data.json').write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
embedded = max(re.findall(r'<svg\b.*?</svg>', html, re.S), key=len)
(output / 'ground-floor-embedded.svg').write_text(embedded, encoding='utf-8')
records = []
for layer in data['layers']:
    name = layer['name']
    filename = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    try:
        request = urllib.request.Request(layer['file'], headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=30) as response:
            svg = response.read()
        assert ET.fromstring(svg).tag.endswith('svg'), 'Response is not SVG'
        (output / (filename + '.svg')).write_bytes(svg)
        document = fitz.open(stream=svg, filetype='svg')
        page = document[0]
        page.get_pixmap(matrix=fitz.Matrix(2400 / page.rect.width, 2400 / page.rect.width)).save(output / (filename + '.png'))
        records.append({'floor': name, 'source': layer['file'], 'svg': filename + '.svg', 'png': filename + '.png'})
        print(name, 'saved and rendered')
    except Exception as error:
        print(name, 'FAILED:', error)
        records.append({'floor': name, 'source': layer['file'], 'error': str(error)})
(output / 'sources.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
assert ET.fromstring(embedded).tag.endswith('svg')
print('Output:', output)
