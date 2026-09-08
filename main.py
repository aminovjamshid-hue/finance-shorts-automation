import os
import sys
import logging
import requests
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Default Configuration Constants
DEFAULT_DIFY_BASE_URL = os.getenv("DIFY_BASE_URL", "https://dify.ai")
DEFAULT_DIFY_API_KEY = os.getenv("DIFY_API_KEY", "app-P0OifMZDIFvzd2wDH8ma6qUX")
DEFAULT_TOPIC = "Daily money habits for Gen Z"


class DifyClient:
    """
    Client for interacting with Dify.ai API endpoints (Chatflow / Workflows).
    """

    def __init__(self, api_key: str = DEFAULT_DIFY_API_KEY, base_url: str = DEFAULT_DIFY_BASE_URL):
        self.api_key = api_key
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


def generate_voiceover(script_text: str) -> Dict[str, Any]:
    """
    Placeholder function for ElevenLabs API integration.
    Turns finalized script text into high-quality audio voiceover.

    :param script_text: The finalized script text to be converted to voiceover audio.
    :return: Dict containing placeholder metadata or audio generation status.
    """
    logger.info("--- [PLACEHOLDER] ElevenLabs Voiceover Generation ---")
    logger.info(f"Script Text Length: {len(script_text)} characters")
    logger.info("ElevenLabs API integration will be implemented in the next step.")

    return {
        "status": "placeholder",
        "message": "ElevenLabs API integration pending",
        "script_length": len(script_text),
        "audio_url": None
    }


def run_automation_pipeline(topic: str = DEFAULT_TOPIC) -> Dict[str, Any]:
    """
    Executes the full Smart Financial Automation pipeline:
    1. Triggers Dify Chatflow with topic.
    2. Receives and extracts finalized script from Dify ANSWER block.
    3. Passes script to voiceover generator placeholder.

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

    # Step 4: Generate Voiceover (Placeholder)
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
