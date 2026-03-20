"""
YouTube Live News Extractor
Extracts video from YouTube live streams
"""
import subprocess
import os
from datetime import datetime
from pathlib import Path

FFMPEG_COMMON_PATHS = [
    r"D:\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
]

def _find_ffmpeg():
    import shutil
    path = shutil.which("ffmpeg")
    if not path:
        for p in FFMPEG_COMMON_PATHS:
            if os.path.exists(p):
                return p
    return path or "ffmpeg"


class YouTubeExtractor:
    def __init__(self, output_dir="news_videos"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.ffmpeg_path = _find_ffmpeg()
        
        # Popular Indian news channels on YouTube
        self.channels = {
            "aajtak": "https://www.youtube.com/@aajtak/live",
            "abpnews": "https://www.youtube.com/@abpnewstv/live",
            "indiatv": "https://www.youtube.com/@IndiaTV/live",
            "ndtv": "https://www.youtube.com/@ndtv/live",
            "zeenews": "https://www.youtube.com/@zeenews/live",
            "republicworld": "https://www.youtube.com/@RepublicWorld/live",
        }
    
    def extract_live_stream(self, channel_name, duration=60):
        """
        Extract from YouTube live stream
        
        Args:
            channel_name: Name of the channel (e.g., 'aajtak')
            duration: Duration in seconds to record
            
        Returns:
            Path to the downloaded video file or None if failed
        """
        if channel_name not in self.channels:
            print(f"✗ Unknown channel: {channel_name}")
            print(f"Available channels: {', '.join(self.channels.keys())}")
            return None
        
        url = self.channels[channel_name]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.output_dir, f"{channel_name}_{timestamp}.mp4")
        
        print(f"\n{'='*70}")
        print(f"Extracting from YouTube Live Stream")
        print(f"{'='*70}")
        print(f"Channel: {channel_name.upper()}")
        print(f"URL: {url}")
        print(f"Duration: {duration}s")
        print(f"Output: {output_path}")
        print(f"{'='*70}\n")
        
        # Use yt-dlp with duration limit
        # Try to find ffmpeg location
        import shutil
        ffmpeg_path = shutil.which("ffmpeg")
        
        # If not found in PATH, try common locations
        if not ffmpeg_path:
            common_paths = [
                r"D:\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe",
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
            ]
            for path in common_paths:
                if os.path.exists(path):
                    ffmpeg_path = path
                    break
        
        command = [
            "yt-dlp",
            url,
            "-o", output_path,
            "--format", "best[ext=mp4]",
            "--download-sections", f"*0-{duration}",
            "--no-playlist"
        ]
        
        if self.ffmpeg_path:
            command.extend(["--ffmpeg-location", self.ffmpeg_path])
            print(f"Using FFmpeg from: {self.ffmpeg_path}")
        
        try:
            print("Starting download...")
            process = subprocess.run(command, capture_output=True, text=True, timeout=duration+30)
            
            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print(f"\n✓ SUCCESS! Video saved: {output_path}")
                print(f"File size: {size_mb:.2f} MB\n")
                return output_path
            else:
                print(f"\n✗ Failed to download")
                print(f"stdout: {process.stdout}")
                print(f"stderr: {process.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"\n✗ Download timed out after {duration+30}s")
            return None
        except FileNotFoundError:
            print("\n✗ ERROR: yt-dlp not found!")
            print("Please install yt-dlp: pip install yt-dlp")
            return None
        except Exception as e:
            print(f"\n✗ Error: {e}")
            return None
    
    def download_video_from_url(self, url):
        """
        Download any YouTube video from URL
        
        Args:
            url: Full YouTube video URL
            
        Returns:
            Path to the downloaded video file or None if failed
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.output_dir, f"youtube_{timestamp}.mp4")
        
        print(f"\n{'='*70}")
        print(f"Downloading YouTube Video")
        print(f"{'='*70}")
        print(f"URL: {url}")
        print(f"Output: {output_path}")
        print(f"{'='*70}\n")
        
        command = [
            "yt-dlp",
            url,
            "-o", output_path,
            "--format", "best[ext=mp4]",
            "--no-playlist"
        ]
        
        if self.ffmpeg_path:
            command.extend(["--ffmpeg-location", self.ffmpeg_path])
            print(f"Using FFmpeg from: {self.ffmpeg_path}")
        
        try:
            print("Starting download...")
            process = subprocess.run(command, capture_output=True, text=True, timeout=600)
            
            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print(f"\n✓ SUCCESS! Video saved: {output_path}")
                print(f"File size: {size_mb:.2f} MB\n")
                return output_path
            else:
                print(f"\n✗ Failed to download")
                print(f"stdout: {process.stdout}")
                print(f"stderr: {process.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"\n✗ Download timed out")
            return None
        except FileNotFoundError:
            print("\n✗ ERROR: yt-dlp not found!")
            print("Please install yt-dlp: pip install yt-dlp")
            return None
        except Exception as e:
            print(f"\n✗ Error: {e}")
            return None
    
    def get_available_channels(self):
        """Get list of available channels"""
        return list(self.channels.keys())
