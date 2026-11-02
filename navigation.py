from dataclasses import dataclass
from heapq import heappop, heappush
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re

import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon

ROOT = Path(__file__).resolve().parent
FLOORS = {'ground': 'Ground Floor', 'first': '1st Floor'}
CATEGORIES = ['All', 'Dining', 'Toilets', 'Lifts', 'Escalators', 'ATMs', 'Stores', 'Exit']


class PlainText(HTMLParser):
    """Simple HTML stripper for location descriptions."""

    def __init__(self, value: str):
        super().__init__()
        self.parts = []
        self.feed(value)

    def handle_data(self, data: str):
        self.parts.append(data)


def directory_position(coord: tuple) -> tuple[float, float]:
    """Convert normalized web coordinates to local SVG planar coordinates.
    
    The 420x300 SVG is centered in the source site's 1000x600 viewport.
    """
    return ((float(coord[0]) * 1000 - 80) / 2, float(coord[1]) * 300)


@dataclass
class Place:
    """Represents a store, facility, or point of interest."""
    id: str
    title: str
    floor: str
    unit: str
    category: str
    xy: tuple
    description: str = ''
    entrance: str | None = None


def load_places(data: dict) -> list[Place]:
    """Extract and parse place definitions from map-data JSON."""
    places = []
    for row in data.get('locations', []):
        floors = row.get('layer', [])
        floors = [floors] if isinstance(floors, str) else floors
        for floor in floors:
            if floor not in FLOORS:
                continue
            text = ' '.join(PlainText(row.get('desc', '')).parts)
            match = re.search(r'Unit\s+([A-Za-z0-9]+(?:\s*[-,]\s*[A-Za-z0-9]+)*)', text)
            category = 'Dining' if 'group2' in row.get('group', []) else 'Stores'
            if 'ATM' in row.get('title', '').upper():
                category = 'ATMs'
            xy = directory_position(row['coord'])
            if not all(math.isfinite(v) for v in xy):
                raise ValueError(f"Invalid coordinates: {row['id']}")
            places.append(Place(
                f"{floor}:{row['id']}",
                row['title'],
                floor,
                match[1] if match else '',
                category,
                xy,
                text
            ))
    return places


