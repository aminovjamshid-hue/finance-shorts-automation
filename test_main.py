import unittest
from unittest.mock import patch, MagicMock
import requests

import os
from main import (
    DifyClient,
    generate_voiceover,
    run_automation_pipeline,
    DEFAULT_DIFY_API_KEY,
    DEFAULT_DIFY_BASE_URL,
    DEFAULT_ELEVENLABS_VOICE_ID,
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

    @patch("requests.post")
    def test_generate_voiceover_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_mp3_audio_data"
        mock_post.return_value = mock_response

        script_text = "Save 20% of your income daily."
        test_filename = "test_output.mp3"

        try:
            result = generate_voiceover(
                script_text=script_text,
                voice_id="test_voice_id",
                api_key="test_xi_key",
                base_url="https://api.elevenlabs.io",
                output_filename=test_filename
            )

            mock_post.assert_called_once_with(
                "https://api.elevenlabs.io/v1/text-to-speech/test_voice_id",
                headers={
                    "xi-api-key": "test_xi_key",
                    "Content-Type": "application/json",
                },
                json={
                    "text": script_text,
                    "model_id": "eleven_multilingual_v2",
                },
                timeout=60,
            )

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["voice_id"], "test_voice_id")
            self.assertEqual(result["output_filename"], test_filename)
            self.assertEqual(result["audio_bytes_length"], len(b"fake_mp3_audio_data"))

            self.assertTrue(os.path.exists(test_filename))
            with open(test_filename, "rb") as f:
                self.assertEqual(f.read(), b"fake_mp3_audio_data")
        finally:
            if os.path.exists(test_filename):
                os.remove(test_filename)

    def test_generate_voiceover_empty_script_raises(self):
        with self.assertRaises(ValueError):
            generate_voiceover(script_text="   ")

    @patch("requests.post")
    def test_generate_voiceover_http_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Bad Request")
        mock_post.return_value = mock_response

        with self.assertRaises(requests.exceptions.HTTPError):
            generate_voiceover("Some script", api_key="test_key")

    @patch("main.generate_voiceover")
    @patch("main.DifyClient")
    def test_run_automation_pipeline(self, mock_dify_cls, mock_generate_voiceover):
        mock_client_inst = MagicMock()
        mock_client_inst.trigger_chatflow.return_value = {
            "answer": "Polished script from CEO, Creative, and Negative Critic agents."
        }
        mock_client_inst.extract_script.return_value = "Polished script from CEO, Creative, and Negative Critic agents."
        mock_dify_cls.return_value = mock_client_inst

        mock_generate_voiceover.return_value = {
            "status": "success",
            "output_filename": "output_voiceover.mp3",
            "audio_bytes_length": 1024
        }

        pipeline_res = run_automation_pipeline(DEFAULT_TOPIC)

        self.assertEqual(pipeline_res["topic"], DEFAULT_TOPIC)
        self.assertEqual(pipeline_res["script"], "Polished script from CEO, Creative, and Negative Critic agents.")
        self.assertEqual(pipeline_res["voiceover"]["status"], "success")
        mock_generate_voiceover.assert_called_once_with("Polished script from CEO, Creative, and Negative Critic agents.")


if __name__ == "__main__":
    unittest.main()
