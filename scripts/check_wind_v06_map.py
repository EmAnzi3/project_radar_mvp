#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIND = ROOT / "docs" / "wind"
html = (WIND / "index.html").read_text(encoding="utf-8")
js = (WIND / "assets" / "province-map-v06.js").read_text(encoding="utf-8")
css = (WIND / "assets" / "province-map-v06.css").read_text(encoding="utf-8")

assert 'id="provinceMap"' in html
assert 'Mappa per provincia' in html
assert 'data-metric="mw"' in html
assert 'data-metric="projects"' in html
assert 'data-metric="e4mw"' in html
assert 'assets/province-map-v06.css' in html
assert 'assets/province-map-v06.js' in html
assert 'echarts@5' in html
assert 'italy-base.svg' not in html, "old static marker-map base should no longer be visible"
assert 'class="map-marker' not in html

assert "openpolis/geojson-italy" in js
assert "wind_italy_provinces" in js
assert "type:'map'" in js
assert "visualMap" in js
assert "BESS non sommato" in js
assert "row.mw+=+p.mw" in js
assert "row.e4mw+=+p.mw" in js
assert "row.projects++" in js
assert "normProvince(p.province)" in js
assert "p.lat" not in js and "p.lon" not in js, "province map must not regress to project marker coordinates"
assert ".province-map-viz" in css
assert ".legacy-map-compat" in css

print("v0.6 province map OK: choropleth by canonical province with MW/projects/E4+ metrics and no project-marker dependence")
