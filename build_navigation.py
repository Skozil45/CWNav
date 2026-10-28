"""Offline mapping aid: corridor-constrained paths, reviewed approaches and exclusions.

Runtime needs only the generated JSON. Regeneration additionally needs Pillow,
NumPy, SciPy and scikit-image (requirements-mapping.txt).
"""
from collections import defaultdict, deque
from heapq import heappop, heappush
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_closing, distance_transform_edt, label
from skimage.morphology import skeletonize
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from shapely.affinity import scale, rotate

from navigation import ROOT, load_places

SCALE = 2


def ellipse(x, y, rx, ry, angle=0):
    shape = scale(Point(x,y).buffer(1, quad_segs=32), rx, ry)
    return list(rotate(shape,angle).exterior.coords)


EXCLUSIONS = {
    'ground': [
        ('Oval east atrium',ellipse(166,171.5,28,12)),
        ('Oval atrium',ellipse(299,200,12.5,29,-20)),
        ('Linear east atrium',[(135,105),(153,105),(161,103),(165,100),(165,94),(194,94),(204,97),(209,101),(209,105),(204,110),(198,111),(144,111),(138,109)]),
        ('Void atrium',[(217,100),(219,95),(223,94),(237,96),(252,100),(265,104),(267,109),(266,119),(253,116),(239,113),(222,111),(217,108)]),
        ('Linear atrium',[(297,121),(300,119),(315,125),(330,135),(345,146),(356,157),(361,166),(360,170),(356,173),(349,170),(337,160),(326,148),(315,139),(299,133),(296,130)])
    ],
    'first': [('Mini atrium',ellipse(128,116,16,9))]
}

# Approximate corridor-side access points; never route to an interior tenant marker.
APPROACHES = {
    'ground:loft':(85,141), 'ground:wilson':(155,158),
    'ground:sandro':(181,158), 'ground:molton-brown':(131,127),
    'ground:filosofia':(165,111.5), 'ground:pandora':(189,111.5),
    'ground:frank-and-co':(299,151), 'ground:boss':(340,173),
    'ground:starbucks':(211,176), 'ground:tumi':(244,167),
    'ground:coach':(268,168), 'ground:digimap':(198,179),
    'ground:hnm-gf':(119,170), 'ground:memo-paris':(162,92),
    'ground:tissot':(203,92), 'ground:frederique-constant':(127,92),
    'ground:kate-spade':(233,145), 'ground:bowie':(283,200),
    'ground:aigner':(310,231), 'ground:denza':(352,253),
    'ground:marketing-gallery-apartment':(244,65),
    'first:mycws-lounge':(378,157), 'first:amakute':(143,170),
    'first:mst_golf':(304,232), 'first:sociolla':(379,175),
    'first:tommy-hilfiger':(267,173), 'first:thule':(143,124),
    'first:the-body-shop':(270,165), 'first:steve-madden':(143,160),
    'first:staccato':(298,217), 'first:skechers':(353,110),
    'first:project-soul':(256,78), 'first:planet-sports':(359,101),
    'first:one-love-bespoke':(224,132), 'first:new-era':(123,123),
    'first:new-balance':(353,125), 'first:marks-and-spencer':(302,101),
    'first:maison-aura':(381,204), 'first:levis':(125,102),
    'first:laxmi-tailors':(184,103), 'first:loccitane':(270,139),
    'first:jd-sports':(220,176), 'first:hush-puppies':(324,198),
    'first:havaianas':(255,111), 'first:hnm-1f':(141,184),
    'first:giordano':(311,153), 'first:footlocker':(176,145),
    'first:flying-tiger':(237,173), 'first:everbest-studio':(317,175),
    'first:cuffed':(181,136), 'first:aldo':(292,204),
    'first:cnf':(378,221), 'first:calvin-klein':(252,173),
    'first:converse':(203,124), 'first:batik-keris':(382,193),
    'first:adidas':(160,102), 'first:bags-city':(128,158),
    'first:birkenstock':(111,142), 'first:asics':(196,188)
}


