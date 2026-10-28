# CWNav verification

## Scope and evidence

### Floor-connection approach tolerance (2026-10-28)

The former 1 m check only considered the player's current edge endpoints, so a nearby connection beyond a short corridor junction could remain unavailable. It is replaced with a bounded same-floor graph search seeded at the player's exact edge position. The nearest connection within 3 approximate metres of walkway travel is usable. It cannot cross a floor connection or disconnected wall gap when measuring proximity. Holding E ignores auto-repeat, and a successful transition clears movement input.

All 24 logic tests pass, including walking a route to all ten escalator endpoints using the eight keyboard headings, using every escalator from 2.5 m away in both directions, exact-radius inclusion, exclusion beyond the radius, and rejection of a geometrically nearby disconnected walkway. The 166 UI checks include all five pairs in both directions from 2.5 m away, with both the button and E, plus held-E bounce prevention. Frank & Co and BOSS/information–Sociolla pass these checks. The full network audit still passes 26,508 destination pairs and 898 directed corridor traversals. No map geometry or physical escalator direction was changed; distances remain uncalibrated.

### Five requested escalator pairings (2026-10-28)

The builder now authors all five requested pairs: Memo Paris–Laxmi Tailors, Frank & Co–Giordano, BOSS/information–Sociolla, Marketing Office–Project Soul/Forever New, and Oval East Atrium–Asics/JD Sports. The first three carry `pairing_source: user-confirmed`; the last two remain inferred. The lower Sociolla-side icon is used for BOSS; precise approaches, travel cost and operational direction remain approximate. All five prior exclusions remain in force. The former GF Fore endpoint is still an ordinary corridor node with no floor transition; Giordano now connects only through its new Frank & Co counterpart.

Regenerated shared rails contain 430 nodes and 449 corridor segments. All 94 supported destinations (70 tenants and 24 facilities) are reachable in each transport mode. The network audit passes 8,836 ordered pairs per mode, 26,508 total, and 898 directed corridor traversals. All 22 logic tests and 106 UI checks pass, including exact pair identity, five escalator/four lift transitions in both directions, exclusions, corridor-mask containment and routing filters. No physical-direction validation is claimed. These counts supersede prior reports below.

### User-annotated escalator exclusions (2026-10-28)

Five crossed locations are recorded in `excluded_escalators`: three on GF (below Fore, beside Metro/lift, between H&M and Digimap), two on 1F (Birkenstock frontage, below Hush Puppies). Only the first was previously modeled as an active GIS escalator facility/connection. The GF East facility and East cross-floor edge are now absent; the unmarked 1F Giordano endpoint remains a facility with no transition. Four other crossed icons had no active GIS records. No corridor edges were removed. The builder retains the exclusions and no longer generates the East connection. Source artwork is unchanged.

21 logic tests and 106 UI checks pass. Negative tests reject transitions at both former East endpoints and check that no active escalator facility lies at any excluded site. The network audit passes 7,921 ordered destination pairs per transport mode (23,763 total), with all 421 nodes reachable and all 440 corridor edges traversable in both directions. There are now 89 supported destinations, including 19 facilities, with two inferred escalator pairs and four lift pairs. This supersedes older counts below. Remaining escalator pairings and directions are still unverified; no new pairing was invented from the annotated screenshots.

### Silhouette label layout, lounge artwork and full route audit (2026-10-28)

This supersedes the earlier bounding-box label method. Source shop shapes are rasterized at four samples per map unit, and each directory marker is matched by silhouette containment. All 72 shop entries match without fallback. Labels choose a fixed interior position, wrapping and font scale with a boundary margin. All label rectangles fit inside the matched silhouettes and no label rectangles overlap on either floor. They remain fixed through zoom and refresh; small-shop text requires zoom. Both floors were visually inspected. These are display silhouettes, not surveyed GIS tenant polygons.

Only the original first-floor MYCWS LOUNGE glyph block (source elements 830–841) is additionally hidden in the derived display SVG. The graph label and routed destination remain. Source hashes and the builder's attribute comparison confirm that the original maps and all other display elements are preserved.

Validation: 20 logic tests and 106 Qt interaction checks pass. `verify_network.py` confirms all 421 nodes are reachable in Any, Lifts only and Escalators only modes. All 8,100 ordered pairs of the 90 supported destinations pass per mode (24,300 total); paths use valid adjacent edges and respect the selected connector type. All 440 corridor segments pass simulated movement in both directions (880 traversals). Existing tests also sample every edge against corridor masks and test all seven floor connections in both directions. No disconnected mapped network segment was found. Redback and Autoschoon remain explicitly unsupported because their external/parking connections cannot be established from supplied maps; this audit does not invent those paths or certify real-world access.

