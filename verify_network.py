"""Exhaustive connectivity and destination-pair routing audit of the mapped network."""
import json
import math
from navigation import ROOT, Model, Player


def main():
    model = Model()
    destinations = [p for p in model.places if p.entrance]
    report = {'nodes': len(model.nodes), 'corridor_edges': len(model.edges),
              'destinations': len(destinations), 'unsupported': model.data['unsupported'], 'modes': {}}
    for mode in ('any', 'lift', 'escalator'):
        visited, pending = set(), [model.data['start']]
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            pending.extend(other for other, _ in model.graph[node]
                           if mode == 'any' or model.connector_kinds.get((node, other)) in (None, mode))
        assert visited == set(model.nodes), (mode, set(model.nodes)-visited)
        count = 0
        for origin in destinations:
            for destination in destinations:
                path, cost = model.route(origin.entrance, destination.entrance, mode)
                assert path and math.isfinite(cost), (origin.id, destination.id, mode)
                assert path[0] == origin.entrance and path[-1] == destination.entrance
                assert all(any(n == b for n, _ in model.graph[a]) for a,b in zip(path,path[1:]))
                assert all(mode == 'any' or model.connector_kinds.get((a,b)) in (None,mode) for a,b in zip(path,path[1:]))
                count += 1
        report['modes'][mode] = {'reachable_nodes': len(visited), 'destination_pairs_passed': count}
    traversals = 0
    for a, b, line in model.edges:
        for start, end in ((a,b), (b,a)):
            p = Player(model)
            p.node, p.target, p.progress = start, end, 0
            x,y = model.nodes[start]['xy']
            xx,yy = model.nodes[end]['xy']
            p.move(xx-x, yy-y, .1, line.length*model.scale*5)
            assert math.dist(p.xy, ((x+xx)/2, (y+yy)/2)) < 1e-7, (start,end)
            traversals += 1
    report['directed_corridor_traversals_passed'] = traversals
    (ROOT/'verification/network-connectivity.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
