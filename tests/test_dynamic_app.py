import unittest

from app import create_app


class DynamicAppTests(unittest.TestCase):
    def test_app_serves_homepage(self):
        app = create_app()
        client = app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("सजिलो एआई खबर", response.get_data(as_text=True))

    def test_api_articles_works(self):
        app = create_app()
        client = app.test_client()
        response = client.get("/api/articles")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("articles", payload)
        self.assertTrue(len(payload["articles"]) > 0)


if __name__ == "__main__":
    unittest.main()
