"""Offline source-topology/opacity audit, not source-engine mesh evaluation.

Reproduces only frame selection, motion-reference guards and opacity products
used by the fixed native compiler. No geometry/mesh, mask or raster visibility
is inferred. Complete post-update source-engine parameters are external input.
"""
from pathlib import Path
import bisect
import collections
import csv
import hashlib
import json
import math

BASE=Path(__file__).resolve().parent.parent
SOURCE=BASE/'inputs/ems/yuk_0.ems.json'
PARAMS=BASE/'native_integration/rebuilt-combo-complete-parameters.json'
data=json.loads(SOURCE.read_text(encoding='utf8'))
parameters=json.loads(PARAMS.read_text(encoding='utf8'))
resx=json.loads((BASE/'inputs/ems/yuk_0.ems.resx.json').read_text(encoding='utf8'))
parts={}
raw_owners={}
def collect(layers,path):
    for i,item in enumerate(layers):
        p=path+'/'+str(i)
        if 'meshCombinator' in item:raw_owners[p]=item
        collect(item.get('children',[]),p+'/children')
for group in sorted(data['object']):
    for name in sorted(data['object'][group]['motion']):
        motion=data['object'][group]['motion'][name]
        path='/object/'+group+'/motion/'+name
        parts[group+'/'+name]=(motion,path)
        collect(motion['layer'],path+'/layer')
order={key:i for i,key in enumerate(parts)}

def sample(item,part,values):
    binding=item.get('parameterize')
    if binding is None:binding=part.get('parameterize')
    controls=item.get('parameter') or part.get('parameter') or []
    control=controls[binding] if binding is not None else None
    time=0.
    if control and control.get('enabled',True):
        value=values.get(control['id'],0)
        if control.get('discretization',0)==1:value=math.trunc(value)
        begin,end=control['rangeBegin'],control['rangeEnd']
        if end>begin:time=(max(begin,min(end,value))-begin)*control['division']/(end-begin)
    frames=item.get('frameList',[])
    index=bisect.bisect_right([f['time'] for f in frames],time)-1
    if index<0:return dict(active=False,time=time,binding=control,resource=None,opacity=0,bp=False)
    left=frames[index];content=left.get('content')
    if left['type']==0 or not isinstance(content,dict):
        return dict(active=False,time=time,binding=control,resource=None,opacity=0,bp=False,frame_index=index)
    opacity=content.get('opa',255)/255.
    bp=content.get('mesh',{}).get('bp') is not None
    if left['type']==3 and index+1<len(frames):
        right=frames[index+1];r=right.get('content')
        if right['type']!=0 and isinstance(r,dict) and right['time']>left['time']:
            t=(time-left['time'])/(right['time']-left['time'])
            opacity=opacity*(1-t)+(r.get('opa',255)/255.)*t
            bp |= t>0 and r.get('mesh',{}).get('bp') is not None
    src,icon=content.get('src'),content.get('icon')
    return dict(active=True,time=time,binding=control,
                resource=src+'/'+icon if src is not None and icon is not None else None,
                opacity=opacity,bp=bp,frame_index=index,source_content=content)

nodes=[dict(id=0,parent=0,path='',active=True,cumulative_opacity=1.,resource=None,
            layer={},sample={},scope=0)]
scope_counter=0
def motion(key,parent,path,guard,stack):
    global scope_counter
    if key in stack:raise ValueError('cyclic motion reference')
    scope_counter+=1;scope=scope_counter
    part,raw=parts[key]
    for i,item in enumerate(part['layer']):
        layer(item,part,parent,path,raw+'/layer/'+str(i),guard,scope,stack+[key])

def layer(item,part,parent,path,raw,guard,scope,stack):
    state=sample(item,part,parameters)
    ancestor=nodes[parent]
    branch=ancestor['active'] and (guard is None or guard==ancestor['resource'])
    active=branch and state['active']
    node=dict(id=len(nodes),parent=parent,path=path+'/'+item['label'],raw_path=raw,
              label=item['label'],type=item['type'],scope=scope,layer=item,part=part,
              guard=guard,branch_selected=branch,active=active,sample=state,
              cumulative_opacity=ancestor['cumulative_opacity']*state['opacity'] if active else 0.,
              resource=state['resource'])
    nodes.append(node)
    refs={c['src']+'/'+c['icon'] for f in item.get('frameList',[])
          if f['type']!=0 and isinstance(c:=f.get('content'),dict)
          and c.get('src') is not None and c.get('icon') is not None
          and c['src']+'/'+c['icon'] in parts}
    for key in sorted(refs,key=order.__getitem__):
        motion(key,node['id'],node['path']+'/'+key,key,stack)
    for i,child in enumerate(item.get('children',[])):
        layer(child,part,node['id'],node['path'],raw+'/children/'+str(i),None,scope,stack)

