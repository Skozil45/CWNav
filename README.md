# CWNav

Python desktop prototype for Ciputra World Surabaya Ground Floor and 1st Floor. Uses the supplied mall SVGs and directory offline, PySide6 for the interface, Shapely for spatial operations, and a standard-library Dijkstra implementation.

## Run

The active application and repository folder is `C:\Users\USER\Desktop\Kuliah\Semester 5\Computer Graphic\AFL2\Main\CWNav`. Keep future code, data, and asset changes in this folder.

From this directory, with Python 3.10 or newer:

```powershell
python -m pip install -r requirements.txt
python main.py
```

The tested environment is Windows, Python 3.14, PySide6 6.12.0. The dependency installation is needed once; running the app does not fetch web content. `main.py` resolves bundled data relative to its own location, so it can also be launched from another working directory. Missing or invalid data produces a startup error dialog.

## Controls

- Movement speed below the map controls adjusts keyboard movement from 0.5 to 12 approximate m/s (default 12). Changes apply immediately and reset to the default when the app restarts. Movement remains constrained to the same corridor graph.

- Search by tenant name or unit. Click a result or press Enter to select it.
- Click the map and use WASD or arrow keys. Movement selects the connected corridor most aligned with your input; it cannot move freely through a store.
- Drag the map to pan. Use the mouse wheel or zoom buttons to zoom; Reset view fits the floor.
- The floor selector changes only the viewed map. Show player floor in the top toolbar returns to your actual simulated floor.
- Within approximately 3 m of a purple connector along the connected walkway, press E or Use floor connection. The nearest eligible connector is selected, even across small corridor junctions. Straight-line closeness across a wall is not sufficient. A held E key cannot bounce back automatically, and movement input clears after the floor change.
- Choose Any floor connection, Lifts only, or Escalators only under Your route. This restricts the connections used by Dijkstra. Hover the action button to see the nearby connection's name. Search for the escalator name (for example, Frank & Co - Giordano) to route to the escalator approach rather than the shop entrance.
- Clear destination removes the route. Map picture toggles the supplied floor artwork. Graph independently toggles shop/service outlines, shared rails, mapped entry points, routes, connectors, player and search buffer. Both can be on or off; choices persist when switching floors. These are display controls: movement and GIS calculations continue.
- Graph-only shop outlines reuse the source SVG's shop/service-colored shapes. They are visual references, not surveyed tenant polygons or verified doors.
- Shop names use fixed positions inside the actual source shop silhouettes. The layout chooses centered text wrapping, size and an interior position with clearance from the shop boundary; it does not reposition labels during movement or zoom. All current directory markers match a silhouette. Names sharing one shape are grouped. Labels follow the Graph toggle; hover shows the full name and unit. Matching remains inferred rather than surveyed; unnamed shapes remain unlabeled. Tiny shops need zoom for readable labels.
- Nearby results use the player's floor, even when viewing the other floor. Categories include Stores, Dining, Toilets, Lifts, Escalators, and ATMs. Missing categories have a real empty state.
- The default 20 m search expands to 40 and 60 m if necessary. A custom radius is used as entered, with no expansion. Facility distances are straight-line distances; route distances follow the graph.

For a quick demonstration, select Fore on GF, then Lacoste on 1F. Try Lifts only and Escalators only to compare routes. Follow the teal route to its purple connection, use E, and continue on the destination floor. MyCWS Lounge, the west-side tenants, and the remaining interior stores now have approaches. Select Autoschoon or Redback to see why the supplied plans cannot establish those two access routes.

## Data and accuracy

This is a simulation with routes to 70 of 72 directory tenants and all 24 mapped facility approaches, not a surveyed wayfinding system. All distances and approach points are explicitly approximate. No GPS, backend, account, or live indoor positioning is involved.

The imported directory contains **72 tenant entries across GF and 1F**. It handles both single-string and array-valued floor assignments and converts descriptions to plain text. Raw HTML is never inserted into a web view. The directory supplies tenant markers, which are generally inside stores and are not entrance coordinates.

`navigation-data.json` adds a deliberately separate dataset:

