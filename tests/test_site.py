import html
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools import ports
from tools.build_site import (
    FRAMES, INSTALL_CMD, OG_NAME, OG_SIZE, ZIP_NAME, all_zip, build, install_cmd, load, port_file, room_zip,
)


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
            for i, frame in enumerate(FRAMES):
                self.assertEqual((out / frame["file"]).read_bytes()[8:12], b"WEBP")
                self.assertIn(f'<img class="frame f{i}" src="{frame["file"]}"', page)
                self.assertIn(f'.gilt[data-frame="{i}"] .hero-term', page)
            self.assertIn("Import&hellip;", page)
            self.assertIn(html.escape(INSTALL_CMD), page)
            self.assertNotIn("Double-click a", page)
            self.assertTrue((out / "install.sh").is_file())

            # The terminal picker, and the same downloads for every port.
            self.assertEqual(page.count('name="terminal"'), 1 + len(ports.PORTS))
            self.assertIn("Ghostty, iTerm2, kitty, WezTerm, Alacritty and Warp", page)
            self.assertIn(html.escape(install_cmd("ghostty")), page.replace("\\/", "/"))
            for port in ports.PORTS:
                with zipfile.ZipFile(out / all_zip(port.app)) as zf:
                    names = zf.namelist()
                self.assertEqual(len(names), len(works), port.app)
                self.assertTrue(all(n.startswith(f"gallery-zero-{port.app}/") for n in names), port.app)
                for c in collections:
                    with zipfile.ZipFile(out / room_zip(c["slug"], port.app)) as zf:
                        self.assertEqual(len(zf.namelist()), len(c["works"]))
                    for w in c["works"]:
                        self.assertTrue((out / port_file(w, c["slug"], port.app)).is_file())


if __name__ == "__main__":
    unittest.main()