base=data['metadata']['base'];base_key=base['chara']+'/'+base['motion']
motion(base_key,0,base_key,None,[])

def chain(node_id):
    out=[]
    while node_id:
        out.append(nodes[node_id]);node_id=nodes[node_id]['parent']
    return out

def is_sprite(node):
    resource=node['resource']
    return node['type']==0 and resource is not None and resource not in parts and not resource.startswith('blank/')

def is_possible_sprite(node):
    if node['type']!=0:return False
    for frame in node['layer'].get('frameList',[]):
        content=frame.get('content')
        if frame['type']==0 or not isinstance(content,dict):continue
        src,icon=content.get('src'),content.get('icon')
        if src is not None and icon is not None and src!='blank' and src+'/'+icon not in parts:
            return True
    return False

def short(node):
    sample=node['sample'];control=sample.get('binding')
    return dict(id=node['id'],path=node['path'],raw_path=node['raw_path'],label=node['label'],
                active=node['active'],local_opacity=sample.get('opacity',0),
                cumulative_opacity=node['cumulative_opacity'],resource=node['resource'],
                bp=sample.get('bp',False),binding=control,
                binding_value=parameters.get(control['id'],0) if control else None,
                sample_time=sample.get('time'))

def candidate_grid_state(item):
    summed=[0.]*32
    all_neutral=True
    for control in item['meshCombinator']['combinatorList']:
        var=control['variable'];value=parameters.get(var['key'],0)
        q=max(0,min(1,(value-var['rangeBegin'])/(var['rangeEnd']-var['rangeBegin'])))*(var['meshCount']-1)
        lo=math.floor(q);hi=min(lo+1,var['meshCount']-1);t=q-lo
        all_neutral &= control['neutralIndex']>=0 and lo==control['neutralIndex'] and t<2**-23
        raw=resx['ExtraFlattenArrays'][control['rawMeshList'].split('#resource')[1]]
        for i in range(32):summed[i]+=(1-t)*raw[lo*32+i]+t*raw[hi*32+i]
    identity=[v for y in range(4) for x in range(4) for v in (x/3,y/3)]
    return dict(all_neutral_under_candidate_formula=all_neutral,
                max_sampled_grid_deviation_from_identity=max(abs(a-b) for a,b in zip(summed,identity)),
                interpretation='Candidate clamped linear interpolation/sum only; not a source-engine evaluation.')

owner_instances=[]
for node in nodes[1:]:
    if 'meshCombinator' not in node['layer']:continue
    ancestors=chain(node['id'])
    descendant=[n for n in nodes[1:] if node['id'] in {a['id'] for a in chain(n['id'])}]
    active_sprites=[n for n in descendant if is_sprite(n) and n['active'] and n['cumulative_opacity']>0]
    all_sprites=[n for n in descendant if is_possible_sprite(n)]
    fade_ancestors=[short(a) for a in ancestors
                    if (c:=a['sample'].get('binding')) and c['id'].startswith('fade_')]
    fade_descendants=[short(a) for a in descendant
                      if (c:=a['sample'].get('binding')) and c['id'].startswith('fade_')]
    default=sample(node['layer'],node['part'],{})
    first=node['layer']['frameList'][0].get('content',{})
    owner_instances.append(dict(
        owner=short(node),owner_path=node['raw_path'],expanded_owner_path=node['path'],
        first_frame_opacity_raw=first.get('opa',255),default_own_opacity=default['opacity'],
        first_frame_src=first.get('src'),first_frame_bp=first.get('mesh',{}).get('bp'),
        mesh_sync_child_mask=node['layer'].get('meshSyncChildMask',0),
        controls=[dict(variable=c['variable']['key'],value=parameters.get(c['variable']['key'],0),
                       neutral_index=c['neutralIndex'],resource=c['rawMeshList'])
                  for c in node['layer']['meshCombinator']['combinatorList']],
        candidate_grid_state=candidate_grid_state(node['layer']),
        nearest_fade_parameter=fade_ancestors[0]['binding']['id'] if fade_ancestors else None,
        fade_ancestor_chain=fade_ancestors,
        fade_descendant_gates=fade_descendants,
        inactive_or_zero_opacity_possible_sprite_descendants=[short(n) for n in all_sprites
            if not n['active'] or n['cumulative_opacity']<=0],
        ancestor_active_bp_nodes=[short(a) for a in ancestors[1:] if a['active'] and a['sample'].get('bp')],
        potential_descendant_sprite_count=len(all_sprites),
        selected_positive_opacity_descendant_sprite_count=len(active_sprites),
        selected_positive_opacity_descendant_sprites=[short(n) for n in active_sprites],
        selected_positive_opacity_bp_descendant_count=sum(n['sample'].get('bp',False) for n in descendant if n['active'] and n['cumulative_opacity']>0),
        classification=('unselected_or_inactive_owner' if not node['active'] else
                        'zero_opacity_owner' if node['cumulative_opacity']<=0 else
                        'positive_opacity_sprite_descendants' if active_sprites else
                        'no_selected_positive_opacity_sprite_descendants'),
        visibility_limit='Topology/frame/opacity only; no stencil, occlusion, clipping, inheritance-warp influence or original-engine field-consumption claim.'))

