import os
import json
from dotenv import load_dotenv
from serpapi import GoogleSearch
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
from gtts import gTTS
import re
from datetime import datetime
import threading


# Initialize clients
load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
serpapi_key = os.getenv("SERPAPI_API_KEY")

app_domain = os.getenv("APP_DOMAIN")


# Helper functions
def extract_videoid(url: str) -> str:
    print("extracting videoId, video url...", url)
    """Extract YouTube video ID from URL"""
    regex = r"(?:v=|/)([0-9A-Za-z-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None


# Core functionality
def search_youtube_video(query: str) -> dict:
    print("searching video result...", query, "\n")
    """Search YouTube videos using SerpAPI"""
    params = {"engine": "youtube", "search_query": query, "api_key": serpapi_key}

    try:
        results = GoogleSearch(params).get_dict()
        video = results.get("video_results", [{}])[0]
        return {
            "title": video.get("title"),
            "link": video.get("link"),
            "channel": (
                video.get("channel").get("name") if video.get("channel") else None
            ),
            # "video_id": video.get("")
        }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}


def get_video_transcript(video_id: str) -> str:
    print("getting video transcript...", video_id, "\n")
    """Get YouTube video transcript"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry["text"] for entry in transcript])
    except Exception as e:
        return f"Transcript error: {str(e)}"


def generate_summary(text: str) -> str:
    print("generating video summary...")
    """Generate AI summary using Llama"""
    prompt = f"""Analyze this video transcript and create a detailed summary including:
    
    Core message and key themes
    Main storyline/plot points
    Emotional tone and sentiment
    Notable characters/participants
    Key takeaways

    Transcript: {text[:6000]}"""  # Token limit management

    response = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content


def text_to_speech(text: str, filename: str = "summary"):
    print("converting summary to speech...", "\n\n")
    """Convert text summary to speech"""

    # Ensure the 'static' directory exists
    os.makedirs("static", exist_ok=True)

    tts = gTTS(text=text, lang="en", slow=False)
    audio_path = f"static/{filename}.mp3"
    tts.save(audio_path)
    return audio_path


# Function to trigger TTS in a separate thread
def async_text_to_speech(summary: str, filename: str):
    threading.Thread(
        target=text_to_speech, args=(summary, filename), daemon=True
    ).start()


# Function calling setup
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_youtube_video",
            "description": "Search YouTube videos by title or description",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query or video title",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_summary",
            "description": "Generate detailed summary from text content",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text content to summarize",
                    }
                },
                "required": ["text"],
            },
        },
    },
]


def analyze_video(prompt: str, tts: bool = False) -> dict:
    """Main analysis workflow"""
    # Step 1: Find video
    search_result = search_youtube_video(prompt)
    if "error" in search_result:
        return {"error": search_result["error"]}
    print("video search result...", search_result, "\n")

    # Step 2: Get transcript
    video_id = extract_videoid(search_result["link"])
    transcript = get_video_transcript(video_id)

    # Step 3: Generate summary
    summary = generate_summary(transcript)

    # Step 4: Optional TTS
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{video_id}_{timestamp}" if tts else None
    if tts:
        # audio_file_path = text_to_speech(summary, filename)
        # Trigger TTS generation asynchronously
        async_text_to_speech(summary, filename)

    return {
        "title": search_result["title"],
        "link": search_result["link"],
        "channel": search_result["channel"],
        "summary": summary,
        "audio_filename": f"{filename}.mp3",
        "audio_summary_url": (
            f"{app_domain}/download-audio/{filename}.mp3" if tts else None
        ),
    }


# I did an example usage so you can see the workflow and easily implement it
if __name__ == "__main__":
    analysis = analyze_video(
        "Love in Every Word (Odogwu Paranra) by Omoni Oboli", tts=True
    )

    print(f"Title: {analysis['title']}")
    print(f"Channel: {analysis['channel']}")
    print(f"Link: {analysis['link']}")
    print("\nSummary:")
    print(analysis["summary"])
    print(f"\nAudio summary saved to: {analysis['audio']}")