Warm UI benchmark p95: GF fit/4x 25.03/7.11 ms; 1F fit/4x 27.11/7.63 ms, all below the 50 ms budget. Silhouette fitting happens once per loaded floor and adds initial loading work, not per movement update.

### Map unit numbers removed (2026-10-28)

The display now loads derived GF/1F SVGs with only the reviewed unit-number vector blocks hidden. The builder verifies source hashes and asserts that all other element attributes remain unchanged. Source SVGs/PNGs, routing data, facility icons and non-unit map text are preserved. Both rendered floors were visually inspected and all 100 UI checks passed. Unit numbers remain in directory search/details; no route or physical accuracy claims change.

### Adjustable movement speed (2026-10-28)

The speed control supports 0.5–12 approximate m/s, default 3. The shared movement routine uses the selected speed for both input methods without changing corridor constraints or the elapsed-time cap. All 20 logic tests pass, including speed changes, distance scaling, and rejection of nonpositive/nonfinite speed. The UI suite passes 92 checks including keyboard and on-screen speed forwarding. The physical speed remains uncalibrated because map scale is illustrative.

### Fixed shop labels (2026-10-28)

Names now use fixed map coordinates at matched source shop bounding-box centers, with directory coordinates as the fallback. Multiple directory names assigned to the same shape share one label. Text wraps and scales to fit, remains anchored during zoom/refresh, and follows Graph visibility. All 72 directory shop entries are represented; shapes without directory names are not invented. Both graph-only floor screenshots were visually checked. The UI suite passes 90 checks, including name coverage, fixed positions and layer visibility. Shape association is inferred from marker containment in bounds, not verified polygon containment or surveyed occupancy. The prior performance timings below predate these labels; performance was not rebenchmarked for this change.

### Independent visual layers (2026-10-28)

Map picture and Graph are independent visibility controls. Graph includes source-derived shop/service outlines, mapped approach points, shared rails, route segments, connectors, player and buffer. All four combinations were checked on both floors, after refresh/player updates and across a floor switch. The Qt suite now passes 78 checks; the 19 logic tests still pass. Graph-only and compact screenshots were inspected: controls remain readable, original map shapes are preserved, and no new visual theme or decoration was introduced.

The latest benchmark with both layers enabled measures p95 updates of 25.57/24.74 ms on GF (fit/4x) and 40.27/35.00 ms on 1F, passing the existing 50 ms budget. These supersede the earlier timings below. A second cached transparent image adds roughly 50 MB per loaded floor. Shop outlines are selected from the source SVG shop/service fill colors; they are display geometry, not newly verified GIS tenant boundaries. Visibility changes do not change routing, movement, or spatial-query data.

The delivered app is a Python-only, offline desktop prototype for GF and 1F. No React/web frontend or backend was added. Its runtime entry point is `python main.py`.

Logic checks: `python -m unittest -v test_navigation` passes 19 tests. In addition to routing, spatial queries, coordinates and movement, the suite checks every supported destination under all three transport modes; every lift/escalator transition in both directions; lift-only exclusion of escalators; and dense samples along every edge against the reviewed corridor masks. A complete cross-floor route is walked to arrival. The new rail regression verifies that different destinations share existing edges, routing does not mutate the graph, and GIS LineStrings contain no duplicate overlapping lengths.

UI checks: `python verify_ui.py` launches a real PySide6 window and records 52 passing checks in `verification/ui-checks.json`. These include lift-only and escalator-only selection, a lift action that changes floors, routing to the newly mapped lounge, and an explanation for unsupported parking access. Earlier search, movement, mouse, floor, nearby, arrival, cache-reuse and map-alignment checks remain in the suite. Screenshots show GF, 1F, and a compact desktop layout.

## Performance update

After the routing expansion, the stress benchmark also enables the full corridor overlay and recalculates a cross-floor lift-only route with all categories and a 60 m facility buffer. Warm 4x-zoom medians are 13.52 ms (GF) and 14.17 ms (1F), with p95 values 16.08 ms and 17.14 ms. All four fit/zoom cases pass the 50 ms budget. The following earlier figures describe the initial rendering optimization before this expanded workload.

The original warm 4x-zoom benchmark measured median updates of 793.01 ms on GF and 862.36 ms on 1F, including synchronous painting. The matching updated benchmark measured 7.45 ms and 7.57 ms, respectively, on this machine. Updated p95 values were 8.72 ms on both floors. These are synthetic warm-update timings, not a guarantee of display refresh rate or cold-start speed. `benchmark_ui.py` reproduces the workload and writes `verification/performance.json`; all four floor/zoom cases passed its 50 ms p95 regression budget.