raw_seen={x['owner_path'] for x in owner_instances}
counts=collections.Counter(x['classification'] for x in owner_instances)
report={'scope':'offline NekoMote-style topology, frame and opacity reconstruction; no renderer run',
        'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'parameters':str(PARAMS),'parameters_sha256':hashlib.sha256(PARAMS.read_bytes()).hexdigest(),
        'parameter_count':len(parameters),'base':base_key,'expanded_node_count':len(nodes)-1,
        'raw_combinator_owners':len(raw_owners),'expanded_combinator_owners':len(owner_instances),
        'uninstantiated_raw_owners':sorted(set(raw_owners)-raw_seen),
        'classification_counts':dict(counts),
        'nearest_fade_counts':dict(collections.Counter(x['nearest_fade_parameter'] or '(none)' for x in owner_instances)),
        'positive_descendant_and_non_neutral_candidate_count':sum(
            x['selected_positive_opacity_descendant_sprite_count']>0 and
            not x['candidate_grid_state']['all_neutral_under_candidate_formula'] for x in owner_instances),
        'no_positive_opacity_descendant_details':[
            {'node':162,'role':'cheek mask deformation parent','gate':'face_cheek=4',
             'reason':'Referenced face_parts/頬mask chooses time4 type0 terminal; textured frame at0 is not selected.'},
            {'node':225,'role':'right arm B deformation parent','gate':'downstream fade_b=1',
             'reason':'Owner is above fade_b, not below it. Fade opacity is0 and direct B sprite is terminal at time60.'},
            {'node':246,'role':'left arm B deformation parent','gate':'downstream fade_b=1',
             'reason':'Owner is above fade_b, not below it. Fade opacity is0 and direct B sprite is terminal at time60.'}],
        'conclusion':'All 43 own blank resources with null bp, but blank deformation parents can lie on live sprite ancestry. Classify by selected/opacity descendants, not by whether the owner draws itself. No proof here that original FreeMote consumes the combinator.',
        'owners':owner_instances,'production_modified':False,'browser_used':False,'board_connected':False}
output=BASE/'agent_audit/combinator_pose_a_visibility.json'
output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
with (BASE/'agent_audit/combinator_pose_a_visibility.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f)
    writer.writerow(['node','owner_path','expanded_owner_path','label','nearest_fade_parameter','default_own_opacity',
                     'current_cumulative_opacity','classification','positive_opacity_sprite_descendants','downstream_fade_keys'])
    for x in owner_instances:
        writer.writerow([x['owner']['id'],x['owner_path'],x['expanded_owner_path'],x['owner']['label'],
            x['nearest_fade_parameter'],x['default_own_opacity'],x['owner']['cumulative_opacity'],
            x['classification'],x['selected_positive_opacity_descendant_sprite_count'],
            '|'.join(sorted({g['binding']['id'] for g in x['fade_descendant_gates']}))])
print(json.dumps({k:v for k,v in report.items() if k not in ['owners','conclusion']},ensure_ascii=True,indent=2))
