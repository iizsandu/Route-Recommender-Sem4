"""
Complete YouTube Live News Pipeline
Video → Audio → Speech-to-Text → Database
"""
from youtube_extractor import YouTubeExtractor
from audio_extractor import AudioExtractor
from speech_to_text import SpeechToText
from db_handler import DBHandler
from datetime import datetime
import os

class YouTubePipeline:
    def __init__(self):
        self.youtube = YouTubeExtractor()
        self.audio = AudioExtractor()
        self.stt = SpeechToText(model_size="base")
        self.db = DBHandler(collection_name="youtube")  # Use youtube collection
    
    def process_live_stream(self, channel_name, duration=60, language=None):
        """
        Complete pipeline: Extract video → Extract audio → Transcribe → Save to DB
        
        Args:
            channel_name: YouTube channel name
            duration: Duration in seconds to record
            language: Language code for transcription (None for auto-detect)
            
        Returns:
            Dictionary with results
        """
        print(f"\n{'='*70}")
        print(f"YouTube Live News Pipeline")
        print(f"{'='*70}")
        print(f"Channel: {channel_name}")
        print(f"Duration: {duration}s")
        print(f"Language: {language if language else 'Auto-detect'}")
        print(f"{'='*70}\n")
        
        result = {
            'success': False,
            'channel': channel_name,
            'video_path': None,
            'audio_path': None,
            'transcription': None,
            'saved_to_db': False,
            'error': None
        }
        
        try:
            # Step 1: Extract video from YouTube live
            print("STEP 1: Extracting video from YouTube live stream...")
            video_path = self.youtube.extract_live_stream(channel_name, duration)
            
            if not video_path:
                result['error'] = "Failed to extract video from YouTube"
                return result
            
            result['video_path'] = video_path
            
            # Step 2: Extract audio from video
            print("\nSTEP 2: Extracting audio from video...")
            audio_path = self.audio.extract_audio(video_path, output_format="mp3")
            
            if not audio_path:
                result['error'] = "Failed to extract audio from video"
                return result
            
            result['audio_path'] = audio_path
            
            # Step 3: Transcribe audio to text
            print("\nSTEP 3: Transcribing audio to text...")
            transcription = self.stt.transcribe_file(audio_path, language=language)
            
            if not transcription:
                result['error'] = "Failed to transcribe audio"
                return result
            
            result['transcription'] = transcription['text']
            
            # Step 4: Save to database
            print("\nSTEP 4: Saving to database...")
            article = {
                'title': f"{channel_name.upper()} Live News - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'url': self.youtube.channels.get(channel_name, ''),
                'source': f'YouTube Live - {channel_name.upper()}',
                'published_date': datetime.now().isoformat(),
                'description': transcription['text'][:500],  # First 500 chars as description
                'extracted_at': datetime.now().isoformat(),
                'full_transcription': transcription['text'],
                'language': transcription['language'],
                'video_path': video_path,
                'audio_path': audio_path,
                'duration': duration
            }
            
            print(f"Saving to collection: {self.db.collection_name}")
            print(f"Article data: title={article['title']}, url={article['url']}")
            save_result = self.db.save_articles([article])
            print(f"Save result: {save_result}")
            result['saved_to_db'] = save_result['inserted'] > 0
            
            result['success'] = True
            
            print(f"\n{'='*70}")
            print(f"✓ PIPELINE COMPLETE!")
            print(f"{'='*70}")
            print(f"Video: {video_path}")
            print(f"Audio: {audio_path}")
            print(f"Transcription length: {len(transcription['text'])} characters")
            print(f"Saved to database: {result['saved_to_db']}")
            print(f"{'='*70}\n")
            
        except Exception as e:
            result['error'] = str(e)
            print(f"\n✗ Pipeline error: {e}")
        
        return result
    
    def process_youtube_url(self, url, language=None):
        """
        Process any YouTube video URL (not just live streams)
        
        Args:
            url: Full YouTube video URL
            language: Language code for transcription (None for auto-detect)
            
        Returns:
            Dictionary with results
        """
        print(f"\n{'='*70}")
        print(f"YouTube Video Pipeline (URL)")
        print(f"{'='*70}")
        print(f"URL: {url}")
        print(f"Language: {language if language else 'Auto-detect'}")
        print(f"{'='*70}\n")
        
        result = {
            'success': False,
            'url': url,
            'video_path': None,
            'audio_path': None,
            'transcription': None,
            'saved_to_db': False,
            'error': None
        }
        
        try:
            # Step 1: Download video from URL
            print("STEP 1: Downloading video from YouTube URL...")
            video_path = self.youtube.download_video_from_url(url)
            
            if not video_path:
                result['error'] = "Failed to download video from YouTube"
                return result
            
            result['video_path'] = video_path
            
            # Step 2: Extract audio from video
            print("\nSTEP 2: Extracting audio from video...")
            audio_path = self.audio.extract_audio(video_path, output_format="mp3")
            
            if not audio_path:
                result['error'] = "Failed to extract audio from video"
                return result
            
            result['audio_path'] = audio_path
            
            # Step 3: Transcribe audio to text
            print("\nSTEP 3: Transcribing audio to text...")
            transcription = self.stt.transcribe_file(audio_path, language=language)
            
            if not transcription:
                result['error'] = "Failed to transcribe audio"
                return result
            
            result['transcription'] = transcription['text']
            
            # Step 4: Save to database
            print("\nSTEP 4: Saving to database...")
            article = {
                'title': f"YouTube Video - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'url': url,
                'source': 'YouTube Video',
                'published_date': datetime.now().isoformat(),
                'description': transcription['text'][:500],
                'extracted_at': datetime.now().isoformat(),
                'full_transcription': transcription['text'],
                'language': transcription['language'],
                'video_path': video_path,
                'audio_path': audio_path
            }
            
            print(f"Saving to collection: {self.db.collection_name}")
            print(f"Article data: title={article['title']}, url={article['url']}")
            save_result = self.db.save_articles([article])
            print(f"Save result: {save_result}")
            result['saved_to_db'] = save_result['inserted'] > 0
            
            result['success'] = True
            
            print(f"\n{'='*70}")
            print(f"✓ PIPELINE COMPLETE!")
            print(f"{'='*70}")
            print(f"Video: {video_path}")
            print(f"Audio: {audio_path}")
            print(f"Transcription length: {len(transcription['text'])} characters")
            print(f"Saved to database: {result['saved_to_db']}")
            print(f"{'='*70}\n")
            
        except Exception as e:
            result['error'] = str(e)
            print(f"\n✗ Pipeline error: {e}")
        
        return result
    
    def get_available_channels(self):
        """Get list of available YouTube channels"""
        return self.youtube.get_available_channels()
