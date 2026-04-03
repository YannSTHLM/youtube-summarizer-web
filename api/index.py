"""
YouTube Transcript Summarizer - FastAPI Backend
Designed for Vercel serverless deployment
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import our modules (copy from CLI version)
from .youtube_fetcher import YouTubeFetcher
from .transcript_extractor import TranscriptExtractor
from .summarizer import TranscriptSummarizer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="YouTube Transcript Summarizer")

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChannelRequest(BaseModel):
    channels: List[str]

class VideoSummary(BaseModel):
    video_id: str
    title: str
    url: str
    channel_name: str
    published_at: str
    summary: Optional[str] = None
    error: Optional[str] = None

class ProcessResponse(BaseModel):
    success: bool
    message: str
    videos: List[VideoSummary]
    stats: dict

# Global state for tracking processing
processing_state = {
    "is_processing": False,
    "current_channel": "",
    "progress": 0,
    "total": 0,
    "videos_processed": []
}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "YouTube Transcript Summarizer API", "status": "running"}


@app.post("/api/process", response_model=ProcessResponse)
async def process_channels(request: ChannelRequest):
    """
    Process YouTube channels and generate summaries
    """
    global processing_state
    
    try:
        # Get API keys from environment
        youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        zai_api_key = os.getenv('ZAI_API_KEY')
        
        if not youtube_api_key:
            raise HTTPException(status_code=500, detail="YouTube API key not configured")
        if not zai_api_key:
            raise HTTPException(status_code=500, detail="Z.ai API key not configured")
        
        # Initialize components
        youtube_fetcher = YouTubeFetcher(youtube_api_key)
        transcript_extractor = TranscriptExtractor()
        summarizer = TranscriptSummarizer(
            api_key=zai_api_key,
            model=os.getenv('ZAI_MODEL', 'glm-4-flash'),
            max_tokens=int(os.getenv('MAX_SUMMARY_TOKENS', '500'))
        )
        
        # Update processing state
        processing_state["is_processing"] = True
        processing_state["total"] = len(request.channels)
        processing_state["progress"] = 0
        processing_state["videos_processed"] = []
        
        all_videos = []
        stats = {
            "channels_processed": 0,
            "videos_found": 0,
            "summaries_generated": 0,
            "errors": 0
        }
        
        # Process each channel
        for channel_input in request.channels:
            try:
                processing_state["current_channel"] = channel_input
                
                # Extract channel ID
                channel_id = youtube_fetcher.extract_channel_id(channel_input)
                
                # Get channel info
                channel_info = youtube_fetcher.get_channel_info(channel_id)
                channel_name = channel_info['title'] if channel_info else channel_id
                
                # Get today's videos
                videos = youtube_fetcher.get_today_videos(channel_id, max_videos=10)
                
                if not videos:
                    logger.info(f"No videos today from {channel_name}")
                    processing_state["progress"] += 1
                    continue
                
                stats["videos_found"] += len(videos)
                
                # Process each video
                for video in videos:
                    try:
                        # Extract transcript - try auto-generated first
                        transcript = transcript_extractor.get_auto_generated_transcript(video['id'])
                        
                        # If no auto-generated, try general method (manual or any available)
                        if not transcript:
                            transcript = transcript_extractor.get_transcript(video['id'])
                        
                        if not transcript:
                            video_summary = VideoSummary(
                                video_id=video['id'],
                                title=video['title'],
                                url=video['url'],
                                channel_name=channel_name,
                                published_at=video['published_at'],
                                error="No transcript available"
                            )
                            all_videos.append(video_summary)
                            continue
                        
                        # Generate summary
                        summary = summarizer.summarize(transcript, video['title'])
                        
                        if summary:
                            stats["summaries_generated"] += 1
                            video_summary = VideoSummary(
                                video_id=video['id'],
                                title=video['title'],
                                url=video['url'],
                                channel_name=channel_name,
                                published_at=video['published_at'],
                                summary=summary
                            )
                        else:
                            video_summary = VideoSummary(
                                video_id=video['id'],
                                title=video['title'],
                                url=video['url'],
                                channel_name=channel_name,
                                published_at=video['published_at'],
                                error="Failed to generate summary"
                            )
                            stats["errors"] += 1
                        
                        all_videos.append(video_summary)
                        processing_state["videos_processed"].append(video_summary.dict())
                        
                    except Exception as e:
                        logger.error(f"Error processing video {video['title']}: {e}")
                        stats["errors"] += 1
                
                stats["channels_processed"] += 1
                processing_state["progress"] += 1
                
            except Exception as e:
                logger.error(f"Error processing channel {channel_input}: {e}")
                stats["errors"] += 1
                processing_state["progress"] += 1
        
        # Mark processing as complete
        processing_state["is_processing"] = False
        
        return ProcessResponse(
            success=True,
            message=f"Processed {stats['channels_processed']} channels, "
                    f"found {stats['videos_found']} videos, "
                    f"generated {stats['summaries_generated']} summaries",
            videos=all_videos,
            stats=stats
        )
        
    except Exception as e:
        processing_state["is_processing"] = False
        logger.error(f"Error in process_channels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """Get current processing status"""
    return processing_state


@app.get("/api/config/check")
async def check_config():
    """Check if API keys are configured"""
    youtube_key = os.getenv('YOUTUBE_API_KEY')
    zai_key = os.getenv('ZAI_API_KEY')
    
    return {
        "youtube_configured": bool(youtube_key and youtube_key != 'your_youtube_api_key_here'),
        "openai_configured": bool(zai_key and zai_key != 'your_zai_api_key_here')
    }


# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)