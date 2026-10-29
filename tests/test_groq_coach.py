"""Groq request, failure handling, and actual Streamlit chat interaction tests."""
import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from streamlit.testing.v1 import AppTest
from water_buddy.domain import default_state
from water_buddy.groq_coach import GroqError, groq_reply

ROOT = Path(__file__).resolve().parents[1]


class GroqTests(unittest.TestCase):
    def test_request_preserves_followup_and_excludes_intro(self):
        reply = MagicMock()
        reply.__enter__.return_value.read.return_value = json.dumps(
            {"choices": [{"message": {"content": " A helpful answer "}}]}
        )
        with patch("water_buddy.groq_coach.urlopen", return_value=reply) as call:
            result = groq_reply("fake-key", [
                {"role": "assistant", "content": "offline intro"},
                {"role": "user", "content": "Make a plan"},
                {"role": "assistant", "content": "Try regular sips"},
                {"role": "user", "content": "Explain that"},
            ], {"intake_ml": 500})
        self.assertEqual(result, "A helpful answer")
        request = call.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.get_header("Authorization"), "Bearer fake-key")
        self.assertEqual(call.call_args.kwargs["timeout"], 25)
        self.assertEqual(len(payload["messages"]), 4)
        self.assertEqual(payload["messages"][-1]["content"], "Explain that")
        self.assertNotIn("offline intro", str(payload))

    def test_errors_do_not_expose_provider_body_or_key(self):
        for error, expected in [
            (HTTPError("url", 401, "secret-key", {}, None), "API key"),
            (HTTPError("url", 429, "secret-key", {}, None), "usage limit"),
            (HTTPError("url", 503, "secret-key", {}, None), "unavailable"),
            (URLError("secret-key"), "connection"),
            (TimeoutError("secret-key"), "connection"),
        ]:
            with self.subTest(error=error), patch("water_buddy.groq_coach.urlopen", side_effect=error):
                with self.assertRaises(GroqError) as caught:
                    groq_reply("secret-key", [], {})
                self.assertIn(expected, str(caught.exception))
                self.assertNotIn("secret-key", str(caught.exception))

    def test_empty_response(self):
        reply = MagicMock()
        reply.__enter__.return_value.read.return_value = '{"choices": []}'
        with patch("water_buddy.groq_coach.urlopen", return_value=reply):
            with self.assertRaises(GroqError):
                groq_reply("fake", [], {})

    def app(self):
        app = AppTest.from_file(str(ROOT / "app_pages/coach.py"), default_timeout=15)
        app.session_state["data"] = default_state()
        return app

    def test_online_chat_and_clear(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "fake-key"}), patch(
            "water_buddy.groq_coach.groq_reply", return_value="Groq test response"
        ) as reply:
            app = self.app().run()
            self.assertFalse(app.exception)
            app.chat_input[0].set_value("Check my progress").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["coach_messages"][-1]["content"], "Groq test response")
            self.assertEqual(reply.call_count, 1)
            app.button(key="coach_clear_chat").click().run()
            self.assertEqual(len(app.session_state["coach_messages"]), 1)

    def test_missing_key_and_failure_fall_back(self):
        for key in ("", "fake-key"):
            with self.subTest(key=key), patch.dict(os.environ, {"GROQ_API_KEY": key}), patch(
                "water_buddy.groq_coach.groq_reply", side_effect=GroqError("Connection unavailable")
            ) as reply:
                app = self.app().run()
                app.chat_input[0].set_value("What is my goal?").run()
                self.assertFalse(app.exception)
                self.assertIn("current goal", app.session_state["coach_messages"][-1]["content"])
                self.assertEqual(reply.call_count, int(bool(key)))
                if key:
                    self.assertTrue(app.warning)


if __name__ == "__main__":
    unittest.main()
