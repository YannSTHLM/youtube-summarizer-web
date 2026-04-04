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

logger = logging.getLogger(__name__)


class TranscriptExtractor:
    """Extracts transcripts from YouTube videos with multiple fallback methods"""
    
    _BROWSER_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    def __init__(self, languages: List[str] = None):
        self.languages = languages or ['en', 'en-US', 'en-GB']
    
    def get_transcript(self, video_id: str) -> Optional[str]:
        """
        Get transcript for a YouTube video.
        
        Tries in order:
        1. youtube-transcript-api fetch with preferred languages
        2. youtube-transcript-api list + fetch any available
        3. Page scraping fallback
        """
        ytt = YouTubeTranscriptApi()
        
        # Method 1: youtube-transcript-api fetch with preferred languages
        try:
            transcript = ytt.fetch(video_id, languages=self.languages)
            text = self._extract_text(transcript)
            if text:
                logger.info(f"Got transcript via API fetch for {video_id} ({len(text)} chars)")
                return text
        except Exception as e:
            logger.warning(f"API fetch failed for {video_id}: {type(e).__name__}: {e}")
        
        # Method 2: list all transcripts and try each
        try:
            transcript_list = ytt.list(video_id)
            for snippet in transcript_list:
                logger.info(f"Found track: {snippet.language} (generated={snippet.is_generated})")
            for snippet in transcript_list:
                try:
                    fetched = snippet.fetch()
                    text = self._extract_text(fetched)
                    if text:
                        logger.info(f"Got transcript via list for {video_id} ({len(text)} chars)")
                        return text
                except Exception as fe:
                    logger.warning(f"Failed to fetch {snippet.language}: {fe}")
                    continue
        except Exception as e:
            logger.warning(f"API list failed for {video_id}: {type(e).__name__}: {e}")
        
        # Method 3: Page scraping fallback
        return self._get_transcript_via_scraping(video_id)
    
    def _extract_text(self, transcript) -> str:
        """Extract text from transcript result (handles different return types)"""
        # FetchedTranscript object with .snippets attribute (v1.x API)
        if hasattr(transcript, 'snippets'):
            snippets = transcript.snippets
            text = ' '.join(
                s.text for s in snippets if hasattr(s, 'text')
            )
            return text.strip() if text else ''
        
        if isinstance(transcript, str):
            return transcript.strip()
        
        if isinstance(transcript, list):
            segments = []
            for seg in transcript:
                if isinstance(seg, dict):
                    segments.append(seg.get('text', ''))
                elif hasattr(seg, 'text'):
                    segments.append(seg.text)
                elif isinstance(seg, str):
                    segments.append(seg)
            result = ' '.join(segments)
            return result.strip() if result.strip() else ''
        
        if hasattr(transcript, 'text'):
            return transcript.text.strip() if transcript.text else ''
        
        return str(transcript).strip()
    
    def _get_transcript_via_scraping(self, video_id: str) -> Optional[str]:
        """Fallback: scrape YouTube page for caption URLs"""
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        try:
            req = urllib.request.Request(url, headers=self._BROWSER_HEADERS)
            logger.info(f"Scraping YouTube page for captions: {video_id}")
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
        except Exception as e:
            logger.warning(f"Failed to fetch page for {video_id}: {e}")
            return None
        
        # Extract player response
        player_response = self._extract_player_response(html, video_id)
        if not player_response:
            return None
        
        # Get caption tracks
        captions_data = player_response.get('captions', {})
        caption_tracks = captions_data.get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
        
        if not caption_tracks:
            logger.warning(f"No caption tracks found for {video_id}")
            return None
        
        logger.info(f"Found {len(caption_tracks)} caption tracks for {video_id}")
        
        # Prioritize and try each track
        prioritized = sorted(caption_tracks, key=self._track_score)
        
        for track in prioritized:
            track_url = track.get('baseUrl')
            lang = track.get('languageCode', 'unknown')
            kind = track.get('kind', 'manual')
            
            if not track_url:
                continue
            
            logger.info(f"Trying caption track: lang={lang}, kind={kind}")
            
            try:
                fmt_url = track_url + '&fmt=json3'
                req = urllib.request.Request(fmt_url, headers=self._BROWSER_HEADERS)
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read().decode('utf-8')
                
                text = self._parse_json3(content)
                if text and len(text.strip()) > 20:
                    logger.info(f"Got transcript via scraping ({len(text)} chars) for {video_id}")
                    return text
            except Exception as e:
                logger.debug(f"json3 failed for {lang}: {e}")
            
            try:
                fmt_url = track_url + '&fmt=srv1'
                req = urllib.request.Request(fmt_url, headers=self._BROWSER_HEADERS)
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read().decode('utf-8')
                
                text = self._parse_srv1(content)
                if text and len(text.strip()) > 20:
                    logger.info(f"Got transcript via srv1 ({len(text)} chars) for {video_id}")
                    return text
            except Exception as e:
                logger.debug(f"srv1 failed for {lang}: {e}")
        
        logger.warning(f"All caption tracks failed for {video_id}")
        return None
    
    def _extract_player_response(self, html: str, video_id: str) -> Optional[dict]:
        """Extract ytInitialPlayerResponse from YouTube page"""
        patterns = [
            r'ytInitialPlayerResponse\s*=\s*(\{.+?\});',
            r'var\s+ytInitialPlayerResponse\s*=\s*(\{.+?\});',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if 'captions' in data or 'videoDetails' in data:
                        return data
                except json.JSONDecodeError:
                    continue
        
        logger.warning(f"Could not extract player response for {video_id}")
        return None
    
    def _track_score(self, track):
        """Score a caption track for priority sorting"""
        lang = track.get('languageCode', '')
        kind = track.get('kind', '')
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
    
    def _parse_json3(self, content: str) -> Optional[str]:
        """Parse JSON3 subtitle format"""
        try:
            data = json.loads(content)
            segments = []
            for event in data.get('events', []):
                segs = event.get('segs', [])
                text = ''.join(s.get('utf8', '') for s in segs).strip()
                if text and text != '\n':
                    segments.append(text.replace('\n', ' '))
            return ' '.join(segments)
        except Exception as e:
            logger.debug(f"Error parsing json3: {e}")
            return None
    
    def _parse_srv1(self, content: str) -> Optional[str]:
        """Parse srv1 (XML) subtitle format"""
        try:
            root = ET.fromstring(content)
            segments = []
            for t in root.findall('.//text'):
                if t.text:
                    segments.append(t.text.replace('\n', ' '))
            return ' '.join(segments)
        except Exception as e:
            logger.debug(f"Error parsing srv1: {e}")
            return None