def corridor_mask(floor):
    filename = 'ground-floor' if floor=='ground' else '1st-floor'
    source = Image.open(ROOT/'extracted-maps'/f'{filename}.png').convert('RGB')
    source = source.resize((840,600),Image.Resampling.NEAREST)
    pixels = np.asarray(source).astype(int)
    mask = np.abs(pixels-np.array([244,240,233])).sum(axis=2) < 20
    # Close sub-unit lettering gaps, not multi-unit shop walls or atrium interiors.
    mask = binary_closing(mask, iterations=1)
    holes,count = label(~mask)
    sizes = np.bincount(holes.ravel())
    protected = np.zeros(count+1,dtype=bool)
    for color in ([124,126,112],[105,120,132],[216,207,197]):
        protected[np.unique(holes[np.abs(pixels-np.array(color)).sum(axis=2)<20])] = True
    fill = (sizes<100) & ~protected
    fill[0] = False
    mask |= fill[holes]
    exclusions = Image.new('1',(840,600))
    draw = ImageDraw.Draw(exclusions)
    for _,ring in EXCLUSIONS[floor]:
        draw.polygon([(round(x*SCALE),round(y*SCALE)) for x,y in ring],fill=1)
    mask &= ~np.array(exclusions,dtype=bool)
    components,_ = label(mask)
    seed = (round(164*SCALE),round(239*SCALE)) if floor=='ground' else (320,480)
    mask &= components==components[seed]
    assert mask[seed], 'Main corridor component not found'
    return mask


def nearest(mask, xy):
    ys,xs=np.nonzero(mask)
    distances=(xs/SCALE-xy[0])**2+(ys/SCALE-xy[1])**2
    index=distances.argmin()
    return (int(xs[index]),int(ys[index])), math.sqrt(distances[index])


def astar(mask, clearance, start, end):
    queue=[(0,0,start)]
    costs={start:0}
    previous={}
    while queue:
        _,cost,current=heappop(queue)
        if cost!=costs[current]:
            continue
        if current==end:
            path=[end]
            while path[-1]!=start:
                path.append(previous[path[-1]])
            return path[::-1]
        x,y=current
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            nx,ny=x+dx,y+dy
            if not (0<=nx<840 and 0<=ny<600 and mask[ny,nx]):
                continue
            if dx and dy and not (mask[y,nx] and mask[ny,x]):
                continue
            step=math.hypot(dx,dy)*(1+2/(1+clearance[ny,nx]))
            candidate=cost+step
            other=(nx,ny)
            if candidate<costs.get(other,math.inf):
                costs[other]=candidate
                previous[other]=current
                heappush(queue,(candidate+math.dist(other,end),candidate,other))
    raise ValueError(f'No corridor route: {start} to {end}')


def visible(mask,a,b):
    steps=max(abs(a[0]-b[0]),abs(a[1]-b[1]))*4+1
    for t in range(steps+1):
        x=a[0]+(b[0]-a[0])*t/steps
        y=a[1]+(b[1]-a[1])*t/steps
        if not all(mask[yy,xx] for xx in {math.floor(x),math.ceil(x)}
                   for yy in {math.floor(y),math.ceil(y)}):
            return False
    return True


def simplify(mask,path):
    result=[path[0]]
    i=0
    while i<len(path)-1:
        j=min(len(path)-1,i+40)
        while j>i+1 and (not visible(mask,path[i],path[j]) or
                         LineString([path[i],path[j]]).hausdorff_distance(LineString(path[i:j+1])) > 1.5):
            j-=1
        result.append(path[j])
        i=j
    return result


