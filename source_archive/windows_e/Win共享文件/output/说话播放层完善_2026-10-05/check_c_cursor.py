import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(r'E:\项目\共享文件夹\aura'); OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT))
from board.interaction.avatar_player import AvatarPlayer
from board.interaction.avatar_timing import Segments
source=r'''
#include <stdio.h>
#include "avatar_assets_table.h"
#include "avatar_playback.h"
int main(void) {
  for (int mode=0; mode<3; ++mode) {
    avatar_cursor_t p; avatar_cursor_reset(&p);
    for (int i=0;i<=600;++i) {
      double t=i/60.0;
      if (mode && i==100) avatar_cursor_request_exit(&p,mode==2);
      double pos=avatar_cursor_sample(&p,t,24.0,0,12,19,38);
      printf("%d %d %.12f %d %d\n",mode,i,pos,p.stage,p.done);
    }
  }
  return AVATAR_PRIMARY_WINDOW_ONLY == 1 && AVATAR_RESOURCES_COUNT == 16 ? 0 : 2;
}
'''
(OUT/'cursor_check.c').write_text(source,encoding='utf-8')
gcc=r'C:\Users\ZhaoZ\.vscode\mingw64\bin\gcc.exe'
subprocess.run([gcc,'-std=c99','-Wall','-Wextra','-Werror','-I',str(ROOT/'board/interaction/lvgl'),str(OUT/'cursor_check.c'),'-lm','-o',str(OUT/'cursor_check.exe')],check=True)
raw=subprocess.check_output([str(OUT/'cursor_check.exe')],text=True)
players={i:AvatarPlayer() for i in range(3)}
seg=Segments((0,12),(12,19),(19,38)); stages={'enter':0,'loop':1,'blend':2,'exit':3}
worst=0
for line in raw.splitlines():
    mode,i,pos,stage,done=line.split(); mode=int(mode); i=int(i); p=players[mode]
    if mode and i==100:
        p._switch_pending=mode==2; p.request_exit()
    expected=p.segment_stage_time('SPEAKING_NEUTRAL',seg,24,0,i/60)[0]*24
    delta=abs(expected-float(pos)); worst=max(worst,delta)
    assert delta<1e-9 and stages[p._stage]==int(stage) and p._exit_done==bool(int(done))
report={'compiled_with_warnings_as_errors':True,'samples':1803,'max_source_position_error':worst,
        'modes':['long_loop','stop_nearest_endpoint','pool_rotation_last_endpoint'],'hardware_tested':False}
(OUT/'c_cursor_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
