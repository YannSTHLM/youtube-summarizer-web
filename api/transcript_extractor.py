"""
Transcript Extractor Module
Handles extracting transcripts from YouTube videos with multiple fallback methods
"""

import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

logger = logging.getLogger(__name__)


class TranscriptExtractor:
    """Extracts transcripts from YouTube videos with fallback to yt-dlp"""
    
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
        
        Tries in order:
        1. youtube-transcript-api with preferred languages
        2. youtube-transcript-api with any available language
        3. yt-dlp fallback (for auto-generated captions)
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Full transcript as a string, or None if not available
        """
        # Method 1: youtube-transcript-api with preferred languages
        try:
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=self.languages
            )
            
            full_transcript = self._combine_transcript_segments(transcript)
            logger.info(f"Successfully extracted transcript for video {video_id} "
                       f"({len(full_transcript)} characters)")
            return full_transcript
            
        except TranscriptsDisabled:
            logger.warning(f"Transcripts are disabled for video {video_id}")
            # Try yt-dlp fallback immediately
            return self._get_transcript_via_ytdlp(video_id)
            
        except NoTranscriptFound:
            logger.warning(f"No transcript found for video {video_id} "
                          f"in languages: {self.languages}")
            # Method 2: try any available transcript
            result = self._try_any_transcript(video_id)
            if result:
                return result
            # Method 3: yt-dlp fallback
            return self._get_transcript_via_ytdlp(video_id)
            
        except VideoUnavailable:
            logger.error(f"Video {video_id} is unavailable")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting transcript for video {video_id}: {e}")
            return self._get_transcript_via_ytdlp(video_id)
    
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
    
    def _get_transcript_via_ytdlp(self, video_id: str) -> Optional[str]:
        """
        Fallback: extract transcript using yt-dlp.
        
        yt-dlp uses a different mechanism to access captions and can often
        retrieve auto-generated transcripts that youtube-transcript-api cannot.
        """
        try:
            import yt_dlp
        except ImportError:
            logger.debug("yt-dlp not installed, skipping fallback")
            return None
        
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            ydl_opts = {
                'skip_download': True,
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Attempting yt-dlp fallback for video {video_id}")
                info = ydl.extract_info(url, download=False)
                
                # Try manual subtitles first, then auto-generated captions
                for sub_key in ['subtitles', 'automatic_captions']:
                    subs = info.get(sub_key, {})
                    if not subs:
                        continue
                    
                    is_auto = sub_key == 'automatic_captions'
                    
                    # Try preferred languages
                    result = self._try_sub_langs(subs, video_id, is_auto)
                    if result:
                        return result
                
                logger.warning(f"yt-dlp: No subtitles found for video {video_id}")
                return None
                
        except Exception as e:
            logger.debug(f"yt-dlp fallback failed for video {video_id}: {e}")
            return None
    
    def _try_sub_langs(self, subs: dict, video_id: str, is_auto: bool) -> Optional[str]:
        """Try to fetch subtitles from a yt-dlp subtitle dict, preferring certain languages"""
        import urllib.request
        
        # Build priority list: preferred langs, then any 'en' variant, then any
        lang_order = []
        for lang in self.languages:
            if lang in subs:
                lang_order.append(lang)
        for lang in subs:
            if lang.startswith('en') and lang not in lang_order:
                lang_order.append(lang)
        for lang in subs:
            if lang not in lang_order:
                lang_order.append(lang)
        
        for lang in lang_order:
            lang_subs = subs.get(lang, [])
            if not lang_subs:
                continue
            
            # Prefer json3 (easy to parse), then srv1 (XML), then vtt
            for fmt in ['json3', 'srv1', 'vtt', 'ttml']:
                sub = next((s for s in lang_subs if s.get('ext') == fmt), None)
                if sub and sub.get('url'):
                    sub_type = "auto-generated" if is_auto else "manual"
                    logger.info(f"yt-dlp: Fetching {sub_type} subtitle "
                               f"(lang={lang}, format={fmt}) for video {video_id}")
                    try:
                        with urllib.request.urlopen(sub['url']) as response:
                            content = response.read().decode('utf-8')
                        text = self._parse_subtitle_content(content, fmt)
                        if text and len(text.strip()) > 20:
                            logger.info(f"yt-dlp: Successfully extracted transcript "
                                       f"({len(text)} characters) for video {video_id}")
                            return text
                    except Exception as e:
                        logger.debug(f"yt-dlp: Failed to fetch/parse {fmt} subtitle: {e}")
                        continue
        
        return None
    
    def _parse_subtitle_content(self, content: str, fmt: str) -> Optional[str]:
        """Parse subtitle content based on format"""
        try:
            if fmt == 'json3':
                data = json.loads(content)
                segments = []
                for event in data.get('events', []):
                    segs = event.get('segs', [])
                    text = ''.join(s.get('utf8', '') for s in segs)
                    text = text.strip()
                    if text and text != '\n':
                        segments.append(text.replace('\n', ' '))
                return ' '.join(segments)
            
            elif fmt == 'srv1':
                root = ET.fromstring(content)
                texts = root.findall('.//text')
                segments = []
                for t in texts:
                    if t.text:
                        segments.append(t.text.replace('\n', ' '))
                return ' '.join(segments)
            
            elif fmt == 'vtt':
                lines = content.split('\n')
                text_lines = []
                for line in lines:
                    # Skip header, timestamps, empty lines, cue identifiers
                    if ('-->' in line or line.startswith('WEBVTT') or 
                        line.startswith('Kind:') or line.startswith('Language:') or
                        not line.strip()):
                        continue
                    # Strip HTML tags
                    clean = re.sub(r'<[^>]+>', '', line).strip()
                    if clean:
                        text_lines.append(clean)
                return ' '.join(text_lines)
            
            else:
                # Generic: strip all tags
                clean = re.sub(r'<[^>]+>', ' ', content)
                clean = re.sub(r'\s+', ' ', clean).strip()
                return clean if clean else None
                
        except Exception as e:
            logger.debug(f"Error parsing subtitle content ({fmt}): {e}")
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
            for _ in transcript_list:
                return True
            return False
        except Exception:
            return False