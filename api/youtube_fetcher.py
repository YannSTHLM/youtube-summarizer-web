"""
YouTube Data Fetcher Module
Handles fetching video metadata from YouTube channels
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class YouTubeFetcher:
    """Fetches video data from YouTube channels"""
    
    def __init__(self, api_key: str):
        """Initialize YouTube API client"""
        self.youtube = build('youtube', 'v3', developerKey=api_key)
    
    def extract_channel_id(self, channel_input: str) -> str:
        """
        Extract channel ID from various input formats
        Handles: channel ID (UC...), @username, or full URL
        """
        if channel_input.startswith('UC'):
            return channel_input
        
        if 'youtube.com' in channel_input:
            # Handle URLs like https://www.youtube.com/@username
            # or https://www.youtube.com/channel/UC...
            if '/channel/' in channel_input:
                return channel_input.split('/channel/')[-1].split('/')[0]
            elif '/@' in channel_input:
                username = channel_input.split('/@')[-1].split('/')[0]
                return self._get_channel_id_by_username(username)
        
        # Handle @username format
        if channel_input.startswith('@'):
            username = channel_input[1:]
            return self._get_channel_id_by_username(username)
        
        return channel_input
    
    def _get_channel_id_by_username(self, username: str) -> str:
        """Get channel ID from username/handle"""
        try:
            response = self.youtube.search().list(
                part='snippet',
                q=username,
                type='channel',
                maxResults=1
            ).execute()
            
            if response['items']:
                return response['items'][0]['snippet']['channelId']
            else:
                raise ValueError(f"Channel not found: @{username}")
        except HttpError as e:
            logger.error(f"Error fetching channel ID for @{username}: {e}")
            raise
    
    def get_today_videos(self, channel_id: str, max_videos: int = 50) -> List[Dict]:
        """
        Fetch videos uploaded today from a channel
        
        Args:
            channel_id: YouTube channel ID
            max_videos: Maximum number of videos to fetch
            
        Returns:
            List of video dictionaries with id, title, url, published_at
        """
        videos = []
        
        try:
            # Calculate time range for today
            today = datetime.utcnow().date()
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = datetime.combine(today + timedelta(days=1), datetime.min.time())
            
            # Get channel's uploads playlist
            channel_response = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()
            
            if not channel_response['items']:
                logger.warning(f"Channel not found: {channel_id}")
                return videos
            
            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Fetch videos from uploads playlist
            next_page_token = None
            
            while len(videos) < max_videos:
                playlist_response = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=uploads_playlist_id,
                    maxResults=min(50, max_videos - len(videos)),
                    pageToken=next_page_token
                ).execute()
                
                for item in playlist_response['items']:
                    published_at = datetime.fromisoformat(
                        item['snippet']['publishedAt'].replace('Z', '+00:00')
                    )
                    
                    # Check if video was published today
                    if start_of_day <= published_at.replace(tzinfo=None) < end_of_day:
                        video_id = item['snippet']['resourceId']['videoId']
                        videos.append({
                            'id': video_id,
                            'title': item['snippet']['title'],
                            'url': f'https://www.youtube.com/watch?v={video_id}',
                            'published_at': published_at.isoformat(),
                            'channel_title': item['snippet'].get('channelTitle', 'Unknown'),
                            'description': item['snippet'].get('description', '')[:200]
                        })
                    elif published_at.replace(tzinfo=None) < start_of_day:
                        # Videos are in reverse chronological order
                        # If we've gone past today, we can stop
                        break
                
                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token:
                    break
            
            logger.info(f"Found {len(videos)} videos uploaded today from channel {channel_id}")
            
        except HttpError as e:
            logger.error(f"Error fetching videos for channel {channel_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error for channel {channel_id}: {e}")
        
        return videos
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict]:
        """Get channel information"""
        try:
            response = self.youtube.channels().list(
                part='snippet',
                id=channel_id
            ).execute()
            
            if response['items']:
                snippet = response['items'][0]['snippet']
                return {
                    'id': channel_id,
                    'title': snippet['title'],
                    'description': snippet.get('description', '')[:200]
                }
        except HttpError as e:
            logger.error(f"Error fetching channel info: {e}")
        
        return None