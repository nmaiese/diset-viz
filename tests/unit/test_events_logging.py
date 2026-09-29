import logging
import unittest
from app import app


class TestEventsLogging(unittest.TestCase):
    def test_analytics_event_log_level_and_emission(self):
        client = app.test_client()
        self.assertEqual(app.logger.getEffectiveLevel(), logging.INFO)
        with self.assertLogs(app.logger, level="INFO") as cm:
            response = client.post(
                "/api/events",
                json={"name": "page_view", "path": "/atlante"},
            )
            self.assertEqual(response.status_code, 204)
        self.assertTrue(any("analytics_event" in message for message in cm.output))


if __name__ == "__main__":
    unittest.main()
