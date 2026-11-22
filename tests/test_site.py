import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools import frame
from tools.build_site import FRAME_NAME, OG_NAME, OG_SIZE, ZIP_NAME, build, load, room_zip


class SiteTest(unittest.TestCase):
    def test_every_profile_is_hung_and_zipped(self):
        collections = load()
        works = [w for c in collections for w in c["works"]]
        self.assertEqual(len(works), 56)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            page = (out / "index.html").read_text(encoding="utf-8")
            self.assertEqual(page.count('<article class="work'), len(works))
            self.assertEqual(page.count('<article class="work feature"'), len(collections))
            for w in works:
                self.assertTrue((out / w["file"]).is_file(), w["file"])
                self.assertTrue(w["text"], w["name"])
            with zipfile.ZipFile(out / ZIP_NAME) as zf:
                self.assertEqual(len(zf.namelist()), len(works))
            for c in collections:
                self.assertIn(f'href="{room_zip(c["slug"])}"', page)
                with zipfile.ZipFile(out / room_zip(c["slug"])) as zf:
                    self.assertEqual(sorted(zf.namelist()), sorted(f"gallery-zero/{w['file']}" for w in c["works"]))
            og = (out / OG_NAME).read_bytes()
            self.assertEqual(og[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", og[16:24]), OG_SIZE)
            self.assertIn(f'{OG_NAME}"', page)
            gilt = (out / FRAME_NAME).read_bytes()
            self.assertEqual(struct.unpack(">II", gilt[16:24]), (frame.SIZE, frame.SIZE))
            self.assertIn(f"url({FRAME_NAME}) {frame.WIDTH} ", page)


if __name__ == "__main__":
    unittest.main()