def rail_paths(mask,clearance,approaches):
    """One thinned corridor backbone, with branches joining it on first contact."""
    ys,xs=np.nonzero(skeletonize(mask))
    rail=set(zip(xs.tolist(),ys.tolist()))
    graph=defaultdict(set)
    def join(a,b):
        graph[a].add(b)
        graph[b].add(a)
    for x,y in sorted(rail):
        for dx,dy in ((1,0),(0,1),(1,1),(-1,1)):
            other=(x+dx,y+dy)
            if other not in rail:
                continue
            if dx and dy:
                corners=((x+dx,y),(x,y+dy))
                if any(c in rail for c in corners):
                    continue
                if not all(mask[cy,cx] for cx,cy in corners):
                    bridge=next((c for c in corners if mask[c[1],c[0]]),None)
                    if bridge is None:
                        continue
                    join((x,y),bridge)
                    join(bridge,other)
                    continue
            join((x,y),other)
    for point in sorted(set(approaches)):
        if point in graph:
            continue
        end=min(graph,key=lambda p:math.dist(point,p))
        path=astar(mask,clearance,point,end)
        stop=next(i for i,p in enumerate(path) if p in graph)
        for a,b in zip(path[:stop],path[1:stop+1]):
            join(a,b)
    protected=set(approaches)
    leaves=deque(p for p in graph if len(graph[p])==1 and p not in protected)
    while leaves:
        p=leaves.popleft()
        if p not in graph or len(graph[p])!=1 or p in protected:
            continue
        q=next(iter(graph[p]))
        graph[q].remove(p)
        del graph[p]
        if len(graph[q])==1 and q not in protected:
            leaves.append(q)
    # Keep shared rails used between stops; discard unused annotation/outdoor loops.
    used=set()
    for start in sorted(protected):
        queue=[(0,start)]
        costs={start:0}
        previous={}
        while queue:
            cost,p=heappop(queue)
            if cost!=costs[p]: continue
            for q in sorted(graph[p]):
                candidate=cost+math.dist(p,q)
                if candidate<costs.get(q,math.inf):
                    costs[q]=candidate
                    previous[q]=p
                    heappush(queue,(candidate,q))
        for end in protected-{start}:
            if end not in previous:
                raise ValueError(f'Disconnected rail stop: {end}')
            p=end
            while p!=start:
                q=previous[p]
                used.add(tuple(sorted((p,q))))
                p=q
    graph=defaultdict(set)
    for a,b in used:
        join(a,b)
    anchors={p for p in graph if len(graph[p])!=2 or p in protected}
    visited=set()
    paths=[]
    for start in sorted(anchors):
        for other in sorted(graph[start]):
            edge=tuple(sorted((start,other)))
            if edge in visited: continue
            path=[start,other]
            visited.add(edge)
            while path[-1] not in anchors:
                nxt=next(p for p in graph[path[-1]] if p!=path[-2])
                visited.add(tuple(sorted((path[-1],nxt))))
                path.append(nxt)
            paths.append(simplify(mask,path))
    return paths


