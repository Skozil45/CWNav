"""Local-coordinate GIS and corridor routing, independent of the desktop UI."""
from dataclasses import dataclass
from heapq import heappop, heappush
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re

from shapely.geometry import LineString, Point, Polygon

ROOT = Path(__file__).resolve().parent
FLOORS = {'ground': 'Ground Floor', 'first': '1st Floor'}


class PlainText(HTMLParser):
    def __init__(self, value):
        super().__init__()
        self.parts = []
        self.feed(value)

    def handle_data(self, data):
        self.parts.append(data)


def directory_position(coord):
    # The 420x300 SVG is centered in the source site's 1000x600 viewport.
    return ((float(coord[0]) * 1000 - 80) / 2, float(coord[1]) * 300)


@dataclass
class Place:
    id: str
    title: str
    floor: str
    unit: str
    category: str
    xy: tuple
    description: str = ''
    entrance: str | None = None


def load_places(data):
    places = []
    for row in data['locations']:
        floors = row.get('layer', [])
        floors = [floors] if isinstance(floors, str) else floors
        for floor in floors:
            if floor not in FLOORS:
                continue
            text = ' '.join(PlainText(row.get('desc', '')).parts)
            match = re.search(r'Unit\s+([A-Za-z0-9]+(?:\s*[-,]\s*[A-Za-z0-9]+)*)', text)
            category = 'Dining' if 'group2' in row.get('group', []) else 'Stores'
            if 'ATM' in row['title'].upper():
                category = 'ATMs'
            xy = directory_position(row['coord'])
            if not all(math.isfinite(v) for v in xy):
                raise ValueError(f"Invalid coordinates: {row['id']}")
            places.append(Place(f"{floor}:{row['id']}", row['title'], floor,
                                match[1] if match else '', category, xy, text))
    return places


class Model:
    def __init__(self, root=ROOT):
        self.data = json.loads((root / 'navigation-data.json').read_text(encoding='utf-8'))
        self.scale = float(self.data['meters_per_unit'])
        if not math.isfinite(self.scale) or self.scale <= 0:
            raise ValueError('meters_per_unit must be finite and positive')
        self.nodes = self.data['nodes']
        for key, node in self.nodes.items():
            if node['floor'] not in FLOORS or len(node['xy']) != 2 or not all(math.isfinite(v) for v in node['xy']):
                raise ValueError(f'Invalid node: {key}')
        self.exclusions = [(row['floor'], Polygon(row['ring'])) for row in self.data['excluded_areas']]
        if any(not polygon.is_valid for _, polygon in self.exclusions):
            raise ValueError('Invalid exclusion polygon')
        self.graph = {key: [] for key in self.nodes}
        self.edges = []
        self.connector_kinds = {}
        for a, b in self.data['edges']:
            if self.nodes[a]['floor'] != self.nodes[b]['floor']:
                raise ValueError('Cross-floor edges must be explicit connectors')
            line = LineString([self.nodes[a]['xy'], self.nodes[b]['xy']])
            if line.length <= 0:
                raise ValueError('Zero-length edge')
            if any(floor == self.nodes[a]['floor'] and line.intersects(polygon) for floor, polygon in self.exclusions):
                raise ValueError(f'Corridor crosses a mapped exclusion: {a}, {b}')
            self.edges.append((a, b, line))
            self.connect(a, b, line.length * self.scale)
        for c in self.data['connectors']:
            if not math.isfinite(c['meters']) or c['meters'] <= 0:
                raise ValueError('Invalid connector weight')
            self.connect(c['a'], c['b'], c['meters'])
            kind = c.get('kind','escalator')
            if kind not in ('lift','escalator'):
                raise ValueError('Unknown connector kind')
            self.connector_kinds[c['a'],c['b']] = kind
            self.connector_kinds[c['b'],c['a']] = kind
        raw = json.loads((root / 'extracted-maps/map-data.json').read_text(encoding='utf-8'))
        self.places = load_places(raw)
        for p in self.places:
            p.entrance = self.data['entrances'].get(p.id)
        for p in self.data['facilities']:
            self.places.append(Place(**p))
        for p in self.places:
            if p.entrance and (p.entrance not in self.nodes or self.nodes[p.entrance]['floor'] != p.floor):
                raise ValueError(f'Invalid entrance for {p.id}')
        self.by_id = {p.id: p for p in self.places}

    def connect(self, a, b, cost):
        self.graph[a].append((b, cost))
        self.graph[b].append((a, cost))

    def route(self, start, end, transport='any'):
        if transport not in ('any','lift','escalator'):
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
                kind = self.connector_kinds.get((node,other))
                if kind and transport != 'any' and kind != transport:
                    continue
                candidate = cost + weight
                if candidate < distances.get(other, math.inf):
                    distances[other] = candidate
                    previous[other] = node
                    heappush(queue, (candidate, other))
        return [], math.inf

    def nearby(self, xy, floor, category, radius):
        if not math.isfinite(radius) or radius <= 0:
            raise ValueError('Radius must be finite and positive')
        radii = [20, 40, 60] if radius == 20 else [radius]
        center = Point(xy)
        for actual in radii:
            buffer = center.buffer(actual / self.scale, quad_segs=64)
            matches = []
            for p in self.places:
                if p.floor != floor or (category != 'All' and p.category != category):
                    continue
                distance = center.distance(Point(p.xy)) * self.scale
                # Polygon approximation must not exclude a true circular boundary point.
                if buffer.intersects(Point(p.xy)) or distance <= actual + 1e-9:
                    matches.append((distance, p))
            if matches:
                return sorted(matches, key=lambda row: (row[0], row[1].title)), actual
        return [], radii[-1]