Map artwork now uses an explicit 4200 by 3000 pixel render of the original SVG rather than repeatedly repainting thousands of SVG paths when zoomed. Each floor render occupies approximately 50 MB, and floor items are retained between switches. Static corridor paths and the moving player/buffer items are reused. Movement ticks every 16 ms; route/list detail refreshes are limited to 10 Hz while walking. Startup and first rendering of each floor still incur a one-time cost; very deep zoom can soften cached labels. Source SVG files were not changed.

Screenshots were inspected. A dark Windows palette leaking into the sidebar was found and corrected by explicitly setting the application surface color. Final text is dark on light surfaces. The original mall map's small labels remain part of the supplied artwork and can be enlarged by zooming.

## Spatial audit

All 72 GF/1F directory entries were imported: 27 GF and 45 1F. The shared rail network routes to 70 tenants and all 20 mapped facility access points, using 421 nodes and 440 corridor edges, reduced from the previous 1,444 nodes and 2,468 overlapping-path segments. Four lift pairs and three escalator pairs connect the floors. Every supported destination remains reachable under Any, Lifts only, and Escalators only. `verification/data-audit.json` records each source marker and approach; `verification/approach-audit.json` records how reviewed positions were fitted to corridor space.

The offline mapping tool follows corridor color, excludes dark voids/tenant fills, and subtracts six manually traced pale atriums. Small lettering gaps and isolated annotation holes are filled without filling components containing tenant/service colors. A thinned centerline provides one reusable rail backbone. Destination branches join that backbone; unused spurs and loops are removed. Simplification is limited to 0.75 map units from the centerline and must remain within the accepted mask. The complete edge scan passes. The final rail overlay and application screenshots were visually inspected. This proves consistency with the prototype masks, not surveyed doors or building geometry.

GIS is preserved: LineString rails and route segments, Point positions/facilities, Polygon buffers and exclusions, planar distance, spatial intersection, and floor/category filtering remain active. Only the route network construction and display changed. The latest rail benchmark passes the 50 ms p95 budget on both floors at fit and 4x zoom; measured p95 values are all below 15 ms on this machine.

Sampled displayed routes include GF start to Fore, newly covered MyCWS Lounge, and cross-floor Lacoste routes using both transport filters. The route ends at a corridor-side approach, which can differ from the interior directory marker or a facility symbol. In particular, service-core approaches stop at the corridor edge rather than inventing an internal toilet passage. Original SVG geometry is retained in the cached render.

## Design checks

- Direction: a calm map-first academic desktop tool using the supplied mall artwork; ENERGY 1, RHYTHM 1, MOTION 1. Teal identifies navigation, rust distinguishes the destination, purple identifies a connector. Neutral controls defer to the map. Segoe UI follows the Windows environment.
- Hard gate: startup and interaction checks pass; missing data has an error dialog; searches and recommendations have empty states; unmapped routes have an explicit message. All application controls have working handlers and keyboard focus styles. Approximate data is visibly labeled.
- Purpose gate: no promotional sections, fabricated metrics, testimonials, unrelated icons, background patterns, or decorative animation. Borders distinguish controls and the map canvas. Color serves route/state identification.
- Liveliness: the map is the primary visual focus, whitespace separates the tool panel, the CWNav name and navigation color provide consistent identity; movement is functional only.
- Craft: maps retain the supplied appearance; a compact layout was inspected; controls use native widgets and accessible names. No complete accessibility audit or screen-reader certification is claimed.

## Unverified and unsupported

- Physical scale, tenant occupancy, exact doors, full corridor coverage, and all source-unit matches remain unverified.
- Lift costs of 8 m, escalator costs of 12 m, connector pairings, and bidirectional behavior are illustrative assumptions. Real direction, pairing, service access and measurements require a site survey.
- Redback's detached MPH/exterior connection and Autoschoon's MSCP parking access are not established by the supplied plans. Those two remain explicitly unavailable. No connection through the intervening building/service area was fabricated.
- Facility approaches are approximate corridor access points, not surveyed internal paths. Stair routes remain unsupported; lift-only routing is not certification of wheelchair accessibility.
- GF/1F ATM coverage is absent from the supplied directory; an empty category is intentional.
- Exclusions and corridor masks are inferred from artwork. They do not establish a surveyed building collision model. Player movement is restricted to the generated graph rather than arbitrary free-space walking.
- The app recalculates the remaining shortest route as the player moves; initial distance stays visible as a reference. It is a simulated player, not indoor positioning.
- Scheduled continuation was created for this chat at an hourly interval. A schedule cannot bypass usage limits; successful execution after a reset is not proven merely by creating it.
