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

- Select a shop or facility to show its route.
- Click the map and use WASD or arrow keys to move along corridors.
- Default speed is 12 approximate m/s and can be adjusted.
- Drag to pan and scroll to zoom.
- Show player floor is in the top toolbar.
- Press E or Use floor connection within approximately 3 m along the connected walkway.
- Route preferences support lifts, escalators or either.
- Map picture and Graph toggle the display layers independently.

GeoPandas manages spatial layers and nearby queries, Shapely supplies geometry, Dijkstra finds routes and PySide6 displays the interface. Coordinates are local map units without a geographic CRS. Scale and physical access remain unverified.

## Project Architecture

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