- A shared rail graph derived offline by thinning the walkable corridor mask to one centerline. Short destination branches join the existing rails on first contact. Unused spurs and loops are removed, and intersections form real junctions. Dijkstra and player movement repeatedly use the same fixed graph, rather than generating a different geometric path for every destination. The graph has 430 nodes and 449 corridor segments.
- 70 inferred tenant approach points. These are corridor-side approaches, not verified doors. Interior directory markers remain separate from routing endpoints.
- Four inferred lift pairings: south, central, east, and north. Each has an illustrative 8 m travel weight.
- Five escalator pairings: Memo Paris–Laxmi Tailors, Frank & Co–Giordano, BOSS/information–Sociolla (pairings confirmed by the user); Marketing Office–Project Soul/Forever New and Oval East Atrium–Asics/JD Sports (inferred pairings approved for inclusion). The Sociolla endpoint uses the lower icon nearest Sociolla, not the upper MyCWS-side icon. Precise approaches and directions remain unverified. Each has an illustrative 12 m travel cost. All five escalator and four lift connections remain bidirectional prototype assumptions.
- 24 facility records: 6 toilet points, 8 lift endpoints, and 10 escalator endpoints. The Giordano endpoint now connects to Frank & Co; it does not connect to the excluded GF endpoint below Fore. Routes lead to corridor-side access points; they do not model the internal corridors of toilet/service cores.
- The user's latest annotated maps exclude five escalator locations from GIS: GF below Fore/CHAGEE, beside Metro's lift, and between H&M/Digimap; 1F in front of Birkenstock and below Hush Puppies. `excluded_escalators` records them in the navigation data. The excluded GF East facility and its inferred cross-floor edge were removed; ordinary corridor nodes/edges remain. The other four were not active GIS facilities. The source-map icons remain visible because this correction concerns GIS, not artwork. Unmarked sites are not automatically assigned new floor pairings.
- Six manually traced pale-atrium exclusion polygons, plus source-derived corridor masks. These are inferred spatial boundaries, not surveyed building geometry.

Two tenant access routes remain unsupported: Redback is in the detached MPH/exterior area, and Autoschoon is in the MSCP parking area. The supplied floor plans do not establish their connecting walkways/entrances. Their search results explain this instead of drawing a path through intervening walls or service areas. No GF/1F ATM records were present in the imported directory; no ATM position has been fabricated. Lift-only routing does not certify wheelchair accessibility. Stair routes, occupancy, exact doors, and every label-to-tenant association remain physically unverified.

### Coordinates and calibration

Both original SVGs have a `0 0 420 300` viewBox. The source website used a 1000 by 600 viewport with the SVG centered at scale 2, leaving 80 display pixels of horizontal padding on each side. Directory fractions `(u,v)` become:

```text
x = (u * 1000 - 80) / 2
y = v * 300
```

This conversion has numerical tests and was visually checked against Fore, CHAGEE, Lacoste, and other map positions. It is a display-coordinate conversion, not georeferencing.

`meters_per_unit` currently equals **1.0 as an illustrative assumption**, not a measurement. To calibrate:

1. Measure a known straight segment on site and identify its endpoints on the SVG.
2. Compute SVG length `sqrt((x2-x1)^2 + (y2-y1)^2)`.
3. Set `meters_per_unit = measured_meters / SVG_length` in `navigation-data.json`.
4. Independently measure connector travel lengths and replace each connector's `meters` value.
5. Verify the scale in multiple areas and on both floors. If the maps differ in scale, normalize them to one common coordinate system before using a shared factor.

The UI intentionally continues to say approximate, even if a data flag is changed: accurate entrances and connections require independent checks too.

### Editing the network

Add nodes with a unique ID, a `ground` or `first` floor, and `[x,y]` in SVG coordinates. Connect same-floor nodes in `edges`. The edge cost is Euclidean length times the scale. Add bends as intermediate nodes; do not draw a straight chord across a curved obstacle.

Add cross-floor connections only in `connectors`, with explicit positive meter costs. Same-floor edges must not connect different floors. The loader rejects zero-length edges, invalid coordinate values, invalid exclusion polygons, and edges crossing a mapped exclusion.

Map a tenant to an approach node using the key `floor:source-directory-id` in `entrances`. Approach points must be on the correct floor and connected to the network. Add separate facility records in `facilities`, with `entrance` omitted when unknown. Preserve evidence and uncertainty in the mapping notes.

