"""Source equivalence checks for the isolated new exact-blend ABI."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
OLD = (ROOT / 'baseline/aura/tools/native_pixels.cpp').read_text()
NEW = (ROOT / 'candidate/aura/tools/native_pixels.cpp').read_text()


def body(source, name):
    match = re.search(r'\b' + re.escape(name) + r'\([^;]*?\)\s*\{', source)
    if match is None:
        raise AssertionError(name)
    start, depth = match.end() - 1, 0
    for index in range(start, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError('Unbalanced function: ' + name)


class ExactBlendSourceTests(unittest.TestCase):
    def test_legacy_pixel_video_helpers_unchanged(self):
        for name in ('blend8', 'flat8', 'aura_blend', 'aura_pose', 'aura_pixels_create',
                     'aura_pixels_threads', 'aura_pixels_mode', 'aura_pixels_times',
                     'aura_pixels_destroy', 'aura_video_create', 'aura_video_attach',
                     'aura_video_push', 'aura_video_stats', 'aura_video_destroy', 'aura_rgb565_copy'):
            self.assertEqual(body(OLD, name), body(NEW, name), name)

    def test_existing_pose_body_recovers_exactly_for_legacy_flag(self):
        old = body(OLD, 'aura_pose_blend')
        new = body(NEW, 'aura_pose_blend_impl')
        new = new.replace('\n  if(exact_blend&&other&&(!std::isfinite(blend)||blend<0||blend>1))return -1;', '')
        new = new.replace('for(int c=0;c<4;++c)\n    v.val[c]=exact_blend?blend8_exact(v.val[c],vv.val[c],blend):blend8(v.val[c],vv.val[c],weight);',
                          'for(int c=0;c<4;++c)v.val[c]=blend8(v.val[c],vv.val[c],weight);')
        self.assertEqual(old, new)

    def test_old_and_new_export_choose_distinct_flags(self):
        arguments = 'owner,rgba,other,blend,w,h,m,ow,oh,r,g,b,out,'
        self.assertEqual(body(NEW, 'aura_pose_blend'), '{\n return aura_pose_blend_impl(' + arguments + 'false);\n}')
        self.assertEqual(body(NEW, 'aura_pose_blend_exact'), '{\n return aura_pose_blend_impl(' + arguments + 'true);\n}')
        self.assertIn('static int aura_pose_blend_impl(', NEW)


if __name__ == '__main__':
    unittest.main(verbosity=2)
