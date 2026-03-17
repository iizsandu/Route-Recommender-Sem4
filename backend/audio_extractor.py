"""
Audio Extractor
Extracts audio from video files using ffmpeg
"""
import subprocess
import os
from pathlib import Path

class AudioExtractor:
    def __init__(self):
        # Try to find ffmpeg
        import shutil
        self.ffmpeg_path = shutil.which("ffmpeg")
        
        # If not found in PATH, try common locations
        if not self.ffmpeg_path:
            common_paths = [
                r"D:\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe",
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
            ]
            for path in common_paths:
                if os.path.exists(path):
                    self.ffmpeg_path = path
                    break
        
        if not self.ffmpeg_path:
            self.ffmpeg_path = "ffmpeg"  # Fallback to command name
    
    def extract_audio(self, video_path, output_format="mp3", audio_quality="192k"):
        """
        Extract audio from video file using ffmpeg
        
        Args:
            video_path: Path to the video file
            output_format: Audio format (mp3, wav, aac, m4a)
            audio_quality: Audio bitrate (e.g., "128k", "192k", "320k")
            
        Returns:
            Path to the extracted audio file or None if failed
        """
        if not os.path.exists(video_path):
            print(f"✗ Error: Video file not found: {video_path}")
            return None
        
        # Create output path
        video_file = Path(video_path)
        output_path = video_file.with_suffix(f".{output_format}")
        
        print(f"\n{'='*70}")
        print(f"Extracting Audio from Video")
        print(f"{'='*70}")
        print(f"Input Video: {video_path}")
        print(f"Output Audio: {output_path}")
        print(f"Format: {output_format.upper()}")
        print(f"Quality: {audio_quality}")
        print(f"{'='*70}\n")
        
        try:
            # ffmpeg command to extract audio
            command = [
                self.ffmpeg_path,
                "-i", video_path,
                "-vn",  # No video
                "-acodec", "libmp3lame" if output_format == "mp3" else "copy",
                "-ab", audio_quality,
                "-y",  # Overwrite output file
                str(output_path)
            ]
            
            print(f"Using FFmpeg from: {self.ffmpeg_path}")
            print("Extracting audio...")
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if process.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                print(f"\n{'='*70}")
                print(f"✓ SUCCESS!")
                print(f"{'='*70}")
                print(f"Audio saved: {output_path}")
                print(f"File size: {file_size:.2f} MB")
                print(f"{'='*70}\n")
                return str(output_path)
            else:
                print(f"\n✗ Failed to extract audio")
                print(f"Error: {process.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("\n✗ Audio extraction timed out")
            return None
        except FileNotFoundError:
            print("\n✗ ERROR: ffmpeg not found!")
            print("Please install ffmpeg and add it to your PATH")
            return None
        except Exception as e:
            print(f"\n✗ Error: {e}")
            return None