class Player:
    def __init__(self, model):
        self.model = model
        self.node = model.data['start']
        self.target = None
        self.progress = 0.0
        self.transport = 'any'

    @property
    def floor(self):
        return self.model.nodes[self.node]['floor']

    @property
    def xy(self):
        a = self.model.nodes[self.node]['xy']
        if self.target is None:
            return tuple(a)
        b = self.model.nodes[self.target]['xy']
        return tuple(a[i] + (b[i] - a[i]) * self.progress for i in range(2))

    def move(self, dx, dy, seconds, speed=3):
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError('Movement speed must be finite and positive')
        norm = math.hypot(dx, dy)
        if not norm or seconds <= 0:
            return
        dx, dy = dx / norm, dy / norm
        remaining = min(seconds, .1) * speed / self.model.scale
        while remaining > 1e-8:
            if self.target is None:
                a = self.xy
                options = []
                for other, _ in self.model.graph[self.node]:
                    if self.model.nodes[other]['floor'] != self.floor:
                        continue
                    b = self.model.nodes[other]['xy']
                    length = math.dist(a, b)
                    alignment = ((b[0]-a[0])*dx + (b[1]-a[1])*dy) / length
                    options.append((alignment, other))
                if not options or max(options)[0] < .35:
                    break
                self.target = max(options)[1]
                self.progress = 0
            a, b = self.model.nodes[self.node]['xy'], self.model.nodes[self.target]['xy']
            length = math.dist(a, b)
            alignment = ((b[0]-a[0])*dx + (b[1]-a[1])*dy) / length
            if abs(alignment) < .2:
                break
            forward = alignment > 0
            available = (1-self.progress if forward else self.progress) * length
            amount = min(remaining, available)
            self.progress += amount / length * (1 if forward else -1)
            remaining -= amount
            if amount >= available - 1e-8:
                if forward:
                    self.node = self.target
                self.target, self.progress = None, 0
            else:
                break

    def route(self, end):
        path, cost = self.model.route(self.node, end, self.transport)
        if self.target is None:
            return path, cost
        length = math.dist(self.model.nodes[self.node]['xy'], self.model.nodes[self.target]['xy']) * self.model.scale
        path2, cost2 = self.model.route(self.target, end, self.transport)
        return min([(path, cost + self.progress * length),
                    (path2, cost2 + (1-self.progress) * length)], key=lambda x: x[1])

    def connector(self):
        nearby = {key for key in (self.node,self.target) if key is not None
                  and math.dist(self.xy,self.model.nodes[key]['xy'])*self.model.scale <= 1}
        return next((c for c in self.model.data['connectors'] if nearby.intersection((c['a'],c['b']))), None)

    def transition(self):
        connector = self.connector()
        if connector:
            self.node = connector['b'] if self.model.nodes[connector['a']]['floor'] == self.floor else connector['a']
            self.target, self.progress = None, 0
            return True
        return False
