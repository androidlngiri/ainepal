import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FallbackBehaviorTests(unittest.TestCase):
    def test_build_site_uses_seed_data_when_empty(self):
        module = load_module("build_site", "scripts/build_site.py")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data_file = root / "data" / "articles.json"
            data_file.parent.mkdir(parents=True)
            data_file.write_text("[]", encoding="utf-8")

            template = ROOT / "templates" / "site_template.html"
            output_file = root / "docs" / "index.html"
            module.DATA_FILE = data_file
            module.TEMPLATE_FILE = template
            module.OUTPUT_FILE = output_file

            module.main()

            html = output_file.read_text(encoding="utf-8")
            self.assertIn("सजिलो एआई खबर", html)
            self.assertIn("ओपनएआईले", html)
            self.assertIn("<html", html.lower())

    def test_fetch_module_has_seed_articles(self):
        module = load_module("fetch_and_translate", "scripts/fetch_and_translate.py")
        articles = module.get_seed_articles()
        self.assertTrue(len(articles) > 0)
        self.assertIn("headline_ne", articles[0])
        self.assertIn("summary_ne", articles[0])


if __name__ == "__main__":
    unittest.main()
