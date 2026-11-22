import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.build_site import ZIP_NAME, build, load


class SiteTest(unittest.TestCase):
    def test_every_profile_is_hung_and_zipped(self):
        collections = load()
        works = [w for c in collections for w in c["works"]]
        self.assertEqual(len(works), 56)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            page = (out / "index.html").read_text(encoding="utf-8")
            self.assertEqual(page.count('<article class="work"'), len(works))
            for w in works:
                self.assertTrue((out / w["file"]).is_file(), w["file"])
                self.assertTrue(w["text"], w["name"])
            with zipfile.ZipFile(out / ZIP_NAME) as zf:
                self.assertEqual(len(zf.namelist()), len(works))


if __name__ == "__main__":
    unittest.main()
