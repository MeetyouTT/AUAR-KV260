"""Discover static metric field names without exporting state text, images or identities."""
before,v,h=preflight()
branches={k:v.get(k) for k in ('avatar_display','avatar_renderer','ui_stage_timings_ms','ui_runtime_timings_ms',
                              'ui_settings_timings_ms','ui_callback_previous','ui_widget_writes','visual','vision')}
b=v.get('board_business',{})
branches.update(memory=b.get('memory'),business_dialogue=b.get('dialogue'),business= b,
                camera_health=h,camera_ui=get_json(8790,'/v1/ui/status'))

def describe(obj,depth=0):
    if not isinstance(obj,dict):return type(obj).__name__
    return {k:('number' if finite(x) else 'bool' if type(x) is bool else
               describe(x,depth+1) if isinstance(x,dict) and depth<2 else type(x).__name__)
            for k,x in obj.items() if k not in ('people','persons','faces','targets','tracklets','gallery','templates','identities',
                                               'history','turns','events','text','reply','transcript','photos','records','rows','last_error')}

print(json.dumps(dict(before=before,top_keys=sorted(v),metric_schema={k:describe(x) for k,x in branches.items()},
                      initial_ui_metrics={k:numeric(v.get(k)) for k in branches if k.startswith('ui_')},
                      initial_avatar=numeric(v.get('avatar_display')))))