def build():
    old=json.loads((ROOT/'navigation-data.json').read_text(encoding='utf-8'))
    places=load_places(json.loads((ROOT/'extracted-maps/map-data.json').read_text(encoding='utf-8')))
    facilities=old['facilities']
    extra=[('first:east-lift','East lobby lift','first','Lifts',[113,85]),
           ('ground:north-lift','North side lift','ground','Lifts',[387,147]),
           ('first:north-lift','North side lift','first','Lifts',[390,151]),
           ('ground:south-escalator','South escalator','ground','Escalators',[247,73]),
           ('first:south-escalator','South escalator','first','Escalators',[260,93]),
           ('ground:central-escalator','Central escalator','ground','Escalators',[180,177]),
           ('first:central-escalator','Central escalator','first','Escalators',[205,180])]
    existing={p['id'] for p in facilities}
    for key,title,floor,category,xy in extra:
        if key not in existing:
            facilities.append(dict(id=key,title=title+' (inferred)',floor=floor,category=category,xy=xy,unit=''))
    unsupported={
        'ground:redback':'MPH/exterior access is separated from the mall corridor in the supplied plan; a connecting walkway is not established.',
        'first:autoschoon':'MSCP parking access is outside the mapped indoor corridor. The service/parking entrance is not established.'}
    desired=defaultdict(dict)
    entrances={}
    for p in places:
        if p.id in unsupported:
            continue
        node=old['entrances'].get(p.id,p.id.replace(':','-')+'-approach')
        xy=APPROACHES.get(p.id,old['nodes'].get(node,{}).get('xy',p.xy))
        desired[p.floor][node]=xy
        entrances[p.id]=node
    for p in facilities:
        node=p.get('entrance') or p['id'].replace(':','-')+'-approach'
        p['entrance']=node
        desired[p['floor']][node]=p['xy']
    desired['ground']['g0']=[239,164]
    desired['first']['f0']=[240,160]
    nodes={}
    edges=set()
    audit=[]
    masks={}
    for floor in ('ground','first'):
        mask=corridor_mask(floor)
        masks[floor]=mask
        clearance=distance_transform_edt(mask)
        points={}
        for key,xy in desired[floor].items():
            pixel,distance=nearest(mask,xy)
            points[key]=pixel
            nodes[key]={'floor':floor,'xy':[pixel[0]/SCALE,pixel[1]/SCALE]}
            audit.append({'node':key,'requested_xy':xy,'corridor_xy':nodes[key]['xy'],'offset_map_units':round(distance,2)})
        by_pixel={}
        for key,pixel in points.items():
            if pixel in by_pixel:
                # Shared approaches refer to one node, avoiding zero-length edges.
                canonical=by_pixel[pixel]
                for pid,nid in list(entrances.items()):
                    if nid==key: entrances[pid]=canonical
                for p in facilities:
                    if p['entrance']==key: p['entrance']=canonical
                nodes.pop(key)
            else:
                by_pixel[pixel]=key
        keys=list(by_pixel.values())
        for path in rail_paths(mask,clearance,by_pixel):
            ids=[]
            for pixel in path:
                if pixel not in by_pixel:
                    key=f'{floor}-corridor-{pixel[0]}-{pixel[1]}'
                    by_pixel[pixel]=key
                    nodes[key]={'floor':floor,'xy':[pixel[0]/SCALE,pixel[1]/SCALE]}
                ids.append(by_pixel[pixel])
            edges.update(tuple(sorted(pair)) for pair in zip(ids,ids[1:]) if pair[0]!=pair[1])
        print(floor,'approaches',len(keys),'mapped',flush=True)
    # Split crossings/overlaps into actual junctions so walking cannot skip a turn.
    planar_edges=set()
    for floor in ('ground','first'):
        coordinates={tuple(round(v,6) for v in row['xy']):key for key,row in nodes.items() if row['floor']==floor}
        merged=unary_union([LineString([nodes[a]['xy'],nodes[b]['xy']]) for a,b in edges if nodes[a]['floor']==floor])
        for line in merged.geoms:
            ids=[]
            for xy in line.coords:
                xy=tuple(round(v,6) for v in xy)
                if xy not in coordinates:
                    key=f'{floor}-junction-{len(coordinates)}'
                    coordinates[xy]=key
                    nodes[key]={'floor':floor,'xy':list(xy)}
                ids.append(coordinates[xy])
            planar_edges.update(tuple(sorted(pair)) for pair in zip(ids,ids[1:]) if pair[0]!=pair[1])
    edges=planar_edges
    facility_by_id={p['id']:p for p in facilities}
    connectors=[]
    for kind,section in [('escalator','east'),('escalator','south'),('escalator','central'),
                         ('lift','south'),('lift','central'),('lift','east'),('lift','north')]:
        a=facility_by_id[f'ground:{section}-{kind}']['entrance']
        b=facility_by_id[f'first:{section}-{kind}']['entrance']
        connectors.append({'a':a,'b':b,'meters':12 if kind=='escalator' else 8,
            'name':f'{section.title()} {kind} (inferred pairing)','kind':kind,'verified':False})
    data={k:old[k] for k in ('meters_per_unit','scale_verified','scale_note')}
    data.update(network_type='shared_corridor_rails',mapping_note='Single shared corridor-centerline rail network from thinned walkable masks. Destination branches join existing rails on first contact; Dijkstra and player movement reuse these fixed LineStrings. Entrances, connector pairs, costs and directionality are inferred, not surveyed.',
        start='g0',nodes=nodes,edges=sorted(edges),connectors=connectors,entrances=entrances,
        facilities=facilities,unsupported=unsupported,
        excluded_areas=[{'floor':floor,'name':name,'ring':ring} for floor,areas in EXCLUSIONS.items() for name,ring in areas])
    (ROOT/'navigation-data.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    (ROOT/'verification/approach-audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    for floor,mask in masks.items():
        Image.fromarray((mask*255).astype('uint8')).save(ROOT/f'verification/{floor}-corridor-mask.png')
    print(len(nodes),'nodes',len(edges),'edges',len(entrances),'tenant approaches',flush=True)


if __name__=='__main__':
    build()
