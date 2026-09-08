import unittest
from unittest.mock import patch, MagicMock
import requests

from main import (
    DifyClient,
    generate_voiceover,
    run_automation_pipeline,
    DEFAULT_DIFY_API_KEY,
    DEFAULT_DIFY_BASE_URL,
    DEFAULT_TOPIC,
)


class TestDifyClient(unittest.TestCase):

    def setUp(self):
        self.client = DifyClient(api_key="test_api_key", base_url="https://dify.ai")

    @patch("requests.post")
    def test_trigger_chatflow_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "event": "message",
            "task_id": "task_123",
            "id": "msg_123",
            "answer": "Here is a viral financial script on Gen Z habits.",
            "status": "succeeded"
        }
        mock_post.return_value = mock_response

        topic = "Daily money habits for Gen Z"
        res = self.client.trigger_chatflow(query=topic)

        mock_post.assert_called_once_with(
            "https://dify.ai/v1/chat-messages",
            headers={
                "Authorization": "Bearer test_api_key",
                "Content-Type": "application/json",
            },
            json={
                "inputs": {"topic": topic},
                "query": topic,
                "response_mode": "blocking",
                "user": "us_finance_automation",
            },
            timeout=60,
        )
        self.assertEqual(res["answer"], "Here is a viral financial script on Gen Z habits.")

    @patch("requests.post")
    def test_trigger_chatflow_http_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError):
            self.client.trigger_chatflow("test topic")

    def test_extract_script_answer_field(self):
        response_data = {"answer": "  Finalized polished script content  "}
        script = self.client.extract_script(response_data)
        self.assertEqual(script, "Finalized polished script content")

    def test_extract_script_fallback_outputs(self):
        response_data = {"data": {"outputs": {"text": "Workflow text output"}}}
        script = self.client.extract_script(response_data)
        self.assertEqual(script, "Workflow text output")

    def test_extract_script_empty_raises(self):
        with self.assertRaises(ValueError):
            self.client.extract_script({})

    def test_extract_script_missing_key_raises(self):
        with self.assertRaises(KeyError):
            self.client.extract_script({"unknown_key": "val"})


class TestVoiceoverAndPipeline(unittest.TestCase):

    def test_generate_voiceover_placeholder(self):
        script_text = "Save 20% of your income daily."
        result = generate_voiceover(script_text)

        self.assertEqual(result["status"], "placeholder")
        self.assertEqual(result["script_length"], len(script_text))
        self.assertIsNone(result["audio_url"])

    @patch.object(DifyClient, "trigger_chatflow")
    def test_run_automation_pipeline(self, mock_trigger):
        mock_trigger.return_value = {
            "answer": "Polished script from CEO, Creative, and Negative Critic agents."
        }

        pipeline_res = run_automation_pipeline(DEFAULT_TOPIC)

        self.assertEqual(pipeline_res["topic"], DEFAULT_TOPIC)
        self.assertEqual(pipeline_res["script"], "Polished script from CEO, Creative, and Negative Critic agents.")
        self.assertEqual(pipeline_res["voiceover"]["status"], "placeholder")


if __name__ == "__main__":
    unittest.main()
