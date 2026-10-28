"""Create display SVGs without unit-number glyphs; preserve the source maps."""
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent / 'extracted-maps'
# Reviewed glyph blocks in these exact source revisions; adjacent facility text stays.
SOURCES = {
    'ground-floor': ('c7b9f0099959ad70f0919d8c20225c71f8eb604f58c65965e9d30e7309f58554', 591, 768),
    '1st-floor': ('13defe1aeca82ad5635f90331c0b05cee1ff0a7a9a5789c90b78478758aaf69a', 587, 830),
}


def main():
    for name, (expected, start, stop) in SOURCES.items():
        source = (ROOT / f'{name}.svg').read_bytes()
        if hashlib.sha256(source).hexdigest() != expected:
            raise ValueError(f'{name}: source changed; review unit-number glyphs before rebuilding')
        root = ET.fromstring(source)
        elements = list(root.iter())
        hidden = set(range(start, stop))
        if name == '1st-floor':
            hidden.update(range(830, 842))  # Original MYCWS LOUNGE glyphs; graph labels are separate.
        for index in hidden:
            elements[index].set('display', 'none')
        output = ROOT / f'{name}-no-units.svg'
        output.write_bytes(ET.tostring(root, encoding='utf-8', xml_declaration=True))
        rebuilt = list(ET.parse(output).iter())
        original = list(ET.fromstring(source).iter())
        assert len(rebuilt) == len(original)
        for index, (before, after) in enumerate(zip(original, rebuilt)):
            expected_attrs = dict(before.attrib)
            if index in hidden:
                expected_attrs['display'] = 'none'
            assert after.attrib == expected_attrs and after.tag == before.tag
        print(f'{output.name}: only reviewed unit-number / lounge artwork elements hidden')


if __name__ == '__main__':
    main()
