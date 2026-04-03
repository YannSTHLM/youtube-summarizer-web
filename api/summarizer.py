"""
Summarizer Module
Handles AI-powered summarization of video transcripts using Z.ai
"""

import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class TranscriptSummarizer:
    """Generates AI summaries of video transcripts"""
    
    def __init__(self, api_key: str, model: str = "glm-4-flash", max_tokens: int = 500):
        """
        Initialize summarizer with Z.ai client
        
        Args:
            api_key: Z.ai API key
            model: Model to use for summarization (default: glm-4-flash)
            max_tokens: Maximum tokens for summary output
        """
        # Z.ai uses OpenAI-compatible API format
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.z.ai/api/coding/paas/v4"
        )
        self.model = model
        self.max_tokens = max_tokens
    
    def summarize(self, transcript: str, video_title: str = "") -> Optional[str]:
        """
        Generate a summary of the transcript
        
        Args:
            transcript: Full transcript text
            video_title: Title of the video (for context)
            
        Returns:
            Summary text, or None if summarization fails
        """
        if not transcript or len(transcript.strip()) < 50:
            logger.warning("Transcript too short to summarize")
            return None
        
        try:
            # Truncate transcript if too long (to avoid token limits)
            max_transcript_length = 15000  # Conservative limit
            truncated_transcript = transcript[:max_transcript_length]
            if len(transcript) > max_transcript_length:
                truncated_transcript += "\n\n[Transcript truncated due to length...]"
            
            # Create the prompt
            system_prompt = """You are a helpful assistant that summarizes YouTube video transcripts. 
            Create concise, informative summaries that capture the key points, main arguments, 
            and important details from the video. Use clear, well-structured language.
            Include bullet points for key takeaways when appropriate."""
            
            user_prompt = f"""Please summarize the following YouTube video transcript.
            
Video Title: {video_title if video_title else "Not provided"}

Transcript:
{truncated_transcript}

Provide a clear, concise summary that captures the main points and key takeaways from this video."""

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3  # Lower temperature for more focused summaries
            )
            
            summary = response.choices[0].message.content
            
            logger.info(f"Successfully generated summary ({len(summary)} characters)")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return None
    
    def summarize_with_key_points(self, transcript: str, video_title: str = "") -> Optional[dict]:
        """
        Generate a summary with structured key points
        
        Args:
            transcript: Full transcript text
            video_title: Title of the video
            
        Returns:
            Dictionary with 'summary' and 'key_points' fields
        """
        if not transcript or len(transcript.strip()) < 50:
            logger.warning("Transcript too short to summarize")
            return None
        
        try:
            # Truncate transcript if too long
            max_transcript_length = 15000
            truncated_transcript = transcript[:max_transcript_length]
            if len(transcript) > max_transcript_length:
                truncated_transcript += "\n\n[Transcript truncated...]"
            
            system_prompt = """You are a helpful assistant that summarizes YouTube video transcripts.
            Provide a structured response with:
            1. A concise summary paragraph
            2. A list of key points/takeaways
            
            Format your response as JSON with 'summary' and 'key_points' fields.
            The 'key_points' should be an array of strings."""
            
            user_prompt = f"""Summarize this YouTube video transcript:

Video Title: {video_title if video_title else "Not provided"}

Transcript:
{truncated_transcript}

Return JSON format with 'summary' (string) and 'key_points' (array of strings)."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            logger.info("Successfully generated structured summary")
            return result
            
        except Exception as e:
            logger.error(f"Error generating structured summary: {e}")
            # Fallback to simple summary
            simple_summary = self.summarize(transcript, video_title)
            if simple_summary:
                return {"summary": simple_summary, "key_points": []}
            return None
    
    def get_bullet_points(self, transcript: str, max_points: int = 5) -> Optional[str]:
        """
        Generate a quick bullet-point summary
        
        Args:
            transcript: Full transcript text
            max_points: Maximum number of bullet points
            
        Returns:
            Formatted bullet point string
        """
        try:
            # Truncate transcript if needed
            truncated_transcript = transcript[:10000]
            
            system_prompt = f"""Extract the {max_points} most important points from this transcript.
            Return them as a simple list, one point per line, starting with '• '."""
            
            user_prompt = f"""Extract the key points from this transcript:

{truncated_transcript}

Provide exactly {max_points} bullet points."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating bullet points: {e}")
            return None