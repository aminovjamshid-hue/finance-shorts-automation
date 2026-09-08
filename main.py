import os
import sys
import logging
import requests
from typing import Optional, Dict, Any, List
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Default Configuration Constants
DEFAULT_DIFY_BASE_URL = os.getenv("DIFY_BASE_URL", "https://dify.ai")
DEFAULT_DIFY_API_KEY = os.getenv("DIFY_API_KEY", "app-P0OifMZDIFvzd2wDH8ma6qUX")
DEFAULT_PEXELS_API_KEY = os.getenv(
    "PEXELS_API_KEY",
    "7PrWdMyTP1VkRWbvi5ibWOrgmo9r4nuU61KNZ5cFnxjKGlvwYywRmrFv"
)
PEXELS_API_URL = "https://api.pexels.com/videos/search"
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


def download_background_videos(
    keywords: str = "finance business money",
    output_dir: str = "downloaded_videos",
    max_videos: int = 3,
    api_key: str = DEFAULT_PEXELS_API_KEY
) -> List[str]:
    """
    Queries the Pexels Video API for high-quality, vertical (9:16 portrait) videos
    based on keywords and downloads them locally.

    :param keywords: Search terms for background videos (e.g., 'finance', 'business').
    :param output_dir: Directory where video files will be saved.
    :param max_videos: Maximum number of video clips to fetch and download.
    :param api_key: Pexels API key.
    :return: List of file paths to the downloaded video files.
    """
    headers = {"Authorization": api_key}
    params = {
        "query": keywords,
        "orientation": "portrait",
        "per_page": max_videos,
        "size": "medium"
    }

    logger.info(f"Searching Pexels Video API for vertical videos matching: '{keywords}'")

    os.makedirs(output_dir, exist_ok=True)
    downloaded_files = []

    try:
        response = requests.get(PEXELS_API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        videos = data.get("videos", [])
        if not videos:
            logger.warning(f"No vertical videos found on Pexels for query: '{keywords}'")
            return downloaded_files

        for idx, video in enumerate(videos):
            video_files = video.get("video_files", [])
            # Select best vertical HD video file
            hd_files = [f for f in video_files if f.get("quality") == "hd"] or video_files
            if not hd_files:
                continue

            download_url = hd_files[0].get("link")
            if not download_url:
                continue

            file_path = os.path.join(output_dir, f"pexels_video_{idx + 1}.mp4")
            logger.info(f"Downloading Pexels video {idx + 1}/{len(videos)} from {download_url}...")

            video_data = requests.get(download_url, timeout=60)
            video_data.raise_for_status()

            with open(file_path, "wb") as f:
                f.write(video_data.content)

            downloaded_files.append(file_path)
            logger.info(f"Successfully saved background video to {file_path}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading background videos from Pexels API: {e}")
        raise

    return downloaded_files


def create_final_shorts_video(
    video_files: List[str],
    audio_file: str = "output_shorts.mp3",
    output_path: str = "final_shorts.mp4"
) -> str:
    """
    Stitches background videos together, aligns total video duration with the audio length,
    overlays audio track, and renders the final vertical video (final_shorts.mp4).

    :param video_files: List of file paths to background video clips.
    :param audio_file: Path to voiceover audio file (output_shorts.mp3).
    :param output_path: Path where rendered final video will be saved (final_shorts.mp4).
    :return: Output path of rendered video.
    """
    if not video_files:
        raise ValueError("No video files provided to create final shorts video.")

    if not os.path.exists(audio_file):
        logger.warning(f"Audio file '{audio_file}' not found. Cannot render final video.")
        raise FileNotFoundError(f"Audio file '{audio_file}' does not exist.")

    logger.info(f"Loading audio track from {audio_file}...")
    audio_clip = AudioFileClip(audio_file)
    target_duration = audio_clip.duration

    logger.info(f"Target video duration to match audio: {target_duration:.2f} seconds")

    clips = []
    current_duration = 0.0

    # Load video clips until target duration is reached
    for file in video_files:
        if current_duration >= target_duration:
            break
        clip = VideoFileClip(file)
        clips.append(clip)
        current_duration += clip.duration

    if not clips:
        raise ValueError("Failed to load valid video clips.")

    # Stitch video clips
    concatenated_video = concatenate_videoclips(clips, method="compose")

    # Trim or loop video to match exact audio duration
    if concatenated_video.duration > target_duration:
        final_video = concatenated_video.subclipped(0, target_duration)
    else:
        # Loop if total clip duration is less than audio
        loops_needed = int(target_duration // concatenated_video.duration) + 1
        looped_clips = [concatenated_video] * loops_needed
        final_video = concatenate_videoclips(looped_clips, method="compose").subclipped(0, target_duration)

    # Attach audio clip
    final_video = final_video.with_audio(audio_clip)

    logger.info(f"Rendering final short video to {output_path}...")
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        logger=None
    )

    logger.info(f"Final shorts video rendered successfully: {output_path}")

    # Close clips to release resources
    final_video.close()
    audio_clip.close()
    for c in clips:
        c.close()

    return output_path


def run_automation_pipeline(topic: str = DEFAULT_TOPIC) -> Dict[str, Any]:
    """
    Executes the full Smart Financial Automation pipeline:
    1. Triggers Dify Chatflow with topic.
    2. Receives and extracts finalized script from Dify ANSWER block.
    3. Passes script to voiceover generator placeholder.
    4. Downloads background videos from Pexels API.
    5. Stitches videos and audio to produce final_shorts.mp4 (if audio present).

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

    # Step 5: Visual Engine - Download background videos from Pexels API
    video_files = []
    final_video_path = None
    try:
        keywords = f"{topic} finance business money"
        video_files = download_background_videos(keywords=keywords)

        # Step 6: Render final video if audio file exists
        if os.path.exists("output_shorts.mp3"):
            final_video_path = create_final_shorts_video(
                video_files=video_files,
                audio_file="output_shorts.mp3",
                output_path="final_shorts.mp4"
            )
    except Exception as e:
        logger.warning(f"Visual engine execution skipped or failed: {e}")

    return {
        "topic": topic,
        "script": script_text,
        "voiceover": voiceover_result,
        "video_files": video_files,
        "final_video_path": final_video_path
    }


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOPIC
    try:
        results = run_automation_pipeline(topic=topic)
        print("\nAutomation Pipeline Completed Successfully!")
        print(f"Topic: {results['topic']}")
        print(f"Script Preview: {results['script'][:100]}...")
        print(f"Downloaded Videos: {len(results['video_files'])}")
        if results.get('final_video_path'):
            print(f"Final Video: {results['final_video_path']}")
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
