# CWNav

Python desktop navigation for Ciputra World Surabaya Ground Floor and 1st Floor.

## Run

From this folder, install dependencies with:
```powershell
python -m pip install -r requirements.txt
python main.py
```

Keep `main.py`, `navigation.py`, `ui/`, `data/`, `extracted-maps/`, and `requirements.txt` together. No development folder is needed to run the app. Original maps and sources.json attribution are preserved.

## Controls

- Click the left-panel section headers to expand or collapse search, nearest-route and nearby controls. Your route summary and Clear destination stay visible. The route preference dropdown is in the top header.

- Select a shop or facility to show its route.
- Search for East Lobby Exit, South Lobby Exit or North Lobby Exit to route to a Ground Floor exit approach (green markers).
- Choose a category under Nearest by walking route and click Find nearest. It selects the shortest reachable route from your current position across both floors, respecting the lift/escalator preference. Click again after moving or changing preferences to choose a new nearest destination.
- Nearby on your floor uses straight-line distance and its search radius. The Exit category shows only the nearest exit within that radius; no exits are mapped on 1st Floor. The Dijkstra search is independent of this radius.
- Click the map and use WASD or arrow keys to move along corridors.
- Default speed is 12 approximate m/s and can be adjusted.
- Drag to pan and scroll to zoom.
- Show player floor is in the top toolbar.
- Press E or Use floor connection within approximately 3 m along the connected walkway.
- Route preferences support lifts, escalators or either.
- Map picture and Graph toggle the display layers independently.

GeoPandas manages spatial layers and nearby queries, Shapely supplies geometry, Dijkstra finds routes and PySide6 displays the interface. Coordinates are local map units without a geographic CRS. Scale and physical access remain unverified.

## Project Architecture

The three lobby exit approaches and their short corridor branches are inferred from the supplied Ground Floor plan. Their physical positions, accessibility and scale are unverified; this is not a certified emergency evacuation map.

```text
CWNav/
├── main.py                  # Application entry point
├── navigation.py            # Core GIS spatial models, GeoPandas layers, and Dijkstra routing
├── data/
│   └── navigation-data.json # Indoor spatial nodes, corridor edges, and tenant access points
├── extracted-maps/          # SVG floor plans and directory metadata
├── ui/                      # Presentation layer (PySide6 / Qt)
│   ├── __init__.py          # UI package export
│   ├── main_window.py       # Main window controller
│   ├── map_view.py          # 2D interactive canvas for map and graphics compositing
│   ├── sidebar_panel.py     # Search, filter, and nearby facilities panel
│   ├── label_layout.py      # Label placement and typography layout
│   └── styles.py            # Global stylesheet and visual theme
└── requirements.txt         # Runtime dependencies (PySide6, Shapely, GeoPandas)
```
