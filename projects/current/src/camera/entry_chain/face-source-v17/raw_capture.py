"""Offer the capture callback's exact image/fid/stamp before detector locks."""
import time


def raw_first_offer(original_offer):
    def offer(face, image, fid, stamp):
        flow = getattr(face, '_edge_flow', None)
        if flow is not None:
            flow.offer(image, fid, stamp)
        began = time.monotonic()
        try:
            # Detection receives the identical original call once; its source,
            # admission, scheduling and identity callback remain untouched.
            return original_offer(face, image, fid, stamp)
        finally:
            if flow is not None:
                flow.note_detector_offer((time.monotonic()-began)*1000)
    return offer


def install(source):
    original_install = source.install

    def install_raw(camera, **options):
        if getattr(camera, '_edge_face_raw_capture_v11', False):
            return
        if getattr(camera, '_edge_face_source_installed', False):
            raise RuntimeError('Raw capture hook must be installed with the face source')
        from board.identity.face_targets import FaceTargetService
        original_offer = FaceTargetService.offer
        original_install(camera, **options)
        # Replace the original extension's detector-first wrapper. Capturing
        # original_offer before install also prevents duplicate flow delivery.
        FaceTargetService.offer = raw_first_offer(original_offer)
        camera._edge_face_raw_capture_v11 = True

    source.install = install_raw
