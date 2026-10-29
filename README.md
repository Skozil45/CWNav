# CWNav

Python desktop navigation for Ciputra World Surabaya Ground Floor and 1st Floor.

## Run

From this folder, install dependencies with: python -m pip install -r requirements.txt
Then launch with: python main.py

Keep main.py, navigation.py, label_layout.py, navigation-data.json, requirements.txt and extracted-maps/ together. No development folder is needed to run the app. Original maps and sources.json attribution are preserved. .git and .gitignore are repository metadata. Python may recreate __pycache__ automatically.

## Controls

Select a shop or facility to show its route. Click the map and use WASD or arrow keys to move along corridors. Default speed is 12 approximate m/s and can be adjusted. Drag to pan and scroll to zoom. Show player floor is in the top toolbar.

Press E or Use floor connection within approximately 3 m along the connected walkway. Route preferences support lifts, escalators or either. Map picture and Graph toggle the display layers independently.

GeoPandas manages spatial layers and nearby queries, Shapely supplies geometry, Dijkstra finds routes and PySide6 displays the interface. Coordinates are local map units without a geographic CRS. Scale and physical access remain unverified.

## Development files

Tests, mapping tools, detailed documentation and verification outputs are in ../CWNav-development/. That folder is outside this Git repository; back it up separately. It is not required to launch the app.
