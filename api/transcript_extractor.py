"""
Transcript Extractor Module
Handles extracting transcripts from YouTube videos
"""

import logging
from typing import Optional, List, Dict
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

logger = logging.getLogger(__name__)


class TranscriptExtractor:
    """Extracts transcripts from YouTube videos"""
    
    def __init__(self, languages: List[str] = None):
        """
        Initialize transcript extractor
        
        Args:
            languages: List of language codes to try (e.g., ['en', 'en-US'])
                      Defaults to English variants
        """
        self.languages = languages or ['en', 'en-US', 'en-GB']
    
    def get_transcript(self, video_id: str) -> Optional[str]:
        """
        Get transcript for a YouTube video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Full transcript as a string, or None if not available
        """
        try:
            # Try to get transcript with preferred languages
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=self.languages
            )
            
            # Combine all transcript segments into a single text
            full_transcript = self._combine_transcript_segments(transcript)
            
            logger.info(f"Successfully extracted transcript for video {video_id} "
                       f"({len(full_transcript)} characters)")
            
            return full_transcript
            
        except TranscriptsDisabled:
            logger.warning(f"Transcripts are disabled for video {video_id}")
            return None
            
        except NoTranscriptFound:
            logger.warning(f"No transcript found for video {video_id} "
                          f"in languages: {self.languages}")
            # Try to get any available transcript
            return self._try_any_transcript(video_id)
            
        except VideoUnavailable:
            logger.error(f"Video {video_id} is unavailable")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting transcript for video {video_id}: {e}")
            return None
    
    def _try_any_transcript(self, video_id: str) -> Optional[str]:
        """
        Try to get any available transcript regardless of language
        """
        try:
            logger.info(f"Listing available transcripts for video {video_id}")
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get the first available transcript (including auto-generated)
            for transcript in transcript_list:
                try:
                    logger.info(f"Attempting to fetch transcript: language={transcript.language}, "
                               f"is_generated={transcript.is_generated}")
                    fetched = transcript.fetch()
                    full_transcript = self._combine_transcript_segments(fetched)
                    transcript_type = "auto-generated" if transcript.is_generated else "manual"
                    logger.info(f"Successfully found {transcript_type} transcript in language '{transcript.language}' "
                               f"for video {video_id} ({len(full_transcript)} chars)")
                    return full_transcript
                except Exception as e:
                    logger.warning(f"Could not fetch transcript in "
                                  f"'{transcript.language}': {type(e).__name__}: {e}")
                    continue
            
            logger.warning(f"No fetchable transcript found for video {video_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error listing transcripts for video {video_id}: {type(e).__name__}: {e}")
            return None
    
    def get_auto_generated_transcript(self, video_id: str) -> Optional[str]:
        """
        Specifically try to get auto-generated transcript
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Auto-generated transcript as a string, or None if not available
        """
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Look specifically for auto-generated transcripts
            for transcript in transcript_list:
                if transcript.is_generated:
                    try:
                        fetched = transcript.fetch()
                        full_transcript = self._combine_transcript_segments(fetched)
                        logger.info(f"Found auto-generated transcript for video {video_id}")
                        return full_transcript
                    except Exception as e:
                        logger.debug(f"Could not fetch auto-generated transcript: {e}")
                        continue
            
            logger.warning(f"No auto-generated transcript found for video {video_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting auto-generated transcript for video {video_id}: {e}")
            return None
    
    def _combine_transcript_segments(self, transcript) -> str:
        """
        Combine transcript segments into a single text
        
        Args:
            transcript: List of transcript segments (dicts or FetchedTranscriptSnippet objects)
            
        Returns:
            Combined transcript text
        """
        # youtube-transcript-api 0.6.x returns FetchedTranscriptSnippet objects
        # with .text attribute; older versions return plain dicts with ['text']
        segments = []
        for segment in transcript:
            if isinstance(segment, dict):
                segments.append(segment.get('text', ''))
            else:
                segments.append(getattr(segment, 'text', ''))
        return ' '.join(segments)
    
    def get_transcript_with_timestamps(self, video_id: str) -> Optional[List[Dict]]:
        """
        Get transcript with timestamps for a video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of transcript segments with timestamps, or None
        """
        try:
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=self.languages
            )
            return transcript
            
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
            logger.warning(f"Could not get transcript with timestamps "
                          f"for {video_id}: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting transcript with timestamps: {e}")
            return None
    
    def check_transcript_available(self, video_id: str) -> bool:
        """
        Check if a transcript is available for a video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if transcript is available, False otherwise
        """
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # Check if there's at least one transcript available
            for _ in transcript_list:
                return True
            return False
        except Exception:
            return False