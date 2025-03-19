from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os

from src.ai_app import analyze_video

# Initialize FastAPI app
app = FastAPI(title="AI Budget Generator", version="1.0")


class VideoRequestQuery(BaseModel):
    user_query: str


# Health check endpoint
@app.get("/")
def read_root():
    return {"message": "AI Youtube Video Summary API is running."}


@app.post("/summarize")
def get_video_summary(video_request: VideoRequestQuery):
    analysis = analyze_video(video_request.user_query)
    return JSONResponse(analysis)


# Endpoint to download audio summary
@app.get("/download-audio/{file_name}")
async def download_file(file_name: str):
    file_path = f"static/{file_name}"
    return FileResponse(file_path)
