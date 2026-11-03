"""Map a user-selected screen line to the letterboxed camera image."""
import math


def camera_zone(settings, boot):
    if (settings.get('schema') != 'aura-face-zone-settings-1'
            or settings.get('board_boot_id') != boot
            or settings.get('target_kind') != 'face'
            or settings.get('reference') != 'face_center'
            or settings.get('mirror_horizontal') is not True
            or settings.get('frame_width') != 640 or settings.get('frame_height') != 480
            or settings.get('left_ratio') != 0.
            or settings.get('viewport') != [8,112,568,300]):
        raise ValueError('Current boot/display face-center boundary required')
    line = settings.get('right_ratio')
    if type(line) not in (int,float) or not math.isfinite(line) or not .3 <= line <= .95:
        raise ValueError('Invalid chosen line')
    x,y,w,h = settings['viewport']
    content_w = min(w,h*640/480)
    offset = (w-content_w)/2
    right = (line*w-offset)/content_w
    if not .2 < right < 1:
        raise ValueError('Line must be inside the actual camera image')
    return {'left_ratio':0., 'right_ratio':right,
            'reference':'face_center', 'content_rect':[x+offset,y,content_w,h],
            'screen_line_x':x+line*w}
