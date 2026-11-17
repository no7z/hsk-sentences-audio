"""Regression checks for preserving originals and not truncating long speech."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from lib.tts import CosyVoiceTTS, seed_sentence
from scripts import synth_audio


class AudioSafetyTest(unittest.TestCase):
    def test_pair_infers_once_and_uses_the_same_pcm(self):
        with tempfile.TemporaryDirectory() as folder:
            tts = CosyVoiceTTS.__new__(CosyVoiceTTS)
            tts._synth_raw, tts._encode = MagicMock(), MagicMock()
            normal, slow = Path(folder) / 'normal.mp3', Path(folder) / 'slow.mp3'
            tts.synth_pair('一句话。', normal, slow)
            tts._synth_raw.assert_called_once()
            self.assertEqual(tts._synth_raw.call_args.args[1], 1.0)
            calls = tts._encode.call_args_list
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0].args[0], calls[1].args[0])
            self.assertEqual([c.kwargs['speed'] for c in calls], [1.0, 0.8])

    def test_pair_never_reencodes_an_existing_normal(self):
        with tempfile.TemporaryDirectory() as folder:
            normal, slow = Path(folder) / 'normal.mp3', Path(folder) / 'slow.mp3'
            normal.write_bytes(b'protected normal')
            tts = CosyVoiceTTS.__new__(CosyVoiceTTS)
            tts._synth_raw, tts._encode = MagicMock(), MagicMock()
            tts.synth_pair('一句话。', normal, slow)
            tts._encode.assert_called_once()
            self.assertEqual(tts._encode.call_args.args[1], slow)
            self.assertEqual(normal.read_bytes(), b'protected normal')
    def test_sentence_seed_preserves_the_existing_normal_rendering(self):
        torch, numpy = MagicMock(), MagicMock()
        torch.cuda.is_available.return_value = False
        with patch.dict(sys.modules, {"torch": torch, "numpy": numpy}):
            self.assertEqual(seed_sentence("hsk7-0001"), 3964377347)
        torch.manual_seed.assert_called_once_with(3964377347)
        numpy.random.seed.assert_called_once_with(3964377347)

    def test_slow_audio_keeps_native_vocoder_speed_and_uses_pcm_tempo(self):
        with tempfile.TemporaryDirectory() as folder:
            tts = CosyVoiceTTS.__new__(CosyVoiceTTS)
            tts._synth_raw = MagicMock()
            with patch("lib.tts.subprocess.run") as encoder:
                tts.synth("慢速测试。", str(Path(folder) / "slow.mp3"), speed=0.8)
            self.assertEqual(tts._synth_raw.call_args.args[1], 1.0)
            command = encoder.call_args.args[0]
            self.assertTrue(command[command.index("-i") + 1].endswith("speech.wav"))
            self.assertTrue(command[command.index("-af") + 1].endswith(",atempo=0.8"))

    def test_normal_audio_does_not_change_tempo(self):
        with tempfile.TemporaryDirectory() as folder:
            tts = CosyVoiceTTS.__new__(CosyVoiceTTS)
            tts._synth_raw = MagicMock()
            with patch("lib.tts.subprocess.run") as encoder:
                tts.synth("常速测试。", str(Path(folder) / "normal.mp3"))
            command = encoder.call_args.args[0]
            self.assertNotIn("atempo", command[command.index("-af") + 1])

    def test_all_nonstream_segments_are_concatenated(self):
        tts = CosyVoiceTTS.__new__(CosyVoiceTTS)
        tts.ref_wav, tts.ref_text = "reference.wav", "reference text"
        first, last = MagicMock(), MagicMock()
        tts._model = SimpleNamespace(sample_rate=24000, inference_zero_shot=MagicMock(
            return_value=iter([{"tts_speech": first}, {"tts_speech": last}])))
        tts._torchaudio = MagicMock()
        torch = MagicMock()
        with patch.dict(sys.modules, {"torch": torch}):
            tts._synth_raw("a long sentence", 1.0, "out.wav")
        torch.cat.assert_called_once_with([first.cpu.return_value, last.cpu.return_value], dim=-1)
        tts._torchaudio.save.assert_called_once_with("out.wav", torch.cat.return_value, 24000)

    def test_empty_model_output_is_an_error(self):
        tts = CosyVoiceTTS.__new__(CosyVoiceTTS)
        tts.ref_wav, tts.ref_text = "reference.wav", "reference text"
        tts._model = SimpleNamespace(inference_zero_shot=lambda *a, **k: iter([]))
        with patch.dict(sys.modules, {"torch": MagicMock()}):
            with self.assertRaisesRegex(RuntimeError, "no speech"):
                tts._synth_raw("text", 1.0, "out.wav")

    def test_existing_mp3_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "original.mp3"
            path.write_bytes(b"original audio")
            tts = CosyVoiceTTS.__new__(CosyVoiceTTS)
            tts._synth_raw = MagicMock()
            with self.assertRaises(FileExistsError):
                tts.synth("text", str(path))
            self.assertEqual(path.read_bytes(), b"original audio")
            tts._synth_raw.assert_not_called()

    def test_failed_encoder_leaves_no_resumable_partial_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new.mp3"
            tts = CosyVoiceTTS.__new__(CosyVoiceTTS)
            tts._synth_raw = MagicMock()
            with patch("lib.tts.subprocess.run", side_effect=RuntimeError("encoder failed")):
                with self.assertRaisesRegex(RuntimeError, "encoder failed"):
                    tts.synth("text", str(path))
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_resume_synthesizes_only_missing_half_of_pair(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "dist/audio").mkdir(parents=True)
            (root / "data/reference").mkdir(parents=True)
            (root / "data/reference/ref_female.txt").write_text("ref", encoding="utf-8")
            (root / "dist/sentences.json").write_text(json.dumps([
                {"id": "hsk7-0001", "hsk_level": 7, "chinese": "测试。"}]), encoding="utf-8")
            normal = root / "dist/audio/hsk7-0001.mp3"
            normal.write_bytes(b"original normal audio")
            tts, torch = MagicMock(), MagicMock()
            torch.cuda.is_available.return_value = False
            with patch.object(synth_audio, "ROOT", root), patch.object(sys, "argv", ["worker", "--level", "7"]), \
                    patch("lib.tts.CosyVoiceTTS", return_value=tts), \
                    patch.dict(sys.modules, {"torch": torch, "numpy": MagicMock()}):
                synth_audio.main()
            tts.synth_pair.assert_called_once_with("测试。", normal, root / "dist/audio/hsk7-0001_slow.mp3")
            self.assertEqual(normal.read_bytes(), b"original normal audio")


if __name__ == "__main__":
    unittest.main()