class Model:
    """Core GIS model managing vector layers, corridor network, and spatial queries."""

    def __init__(self, root: Path = ROOT):
        data_path = root / 'data' / 'navigation-data.json'
        if not data_path.exists():
            data_path = root / 'navigation-data.json'
        self.data = json.loads(data_path.read_text(encoding='utf-8'))
        self.scale = float(self.data['meters_per_unit'])
        if not math.isfinite(self.scale) or self.scale <= 0:
            raise ValueError('meters_per_unit must be finite and positive')

        self.nodes = self.data['nodes']
        for key, node in self.nodes.items():
            if node['floor'] not in FLOORS or len(node['xy']) != 2 or not all(math.isfinite(v) for v in node['xy']):
                raise ValueError(f'Invalid node: {key}')

        # Excluded / non-walkable planar polygons
        self.exclusions = [(row['floor'], Polygon(row['ring'])) for row in self.data['excluded_areas']]
        self.exclusions_gdf = gpd.GeoDataFrame(
            {'floor': [floor for floor, _ in self.exclusions]},
            geometry=[polygon for _, polygon in self.exclusions],
            crs=None
        )
        if not self.exclusions_gdf.is_valid.all():
            raise ValueError('Invalid exclusion polygon')

        # Corridor centerline graph construction
        self.graph = {key: [] for key in self.nodes}
        self.edges = []
        self.connector_kinds = {}

        for a, b in self.data['edges']:
            if self.nodes[a]['floor'] != self.nodes[b]['floor']:
                raise ValueError('Cross-floor edges must be explicit connectors')
            line = LineString([self.nodes[a]['xy'], self.nodes[b]['xy']])
            if line.length <= 0:
                raise ValueError('Zero-length edge')
            exclusions = self.exclusions_gdf[self.exclusions_gdf.floor == self.nodes[a]['floor']]
            if exclusions.intersects(line).any():
                raise ValueError(f'Corridor crosses a mapped exclusion: {a}, {b}')
            self.edges.append((a, b, line))
            self.connect(a, b, line.length * self.scale)

        self.corridors_gdf = gpd.GeoDataFrame(
            [{'start': a, 'end': b, 'floor': self.nodes[a]['floor'], 'geometry': line}
             for a, b, line in self.edges],
            geometry='geometry',
            crs=None
        )
        self.corridors_gdf['length_approx_m'] = self.corridors_gdf.length * self.scale

        # Multi-floor vertical connectors (lifts, escalators)
        for c in self.data['connectors']:
            if not math.isfinite(c['meters']) or c['meters'] <= 0:
                raise ValueError('Invalid connector weight')
            self.connect(c['a'], c['b'], c['meters'])
            kind = c.get('kind', 'escalator')
            if kind not in ('lift', 'escalator'):
                raise ValueError('Unknown connector kind')
            self.connector_kinds[c['a'], c['b']] = kind
            self.connector_kinds[c['b'], c['a']] = kind

        raw = json.loads((root / 'extracted-maps/map-data.json').read_text(encoding='utf-8'))
        self.places = load_places(raw)
        for p in self.places:
            p.entrance = self.data['entrances'].get(p.id)
        for p in self.data['facilities']:
            self.places.append(Place(**p))
        for p in self.places:
            if p.entrance and (p.entrance not in self.nodes or self.nodes[p.entrance]['floor'] != p.floor):
                raise ValueError(f'Invalid entrance for {p.id}')

        self.rebuild_places_layer()

    def rebuild_places_layer(self) -> None:
        """Refresh the spatial GeoDataFrame using entrance points for buffer and proximity queries."""
        self.by_id = {p.id: p for p in self.places}

        def get_spatial_point(p: Place) -> Point:
            if p.entrance and p.entrance in self.nodes:
                return Point(self.nodes[p.entrance]['xy'])
            return Point(p.xy)

        self.places_gdf = gpd.GeoDataFrame(
            [{'id': p.id, 'title': p.title, 'floor': p.floor, 'unit': p.unit,
              'category': p.category, 'entrance': p.entrance,
              'geometry': get_spatial_point(p)}
             for p in self.places],
            columns=['id', 'title', 'floor', 'unit', 'category', 'entrance', 'geometry'],
            geometry='geometry',
            crs=None
        ).set_index('id')

    def connect(self, a: str, b: str, cost: float) -> None:
        """Add bidirectional weighted edge in graph."""
        self.graph[a].append((b, cost))
        self.graph[b].append((a, cost))

    def route(self, start: str, end: str, transport: str = 'any') -> tuple[list[str], float]:
        """Compute shortest path between nodes using Dijkstra's algorithm."""
        if transport not in ('any', 'lift', 'escalator'):
            raise ValueError('Unknown transport preference')
        if start not in self.graph or end not in self.graph:
            return [], math.inf

        queue, distances, previous = [(0, start)], {start: 0}, {}
        while queue:
            cost, node = heappop(queue)
            if cost != distances[node]:
                continue
            if node == end:
                path = [end]
                while path[-1] != start:
                    path.append(previous[path[-1]])
                return path[::-1], cost
            for other, weight in self.graph[node]:
                kind = self.connector_kinds.get((node, other))
                if kind and transport != 'any' and kind != transport:
                    continue
                candidate = cost + weight
                if candidate < distances.get(other, math.inf):
                    distances[other] = candidate
                    previous[other] = node
                    heappush(queue, (candidate, other))
        return [], math.inf

    def nearby(self, xy: tuple, floor: str, category: str, radius: float) -> tuple[list, float]:
        """Perform buffer analysis to find facilities within metric distance."""
        if not math.isfinite(radius) or radius <= 0:
            raise ValueError('Radius must be finite and positive')

        radii = [20, 40, 60] if radius == 20 else [radius]
        center = Point(xy)
        places = self.places_gdf[self.places_gdf.floor == floor]
        if category != 'All':
            places = places[places.category == category]

        distances = places.distance(center) * self.scale
        for actual in radii:
            buffer = center.buffer(actual / self.scale, quad_segs=64)
            inside = places.intersects(buffer) | (distances <= actual + 1e-9)
            matches = [(float(distances.loc[key]), self.by_id[key]) for key in places.index[inside]]
            if matches:
                matches.sort(key=lambda row: (row[0], row[1].title))
                return (matches[:1] if category == 'Exit' else matches), actual
        return [], radii[-1]


