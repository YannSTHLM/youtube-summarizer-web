"""
Transcript Extractor Module
Handles extracting transcripts from YouTube videos with multiple fallback methods
"""

import json
import logging
import re
import urllib.request
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
    """Extracts transcripts from YouTube videos with multiple fallback methods"""
    
    # Browser-like headers to avoid bot detection when scraping
    _BROWSER_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
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
                languages=self.languages,
                format="text"
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
        Fallback: extract transcript by scraping YouTube page directly.
        
        Scrapes the video page HTML to extract caption URLs from the embedded
        player config (ytInitialPlayerResponse). Works in serverless environments
        without browser cookies.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Step 1: Fetch the video page with browser-like headers
        try:
            req = urllib.request.Request(url, headers=self._BROWSER_HEADERS)
            logger.info(f"Scraping YouTube page for caption URLs: {video_id}")
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
        except Exception as e:
            logger.warning(f"Failed to fetch YouTube page for {video_id}: {e}")
            return None
        
        # Step 2: Extract ytInitialPlayerResponse from the page
        player_response = self._extract_player_response(html, video_id)
        if not player_response:
            return None
        
        # Step 3: Get caption tracks from player response
        captions_data = player_response.get('captions', {})
        caption_tracks = captions_data.get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
        
        if not caption_tracks:
            logger.warning(f"No caption tracks found in page data for {video_id}")
            return None
        
        logger.info(f"Found {len(caption_tracks)} caption tracks for {video_id}")
        
        # Step 4: Prioritize tracks by language preference
        prioritized = self._prioritize_tracks(caption_tracks)
        
        # Step 5: Try each track
        for track in prioritized:
            track_url = track.get('baseUrl')
            lang = track.get('languageCode', 'unknown')
            kind = track.get('kind', 'manual')
            is_auto = kind == 'asr'
            
            if not track_url:
                continue
            
            track_type = "auto-generated" if is_auto else "manual"
            logger.info(f"Fetching {track_type} caption (lang={lang}) for {video_id}")
            
            try:
                # Request JSON3 format for easier parsing
                fmt_url = track_url + '&fmt=json3'
                req = urllib.request.Request(fmt_url, headers=self._BROWSER_HEADERS)
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read().decode('utf-8')
                
                text = self._parse_subtitle_content(content, 'json3')
                if text and len(text.strip()) > 20:
                    logger.info(f"Successfully extracted {track_type} transcript "
                               f"({len(text)} chars) for {video_id}")
                    return text
            except Exception as e:
                logger.debug(f"Failed to fetch/parse caption track (lang={lang}): {e}")
                # Try srv1 format as fallback
                try:
                    fmt_url = track_url + '&fmt=srv1'
                    req = urllib.request.Request(fmt_url, headers=self._BROWSER_HEADERS)
                    with urllib.request.urlopen(req, timeout=10) as response:
                        content = response.read().decode('utf-8')
                    
                    text = self._parse_subtitle_content(content, 'srv1')
                    if text and len(text.strip()) > 20:
                        logger.info(f"Successfully extracted {track_type} transcript "
                                   f"via srv1 ({len(text)} chars) for {video_id}")
                        return text
                except Exception as e2:
                    logger.debug(f"srv1 fallback also failed: {e2}")
                    continue
        
        logger.warning(f"All caption tracks failed for {video_id}")
        return None
    
    def _extract_player_response(self, html: str, video_id: str) -> Optional[dict]:
        """Extract ytInitialPlayerResponse from YouTube page HTML"""
        # Try multiple patterns YouTube uses to embed player data
        patterns = [
            r'ytInitialPlayerResponse\s*=\s*(\{.+?\});',
            r'ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;',
            r'var\s+ytInitialPlayerResponse\s*=\s*(\{.+?\});',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if 'captions' in data or 'videoDetails' in data:
                        logger.info(f"Extracted player response for {video_id}")
                        return data
                except json.JSONDecodeError:
                    continue
        
        # Fallback: try to find captions in ytInitialData
        match = re.search(r'ytInitialData\s*=\s*(\{.+?\});', html)
        if match:
            try:
                data = json.loads(match.group(1))
                # Look for captions in the embedded player response
                player_response = data.get('playerResponse', {})
                if isinstance(player_response, str):
                    player_response = json.loads(player_response)
                if 'captions' in player_response:
                    return player_response
            except (json.JSONDecodeError, TypeError):
                pass
        
        logger.warning(f"Could not extract player response from page for {video_id}")
        return None
    
    def _prioritize_tracks(self, tracks: list) -> list:
        """Sort caption tracks by language preference"""
        def track_score(track):
            lang = track.get('languageCode', '')
            kind = track.get('kind', '')
            
            # Prefer non-ASR (manual) tracks, then ASR
            is_asr = kind == 'asr'
            
            if lang in self.languages and not is_asr:
                return (0, self.languages.index(lang))
            elif lang in self.languages:
                return (1, self.languages.index(lang))
            elif lang.startswith('en') and not is_asr:
                return (2, 0)
            elif lang.startswith('en'):
                return (3, 0)
            elif not is_asr:
                return (4, 0)
            else:
                return (5, 0)
        
        return sorted(tracks, key=track_score)
    
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