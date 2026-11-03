"""Public-fixture provenance and scoring checks; no ASR package/model/device."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

import public_quality_worker as worker


class QualityWorkerChecks(unittest.TestCase):
    def test_fixed_corpus_pin_and_negation_sensitive_character_scoring(self):
        source = Path(__file__).with_name("synthetic_acceptance_texts.json").read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(), worker.TEXT_SET_SHA)
        cases = json.loads(source)["cases"]
        self.assertEqual([(x["id"], x["text"], tuple(x["critical_spans"])) for x in cases],
                         list(worker.CASES))
        self.assertEqual(worker.character_error("我没有关灯。", "我关灯")
                         ["edit_distance"], 2)
        self.assertGreater(worker.character_error("三本书", "3本书")["cer"], 0)
        self.assertEqual(worker.character_error("你好，测试。", "你好测试")["cer"], 0)

    def test_public_manifest_and_audio_guard_refuse_tampering(self):
        with tempfile.TemporaryDirectory(prefix="public_asr_quality_check_") as temp:
            root = Path(temp).resolve()
            rows = []
            for ordinal, (case_id, text, _) in enumerate(worker.CASES, 1):
                path = root / (case_id + ".wav")
                with wave.open(str(path), "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(16000)
                    wav.writeframes(bytes((ordinal, 0)) * 160)
                rows.append({"id": case_id, "reference_text": text,
                             "wav_path": str(path), "samples": 160, "rate": 16000,
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            manifest = {"source_texts_sha256": worker.TEXT_SET_SHA,
                        "public_synthetic": True, "intended_not_human_verified": True,
                        "cases": rows}
            with patch.object(worker, "WAV_ROOT", root):
                self.assertEqual(len(worker.validate_manifest(manifest)), 8)
                variants = []
                altered = copy.deepcopy(manifest)
                altered["intended_not_human_verified"] = False
                variants.append(altered)
                altered = copy.deepcopy(manifest)
                altered["cases"][3]["reference_text"] = "我关灯，也锁门。"
                variants.append(altered)
                altered = copy.deepcopy(manifest)
                altered["cases"][0]["samples"] = 159
                variants.append(altered)
                altered = copy.deepcopy(manifest)
                altered["cases"][0]["sha256"] = "0" * 64
                variants.append(altered)
                altered = copy.deepcopy(manifest)
                altered["cases"][0]["wav_path"] = str(root.parent / "unrelated.wav")
                variants.append(altered)
                for index, altered in enumerate(variants):
                    with self.subTest(tamper=index):
                        with self.assertRaises(worker.Refused):
                            worker.validate_manifest(altered)


if __name__ == "__main__":
    unittest.main()
