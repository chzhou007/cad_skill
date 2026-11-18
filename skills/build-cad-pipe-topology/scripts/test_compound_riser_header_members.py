import copy,unittest
from compound_riser_header_members import split_and_allocate

def fixture(reverse=False):
    def edge(eid,a,b,p):return dict(edge_id=eid,start_node_id=a,end_node_id=b,attribute_paths=p)
    h=edge('H','G','OLD',[[[0,0],[100,0]]]);s=edge('S','OLD','R',[[[100,0],[100,20]]]);d=edge('D','OLD','DEST',[[[100,0],[200,0]],[[201,0],[201,10]]])
    rows=[dict(device_name=n,equipment_type=t,edge_id=e)for n,t,e in [('a','ball_valve','H'),('b','ball_valve','H'),('c','balancing_valve','H'),('d','ball_valve','H'),('e','ball_valve','D')]];centers={n:[x,0]for n,x in [('a',20),('b',60),('c',70),('d',80)]}
    profiles=dict(approach={'ball_valve':1},riser={'ball_valve':2,'balancing_valve':1},departure={'ball_valve':1})
    if reverse:
        for e in(h,s,d):e['start_node_id'],e['end_node_id']=e['end_node_id'],e['start_node_id'];e['attribute_paths']=[list(reversed(p))for p in reversed(e['attribute_paths'])]
    return h,s,d,rows,centers,profiles
class Tests(unittest.TestCase):
    def test_reanchor_rebuilds_all_three_edges_without_duplicating_valves(self):
        for rev in(False,True):
            h,s,d,c,pos,p=fixture(rev);before=copy.deepcopy((h,s,d,c));r=split_and_allocate(h,s,d,'OLD',[40,0],c,pos,p)
            self.assertEqual(r['paths']['approach'],[[[0,0],[40,0]]]);self.assertEqual(r['paths']['riser'],[[[40,0],[100,0]],[[100,0],[100,20]]]);self.assertEqual(r['paths']['departure'][0],[[40,0],[100,0]])
            self.assertEqual({x['device_name']for x in r['components']['riser']},{'b','c','d'});self.assertEqual(r['component_ids_conserved'],['a','b','c','d','e']);self.assertEqual((h,s,d,c),before)
    def test_existing_omitted_gap_is_preserved(self):
        h,s,d,c,pos,p=fixture();r=split_and_allocate(h,s,d,'OLD',[40,0],c,pos,p);self.assertEqual(r['paths']['departure'][1:],d['attribute_paths']);self.assertNotEqual(r['paths']['departure'][-2][-1],r['paths']['departure'][-1][0])
    def test_nonunique_component_identity_allocation_is_not_resolved_by_order(self):
        h,s,d,c,pos,p=fixture();c=[r for r in c if r['edge_id']!='D'];p['riser']['ball_valve']=1
        with self.assertRaisesRegex(ValueError,'not unique'):split_and_allocate(h,s,d,'OLD',[40,0],c,pos,p)
    def test_wrong_circle_position_or_component_population_fails(self):
        for kind in('off_line','end','missing','unanchored','duplicate'):
            h,s,d,c,pos,p=fixture();point=[40,0]
            if kind=='off_line':point=[40,2]
            elif kind=='end':point=[100,0]
            elif kind=='missing':c.pop(2)
            elif kind=='unanchored':pos.pop('b')
            else:c.append(dict(c[0]))
            with self.subTest(kind=kind),self.assertRaises(ValueError):split_and_allocate(h,s,d,'OLD',point,c,pos,p)
if __name__=='__main__':unittest.main()