class Player:
    """Represents the simulated player walking through the corridor network."""
    connection_radius = 3.0
    turn_radius = 2.0

    def __init__(self, model: Model):
        self.model = model
        self.node = model.data['start']
        self.target = None
        self.progress = 0.0
        self.transport = 'any'

    @property
    def floor(self) -> str:
        return self.model.nodes[self.node]['floor']

    @property
    def xy(self) -> tuple[float, float]:
        a = self.model.nodes[self.node]['xy']
        if self.target is None:
            return tuple(a)
        b = self.model.nodes[self.target]['xy']
        return tuple(a[i] + (b[i] - a[i]) * self.progress for i in range(2))

    def move(self, dx: float, dy: float, seconds: float, speed: float = 3.0) -> None:
        """Move the player along graph edges based on input velocity vector."""
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError('Movement speed must be finite and positive')
        norm = math.hypot(dx, dy)
        if not norm or seconds <= 0:
            return

        dx, dy = dx / norm, dy / norm
        remaining = min(seconds, 0.1) * speed / self.model.scale

        while remaining > 1e-8:
            if self.target is None:
                a = self.xy
                options = []
                for other, _ in self.model.graph[self.node]:
                    if self.model.nodes[other]['floor'] != self.floor:
                        continue
                    b = self.model.nodes[other]['xy']
                    length = math.dist(a, b)
                    alignment = ((b[0] - a[0]) * dx + (b[1] - a[1]) * dy) / length
                    options.append((alignment, other))
                if not options or max(options)[0] < 0.35:
                    break
                self.target = max(options)[1]
                self.progress = 0

            a, b = self.model.nodes[self.node]['xy'], self.model.nodes[self.target]['xy']
            length = math.dist(a, b)
            alignment = ((b[0] - a[0]) * dx + (b[1] - a[1]) * dy) / length

            turns = []
            for junction, distance, forward_to_junction in (
                (self.node, self.progress * length, False),
                (self.target, (1 - self.progress) * length, True)
            ):
                if alignment >= 0.35 or distance * self.model.scale > self.turn_radius:
                    continue
                origin = self.model.nodes[junction]['xy']
                for branch, _ in self.model.graph[junction]:
                    if branch in (self.node, self.target) or self.model.nodes[branch]['floor'] != self.floor:
                        continue
                    end = self.model.nodes[branch]['xy']
                    heading = ((end[0] - origin[0]) * dx + (end[1] - origin[1]) * dy) / math.dist(origin, end)
                    if heading > max(0.35, abs(alignment) + 0.15):
                        turns.append((heading, -distance, junction, branch, forward_to_junction))

            if turns:
                _, negative_distance, junction, branch, forward_to_junction = max(turns)
                distance = -negative_distance
                amount = min(remaining, distance)
                self.progress += amount / length * (1 if forward_to_junction else -1)
                remaining -= amount
                if amount >= distance - 1e-8:
                    self.node, self.target, self.progress = junction, branch, 0
                    continue
                break

            if abs(alignment) < 0.2:
                break

            forward = alignment > 0
            available = (1 - self.progress if forward else self.progress) * length
            amount = min(remaining, available)
            self.progress += amount / length * (1 if forward else -1)
            remaining -= amount
            if amount >= available - 1e-8:
                if forward:
                    self.node = self.target
                self.target, self.progress = None, 0
            else:
                break

    def route(self, end: str) -> tuple[list[str], float]:
        """Compute shortest route from current interpolated player position to destination."""
        path, cost = self.model.route(self.node, end, self.transport)
        if self.target is None:
            return path, cost
        length = math.dist(self.model.nodes[self.node]['xy'], self.model.nodes[self.target]['xy']) * self.model.scale
        path2, cost2 = self.model.route(self.target, end, self.transport)
        return min(
            [(path, cost + self.progress * length),
             (path2, cost2 + (1 - self.progress) * length)],
            key=lambda x: x[1]
        )

    def nearest_place(self, category: str) -> tuple[Place | None, float]:
        """Choose the reachable destination with the shortest Dijkstra route."""
        if category not in CATEGORIES:
            raise ValueError('Unknown facility category')
        candidates = []
        for place in self.model.places:
            if not place.entrance or (category != 'All' and place.category != category):
                continue
            path, distance = self.route(place.entrance)
            if path and math.isfinite(distance):
                candidates.append((distance, place.title, place.id, place))
        if not candidates:
            return None, math.inf
        distance, _, _, place = min(candidates)
        return place, distance

    def connector(self) -> dict | None:
        """Find the nearest vertical connector if player is within threshold radius."""
        distances = {self.node: 0.0}
        if self.target is not None:
            length = math.dist(self.model.nodes[self.node]['xy'], self.model.nodes[self.target]['xy']) * self.model.scale
            distances = {self.node: self.progress * length, self.target: (1 - self.progress) * length}

        queue = []
        for node, distance in distances.items():
            heappush(queue, (distance, node))

        while queue:
            distance, node = heappop(queue)
            if distance > self.connection_radius + 1e-8:
                break
            if distance != distances[node]:
                continue
            for connector in self.model.data['connectors']:
                if node in (connector['a'], connector['b']):
                    return connector
            for other, weight in self.model.graph[node]:
                if self.model.nodes[other]['floor'] != self.floor:
                    continue
                candidate = distance + weight
                if candidate <= self.connection_radius + 1e-8 and candidate < distances.get(other, math.inf):
                    distances[other] = candidate
                    heappush(queue, (candidate, other))
        return None

    def transition(self) -> bool:
        """Change floor if a connector is reachable."""
        connector = self.connector()
        if connector:
            self.node = connector['b'] if self.model.nodes[connector['a']]['floor'] == self.floor else connector['a']
            self.target, self.progress = None, 0
            return True
        return False
