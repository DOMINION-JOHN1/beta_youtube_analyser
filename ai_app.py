import os
import json
from dotenv import load_dotenv
from serpapi import GoogleSearch 
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi
from gtts import gTTS
import re


# Initialize clients
load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
serpapi_key = os.getenv("SERPAPI_API_KEY")
# api_key = os.getenv("GROQ_API_KEY")

#Helper functions
def extract_videoid(url: str) -> str:
    """Extract YouTube video ID from URL"""
    regex = r"(?:v=|/)([0-9A-Za-z-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

#Core functionality
def search_youtube_video(query: str) -> dict:
    """Search YouTube videos using SerpAPI"""
    params = {
        "engine": "youtube",
        "search_query": query,
        "api_key": serpapi_key
    }

    try:
        results = GoogleSearch(params).get_dict()
        video = results.get("video_results", [{}])[0]
        return {
            "title": video.get("title"),
            "link": video.get("link"),
            "channel": video.get("channel").get("name") if video.get("channel") else None
        }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

def get_video_transcript(video_id: str) -> str:
    """Get YouTube video transcript"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry["text"] for entry in transcript])
    except Exception as e:
        return f"Transcript error: {str(e)}"
    
def generate_summary(text: str) -> str:
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
        temperature=0.3)
    return response.choices[0].message.content

def text_to_speech(text: str, filename: str = "summary.mp3"):
    """Convert text summary to speech"""
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(filename)
    return filename

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
                    "query": {"type": "string", "description": "Search query or video title"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_summary",
            "description": "Generate detailed summary from text content",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text content to summarize"}
                },
                "required": ["text"]
            }
        }
    }
]


def analyze_video(prompt: str, tts: bool = False) -> dict:
    """Main analysis workflow"""
    # Step 1: Find video
    search_result = search_youtube_video(prompt)
    if "error" in search_result:
        return {"error": search_result["error"]}

#Step 2: Get transcript
    video_id = extract_videoid(search_result["link"])
    transcript = get_video_transcript(video_id)

#Step 3: Generate summary
    summary = generate_summary(transcript)

#Step 4: Optional TTS
    if tts:
        audio_file = text_to_speech(summary)

    return {
        "title": search_result["title"],
        "link": search_result["link"],
        "channel": search_result["channel"],
        "summary": summary,
        "audio": audio_file
    }

# I did an example usage so you can see the workflow and easily implement it 
if __name__ == "__main__":
    analysis = analyze_video(
        "Love in Every Word (Odogwu Paranra) by Omoni Oboli",
        tts=True
    )

    print(f"Title: {analysis['title']}")
    print(f"Channel: {analysis['channel']}")
    print(f"Link: {analysis['link']}")
    print("\nSummary:")
    print(analysis['summary'])
    print(f"\nAudio summary saved to: {analysis['audio']}")