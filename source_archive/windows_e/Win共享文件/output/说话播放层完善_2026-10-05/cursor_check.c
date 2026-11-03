
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
