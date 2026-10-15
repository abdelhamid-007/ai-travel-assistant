"""Offline tests: no LLM, no Telegram, no internet needed.  python -m unittest -v"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

_tmp = tempfile.mkdtemp()
os.environ["OUTPUT_DIR"] = _tmp
os.environ["QUEUE_DB"] = str(Path(_tmp) / "q.sqlite")
os.environ["LLM_BASE_URL"] = "http://127.0.0.1:9/v1"      # unreachable on purpose

import common, producer, publisher           # noqa: E402


class ProducerTests(unittest.TestCase):
    def test_clean_scenes_drops_empty_and_caps(self):
        raw = [{"text": " a "}, {"text": ""}, "b"] + [{"text": "x"}] * 20
        out = producer.clean_scenes(raw)
        self.assertEqual(out[0]["text"], "a")
        self.assertLessEqual(len(out), 8)
        self.assertNotIn("", [s["text"] for s in out])

    def test_falls_back_when_llm_down(self):
        script, source = producer.write_script("saving money")
        self.assertEqual(source, "fallback")
        self.assertGreaterEqual(len(script["scenes"]), 3)

    def test_produces_real_vertical_mp4(self):
        info = producer.produce("saving money while travelling")
        self.assertTrue(Path(info["path"]).exists())
        self.assertGreater(info["duration"], 5)
        import subprocess
        size = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                               "-show_entries", "stream=width,height", "-of", "csv=p=0",
                               info["path"]], capture_output=True, text=True).stdout.strip()
        self.assertEqual(size, "1080,1920")


class PublisherTests(unittest.TestCase):
    def test_next_slot_is_future_and_skips_taken(self):
        now = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
        first = publisher.next_slot("telegram", now, set())
        second = publisher.next_slot("telegram", now, {first.isoformat()})
        self.assertGreater(first, now)
        self.assertGreater(second, first)
        self.assertEqual((first.hour, first.minute), (9, 0))

    def test_schedule_then_post_with_retry(self):
        db = Path(_tmp) / "pub.sqlite"
        con = common.connect(db)
        with con:
            con.execute("INSERT INTO videos (id,topic,title,script,path,duration) "
                        "VALUES ('v1','budget travel','Budget travel','{}','/x.mp4',20)")
        now = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        plan = publisher.schedule(["telegram", "tiktok"], db, now)
        self.assertEqual(len(plan), 2)
        self.assertEqual(publisher.schedule(["telegram"], db, now), [])   # nothing new, no duplicates

        later = datetime(2026, 1, 3, 0, 0, tzinfo=timezone.utc)
        boom = mock.Mock(side_effect=RuntimeError("api down"))
        for _ in range(publisher.MAX_ATTEMPTS):
            publisher.run_due(db, later, {"telegram": boom, "tiktok": publisher.post_dry_run})
        rows = {r["platform"]: r["status"] for r in con.execute("SELECT * FROM posts")}
        self.assertEqual(rows, {"telegram": "failed", "tiktok": "posted"})
        self.assertEqual(boom.call_count, publisher.MAX_ATTEMPTS)
        self.assertEqual(con.execute("SELECT status FROM videos").fetchone()[0], "done")

    def test_not_due_is_not_posted(self):
        db = Path(_tmp) / "pub2.sqlite"
        con = common.connect(db)
        with con:
            con.execute("INSERT INTO videos (id,topic,title,script,path,duration) "
                        "VALUES ('v2','t','T','{}','/x.mp4',20)")
        now = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        publisher.schedule(["telegram"], db, now)
        self.assertEqual(publisher.run_due(db, now), [])


if __name__ == "__main__":
    unittest.main()
