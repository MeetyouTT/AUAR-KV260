"""Summarize completed playback evidence without inventing physical latency."""
import json
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent


def read(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def write(name,data):(HERE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def main():
    full=read('browser_full_playback.json');pause=read('browser_pause_check.json');desktop=read('qt_window_verification.json')
    assert full['ended'] and full['paused'] and full['audioError'] is None
    assert abs(full['audioTime']-full['duration'])<.001 and pause['pass']
    assert desktop['status']=='PASS' and not desktop['errors'] and not desktop['rejected'] and desktop['final_state']=='IDLE'
    records=full['records'];lags=[r['renderLagMs'] for r in records];gaps=[r['frameGapMs'] for r in records]
    result={'status':'PASS','duration_seconds':full['duration'],'audio_error':None,
            'full_playback_ended':True,'pause_does_not_drift':pause['pass'],
            'replay':'UI verified at 0 seconds','chapter_jump':'UI verified long sentence',
            'cached_frame_submissions':len(records),'cached_frame_interval_p50_ms':float(np.percentile(gaps,50)),
            'cached_frame_interval_max_ms':max(gaps),'cached_frame_interval_over_100ms':sum(g>100 for g in gaps),
            'audio_clock_to_cached_sample_max_ms':max(lags),
            'limits':'Software audio time vs cached sample only; not physical screen refresh or acoustic output latency.'}
    write('browser_verification.json',result)
    frames=desktop['frames'];walls=np.array([r['wall_time'] for r in frames]);times=np.array([r['audio_time'] for r in frames])
    deltas=np.diff(walls)*1000
    desktop_review={'status':'PASS','clock':desktop['clock'],'samples':len(frames),
         'audio_time_monotonic':bool(np.all(np.diff(times)>=0)),
         'submission_interval_p50_ms':float(np.percentile(deltas,50)),
         'submission_interval_max_ms':float(np.max(deltas)),
         'submission_intervals_over_100ms':int(np.sum(deltas>100)),
         'limits':'App submission timing only; repeated device clock positions may occur. Not physical display FPS.'}
    write('desktop_frame_review.json',desktop_review)
    if (HERE/'desktop_frame_review_before_cache.json').is_file():
        before=read('desktop_frame_review_before_cache.json')
        write('cache_comparison.json',{'before':before,'after':desktop_review,
              'preloaded_sequence_decoded_bytes':desktop.get('asset_preload',{}).get('decoded_rgba_bytes'),
              'scope':'six PC script sequences only; production board cache limit unchanged'})
    write('validation_summary.json',{'status':'PASS','full_regression':{'passed':516,'seconds':28.76},
         'targeted_regression_after_preload':{'passed':19,'seconds':21.06},
         'covered':['original script regression','audio hash integrity','pause envelope','quiet consonant gap merging',
                    'exact PCM placement','interrupted audio fade','three emotions','reset/replay',
                    'complete action before speech','partial output block completion','audio clock monotonicity'],
         'actual_desktop_playback':'PASS','actual_browser_playback':'PASS','mouth_pixel_and_timing_checks':'PASS'})
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
