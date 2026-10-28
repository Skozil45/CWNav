import math
import unittest

from navigation import Model, Place, Player, directory_position, load_places


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.m = Model()

    def test_dijkstra_prefers_shorter_path(self):
        self.m.graph = {'a':[('b',10),('c',2)],'c':[('b',3)],'b':[],'z':[]}
        self.assertEqual(self.m.route('a','b'),(['a','c','b'],5))
        self.assertEqual(self.m.route('a','z'),([],math.inf))
        self.assertEqual(self.m.route('bad','b'),([],math.inf))

    def test_cross_floor_uses_connector_cost(self):
        path,cost = self.m.route('g-escalator','f-escalator')
        self.assertEqual(path,['g-escalator','f-escalator'])
        self.assertEqual(cost,12)
        path,cost = self.m.route('g0','f-lacoste')
        self.assertIn('g-escalator',path)
        self.assertIn('f-escalator',path)
        self.assertGreater(cost,12)

    def test_buffer_boundary_and_filter(self):
        self.m.places = [Place('a','A','ground','','Toilets',(20,0)),
                         Place('b','B','first','','Toilets',(0,0)),
                         Place('c','C','ground','','Dining',(0,0)),
                         Place('d','D','ground','','Toilets',(20.001,0)),
                         Place('e','E','ground','','Toilets',(20/math.sqrt(2),20/math.sqrt(2)))]
        rows,radius = self.m.nearby((0,0),'ground','Toilets',20)
        self.assertEqual({p.id for _,p in rows},{'a','e'})
        self.assertEqual(radius,20)

    def test_expansion_and_empty(self):
        self.m.places = [Place('a','A','ground','','Toilets',(45,0))]
        self.assertEqual(self.m.nearby((0,0),'ground','Toilets',20)[1],60)
        self.assertEqual(self.m.nearby((0,0),'ground','Toilets',30),([],30))
        self.assertEqual(self.m.nearby((0,0),'first','Toilets',20),([],60))
        with self.assertRaises(ValueError):
            self.m.nearby((0,0),'ground','All',float('nan'))

    def test_sorting_and_scale(self):
        self.m.scale = 2
        self.m.places = [Place('a','A','ground','','Dining',(8,0)),Place('b','B','ground','','Dining',(4,0))]
        rows,_ = self.m.nearby((0,0),'ground','Dining',20)
        self.assertEqual([(d,p.id) for d,p in rows],[(8,'b'),(16,'a')])

    def test_display_coordinate_conversion(self):
        self.assertEqual(directory_position((.08,0)),(0,0))
        self.assertEqual(directory_position((.92,1)),(420,300))
        self.assertEqual(directory_position((.5,.5)),(210,150))

    def test_array_layers_and_plain_descriptions(self):
        places=load_places({'locations':[{'id':'x','title':'X','layer':['ground','first','other'],
            'coord':[.5,.5],'desc':'<b>Unit 3-6</b><p>Text</p>','group':['group2']}]})
        self.assertEqual(len(places),2)
        self.assertEqual(places[0].unit,'3-6')
        self.assertEqual(places[0].category,'Dining')
        self.assertNotIn('<',places[0].description)

    def test_actual_directory_coverage(self):
        tenants=[p for p in self.m.places if p.category in ('Dining','Stores')]
        self.assertEqual(len(tenants),72)
        self.assertEqual(len({p.id for p in self.m.places}),len(self.m.places))
        self.assertTrue(all(p.floor in ('ground','first') for p in self.m.places))

    def test_movement_stays_on_edge_and_frame_rate(self):
        self.m.nodes={'g0':{'floor':'ground','xy':[239,164]},'north':{'floor':'ground','xy':[239,154]}}
        self.m.graph={'g0':[('north',10)],'north':[('g0',10)]}
        a,b=Player(self.m),Player(self.m)
        for _ in range(100): a.move(0,-1,.01)
        for _ in range(10): b.move(0,-1,.1)
        self.assertAlmostEqual(math.dist(a.xy,b.xy),0,places=8)
        self.assertAlmostEqual(math.dist(a.xy,(239,164)),3,places=8)
        self.assertEqual(a.target,'north')
        for _ in range(10): a.move(0,1,.1)
        self.assertEqual(a.target,None)
        self.assertEqual(a.node,'g0')

    def test_transition_requires_nearby_connector(self):
        p=Player(self.m)
        self.assertFalse(p.transition())
        p.node='g-escalator'
        self.assertTrue(p.transition())
        self.assertEqual(p.floor,'first')

    def test_adjustable_speed(self):
        self.m.nodes={'g0':{'floor':'ground','xy':[0,0]},'north':{'floor':'ground','xy':[0,-10]}}
        self.m.graph={'g0':[('north',10)],'north':[('g0',10)]}
        for speed in (.5, 3, 12):
            p=Player(self.m)
            p.move(0,-1,.1,speed)
            self.assertAlmostEqual(math.dist(p.xy,(0,0)),speed*.1/self.m.scale)
            p.move(0,-1,.1,.5)
            self.assertAlmostEqual(math.dist(p.xy,(0,0)),(speed+.5)*.1/self.m.scale)
        for speed in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                Player(self.m).move(0,-1,.1,speed)

    def test_all_supported_destinations_reachable_with_both_modes(self):
        for p in self.m.places:
            if not p.entrance:
                self.assertIn(p.id,self.m.data['unsupported'])
                continue
            for mode in ('any','lift','escalator'):
                path,cost=self.m.route(self.m.data['start'],p.entrance,mode)
                self.assertTrue(path,(p.id,mode))
                self.assertTrue(math.isfinite(cost))
                kinds=[self.m.connector_kinds.get((a,b)) for a,b in zip(path,path[1:])]
                if mode!='any':
                    self.assertTrue(all(kind in (None,mode) for kind in kinds),(p.id,mode))

    def test_every_lift_and_escalator_transitions_both_ways(self):
        self.assertEqual(sum(c['kind']=='lift' for c in self.m.data['connectors']),4)
        self.assertEqual(sum(c['kind']=='escalator' for c in self.m.data['connectors']),3)
        for c in self.m.data['connectors']:
            p=Player(self.m)
            p.node=c['a']
            self.assertTrue(p.transition())
            self.assertEqual(p.node,c['b'])
            self.assertTrue(p.transition())
            self.assertEqual(p.node,c['a'])

    def test_routes_stay_inside_reviewed_corridor_masks(self):
        from PySide6.QtGui import QImage
        from navigation import ROOT
        masks={floor:QImage(str(ROOT/'verification'/f'{floor}-corridor-mask.png')) for floor in ('ground','first')}
        for a,b,line in self.m.edges:
            mask=masks[self.m.nodes[a]['floor']]
            self.assertFalse(mask.isNull())
            steps=max(1,math.ceil(line.length*8))
            start,end=self.m.nodes[a]['xy'],self.m.nodes[b]['xy']
            for i in range(steps+1):
                x=round((start[0]+(end[0]-start[0])*i/steps)*2)
                y=round((start[1]+(end[1]-start[1])*i/steps)*2)
                self.assertGreater(mask.pixelColor(x,y).red(),0,(a,b,x,y))

    def test_lift_preference_routes_around_escalator(self):
        path,_=self.m.route('g-escalator','f-escalator','lift')
        transitions=[self.m.connector_kinds.get((a,b)) for a,b in zip(path,path[1:])]
        self.assertIn('lift',transitions)
        self.assertNotIn('escalator',transitions)

    def test_route_from_inside_edge(self):
        p=Player(self.m)
        p.move(0,-1,.1)
        path,distance=p.route('g0')
        self.assertEqual(path,['g0'])
        self.assertAlmostEqual(distance,.3)

    def test_all_edges_avoid_mapped_exclusions(self):
        for a,b,line in self.m.edges:
            for floor,polygon in self.m.exclusions:
                if self.m.nodes[a]['floor']==floor:
                    self.assertFalse(line.intersects(polygon),(a,b))

    def test_route_updates_after_deviation(self):
        self.m.nodes={'g0':{'floor':'ground','xy':[0,0]},'north':{'floor':'ground','xy':[0,-10]},
                      'g-fore':{'floor':'ground','xy':[10,0]}}
        self.m.graph={'g0':[('north',10),('g-fore',10)],'north':[('g0',10)],'g-fore':[('g0',10)]}
        p=Player(self.m)
        original,distance=p.route('g-fore')
        p.move(0,-1,.1)
        changed,new_distance=p.route('g-fore')
        self.assertGreater(new_distance,distance)
        self.assertEqual(changed[0],'g0')

    def test_destinations_reuse_fixed_gis_rails(self):
        import copy
        from shapely.geometry import LineString
        from shapely.ops import unary_union
        before=copy.deepcopy(self.m.graph)
        first,_=self.m.route('g0','g-fore')
        second,_=self.m.route('g0','f-lacoste')
        edge_set=lambda path:{frozenset(pair) for pair in zip(path,path[1:])}
        self.assertTrue(edge_set(first)&edge_set(second))
        self.assertEqual(self.m.graph,before)
        self.assertEqual(self.m.data['network_type'],'shared_corridor_rails')
        for floor in ('ground','first'):
            lines=[line for a,b,line in self.m.edges if self.m.nodes[a]['floor']==floor]
            self.assertTrue(all(isinstance(line,LineString) for line in lines))
            self.assertAlmostEqual(sum(line.length for line in lines),unary_union(lines).length,places=5)

    def test_walk_entire_cross_floor_route(self):
        p=Player(self.m)
        path,_=p.route('f-lacoste')
        for next_node in path[1:]:
            if self.m.nodes[next_node]['floor']!=p.floor:
                self.assertTrue(p.transition())
            else:
                for _ in range(10000):
                    x,y=self.m.nodes[next_node]['xy']
                    dx,dy=x-p.xy[0],y-p.xy[1]
                    p.move(dx,dy,min(.1,math.hypot(dx,dy)*self.m.scale/3))
                    if p.node==next_node and p.target is None:
                        break
                else:
                    self.fail('Could not walk to '+next_node)
            self.assertEqual(p.node,next_node)
        self.assertEqual(p.floor,'first')
        self.assertEqual(p.route('f-lacoste'),(['f-lacoste'],0))


if __name__ == '__main__':
    unittest.main()