Source SVG paths remain display artwork, not automatically validated GIS tenant polygons. Shapely Points represent markers and player position; LineStrings represent corridors; Polygons represent buffers and the explicitly mapped exclusions. Facility joins use intersection plus an exact circular boundary-distance check to avoid polygon approximation excluding a point exactly on the search radius.

### Regenerating the expanded mapping

`build_navigation.py` is an offline data-authoring tool. It uses the existing floor PNGs, the directory, reviewed approach coordinates in `APPROACHES`, and atrium exclusions in `EXCLUSIONS`. Scikit-image skeletonization creates the single shared corridor backbone. Approach branches stop when they first touch the rails; only existing rails needed between stops are retained. Simplification stays within 0.75 map units of the centerline and checks neighboring raster cells. Shapely splits intersections. Inspect overlays and the approach audit after changing inputs; extraction alone is not evidence of a real door or floor pairing.

This remains a GIS application: rails and routes are Shapely `LineString` geometry, the player and facilities are `Point` geometry, and proximity buffers/exclusions are `Polygon` geometry. Dijkstra uses planar segment lengths and explicit floor-connection costs. Nearby recommendations still use buffer analysis, spatial intersection and floor/category filtering. The rail appearance does not replace these spatial operations. Coordinates remain a local, uncalibrated map system, not a claimed GPS/EPSG projection.

```powershell
python -m pip install -r requirements-mapping.txt
python build_navigation.py
python -m unittest -v test_navigation
```

The extra image-processing packages are needed only to regenerate the data, not to run the desktop app. The builder overwrites `navigation-data.json`; make manual authoring changes in the builder's mapping inputs if you intend to regenerate.

## Files

- `extracted-maps/*-no-units.svg`: display variants with unit-number glyphs hidden. Keep these files with the app. Original SVGs and PNGs remain unchanged for source reference and mapping.
- `build_display_maps.py`: rebuilds those variants from reviewed source glyph blocks, with source SHA-256 checks and an assertion that other elements are unchanged. If source maps change, review the glyph blocks before updating the hashes. Unit numbers remain available in search and tooltips.
- The original MYCWS LOUNGE text is also hidden in the display SVG. Its independent Graph label, searchable destination and route remain available.
- `label_layout.py`: fits fixed labels into source silhouettes sampled at four pixels per map unit, without changing GIS navigation geometry.
- `verify_network.py`: checks every network node, every supported destination pair in all three transport modes, and traversal of every corridor segment in both directions. Writes `verification/network-connectivity.json`.

- `main.py`: desktop interface, SVG rendering, keyboard/on-screen input, route overlays.
- `navigation.py`: data loading, coordinate conversion, graph routing, constrained movement, spatial queries.
- `navigation-data.json`: editable, inferred navigation dataset.
- `extracted-maps/`: unchanged original assets and extracted directory. `sources.json` records floor-plan URLs.
- `test_navigation.py`: logic tests.
- `verify_ui.py`: repeatable Qt interaction checks and screenshots.
- `VALIDATION.md`: evidence and remaining limitations.

## Verify

```powershell
python -m unittest -v test_navigation
python verify_ui.py
python benchmark_ui.py
```

The UI verification briefly opens a test window, writes screenshots and a check list into `verification/`, then closes. It exercises simulated input and UI state; it does not prove real-world map accuracy.

The performance check measures warm updates including painting at fit and 4x zoom on both floors, with the full network overlay, a cross-floor lift-only route, all categories and a 60 m buffer. Results are written to `verification/performance.json`. Movement uses a 16 ms timer; routes and sidebar results update at most every 100 ms while walking. Controls still refresh immediately. Detailed SVG artwork is cached at about 4200 by 3000 physical pixels per floor, using approximately 50 MB per floor. First-time floor rendering still has a one-time cost; extreme zoom can soften cached labels. Original SVGs remain unchanged.

## Source and reuse

Source: Ciputra World Surabaya's mall directory, supplied as copied page HTML by the user. Original floor URLs are recorded in `extracted-maps/sources.json`. This project does not change those assets or assert ownership of the mall artwork. Retain source attribution when presenting the academic prototype.
