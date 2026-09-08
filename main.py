import os
import sys
import logging
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Default Configuration Constants
DEFAULT_DIFY_BASE_URL = os.getenv("DIFY_BASE_URL", "https://dify.ai")
DEFAULT_DIFY_API_KEY = os.getenv("DIFY_API_KEY")
DEFAULT_ELEVENLABS_BASE_URL = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io")
DEFAULT_ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
DEFAULT_ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "TX3LPaxmHKxFdv7VOQHJ")
DEFAULT_TOPIC = "Daily money habits for Gen Z"


class DifyClient:
    """
    Client for interacting with Dify.ai API endpoints (Chatflow / Workflows).
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = DEFAULT_DIFY_BASE_URL):
        self.api_key = api_key or DEFAULT_DIFY_API_KEY
        if not self.api_key:
            raise ValueError("Dify API key is required. Set DIFY_API_KEY environment variable or pass api_key.")
        self.base_url = base_url.rstrip("/")

    def trigger_chatflow(
        self,
        query: str,
        inputs: Optional[Dict[str, Any]] = None,
        user: str = "us_finance_automation",
        response_mode: str = "blocking"
    ) -> Dict[str, Any]:
        """
        Triggers the Dify Chatflow workflow with the provided query topic and inputs.

        :param query: User input topic/prompt.
        :param inputs: Optional additional input variables dict for the workflow.
        :param user: Identifier for the user session.
        :param response_mode: 'blocking' or 'streaming'. Defaults to 'blocking'.
        :return: JSON response payload from Dify API.
        """
        endpoint = f"{self.base_url}/v1/chat-messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "inputs": inputs or {"topic": query},
            "query": query,
            "response_mode": response_mode,
            "user": user
        }

        logger.info(f"Sending request to Dify API at endpoint: {endpoint}")
        logger.info(f"Triggering workflow for topic: '{query}'")

        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to communicate with Dify API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}, body: {e.response.text}")
            raise

    def extract_script(self, response_data: Dict[str, Any]) -> str:
        """
        Extracts the finalized script output from the Dify ANSWER block / response payload.

        :param response_data: Raw JSON dict returned from Dify API.
        :return: Extracted script string.
        """
        if not response_data:
            raise ValueError("Empty response received from Dify API.")

        # Dify Chatflow blocking mode returns the result in the 'answer' field
        if "answer" in response_data and response_data["answer"]:
            return response_data["answer"].strip()

        # Fallback check for workflow outputs format
        outputs = response_data.get("data", {}).get("outputs", {})
        if isinstance(outputs, dict):
            if "text" in outputs:
                return str(outputs["text"]).strip()
            if "answer" in outputs:
                return str(outputs["answer"]).strip()
            if "result" in outputs:
                return str(outputs["result"]).strip()

        # If answer exists in nested format or raw text
        if "result" in response_data:
            return str(response_data["result"]).strip()

        raise KeyError(f"Could not extract script output from Dify response payload keys: {list(response_data.keys())}")


def generate_voiceover(
    script_text: str,
    voice_id: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    output_filename: str = "output_voiceover.mp3",
    model_id: str = "eleven_multilingual_v2"
) -> Dict[str, Any]:
    """
    Converts finalized script text into high-quality audio voiceover using the ElevenLabs Text-to-Speech API.

    :param script_text: Finalized script text to convert to voiceover audio.
    :param voice_id: ElevenLabs voice identifier.
    :param api_key: API key for ElevenLabs authentication.
    :param base_url: Base URL for ElevenLabs API.
    :param output_filename: Path to save the generated audio MP3 file.
    :param model_id: ElevenLabs TTS model ID.
    :return: Dict containing execution status, output filename, and byte size.
    """
    if not script_text or not script_text.strip():
        raise ValueError("Script text cannot be empty for voiceover generation.")

    effective_api_key = api_key or DEFAULT_ELEVENLABS_API_KEY
    if not effective_api_key:
        raise ValueError("ElevenLabs API key is required. Set ELEVENLABS_API_KEY environment variable or pass api_key.")

    effective_voice_id = voice_id or DEFAULT_ELEVENLABS_VOICE_ID
    effective_base_url = (base_url or DEFAULT_ELEVENLABS_BASE_URL).rstrip("/")

    endpoint = f"{effective_base_url}/v1/text-to-speech/{effective_voice_id}"
    headers = {
        "xi-api-key": effective_api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": script_text,
        "model_id": model_id
    }

    logger.info(f"Triggering ElevenLabs Text-to-Speech API for voice_id: '{effective_voice_id}'")
    logger.info(f"Script length: {len(script_text)} characters")

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        audio_bytes = response.content
        if output_filename:
            with open(output_filename, "wb") as f:
                f.write(audio_bytes)
            logger.info(f"Voiceover audio successfully saved to '{output_filename}' ({len(audio_bytes)} bytes)")

        return {
            "status": "success",
            "voice_id": effective_voice_id,
            "output_filename": output_filename,
            "audio_bytes_length": len(audio_bytes),
            "script_length": len(script_text)
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to generate voiceover via ElevenLabs API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}, body: {e.response.text}")
        raise


def run_automation_pipeline(topic: str = DEFAULT_TOPIC) -> Dict[str, Any]:
    """
    Executes the full Smart Financial Automation pipeline:
    1. Triggers Dify Chatflow with topic.
    2. Receives and extracts finalized script from Dify ANSWER block.
    3. Generates voiceover audio using ElevenLabs text-to-speech API.

    :param topic: Prompt topic for finance reel script generation.
    :return: Pipeline execution summary dict.
    """
    logger.info(f"Starting US Finance Shorts/Reels Automation Pipeline...")

    client = DifyClient()

    # Step 1 & 2: Trigger workflow and receive response
    response = client.trigger_chatflow(query=topic)

    # Step 3: Extract finalized script from Dify ANSWER block
    script_text = client.extract_script(response)
    logger.info("Successfully extracted finalized script from Dify response:")
    logger.info(f"\n--- SCRIPT START ---\n{script_text}\n--- SCRIPT END ---")

    # Step 4: Generate Voiceover via ElevenLabs
    voiceover_result = generate_voiceover(script_text)

    return {
        "topic": topic,
        "script": script_text,
        "voiceover": voiceover_result
    }


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOPIC
    try:
        results = run_automation_pipeline(topic=topic)
        print("\nAutomation Pipeline Completed Successfully!")
        print(f"Topic: {results['topic']}")
        print(f"Script Preview: {results['script'][:100]}...")
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
