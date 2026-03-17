"""
Speech to Text using OpenAI Whisper
Converts audio files to text transcription
"""
import os
from datetime import datetime
from pathlib import Path

class SpeechToText:
    def __init__(self, model_size="base"):
        """
        Initialize Whisper model
        
        Model sizes:
        - tiny: Fastest, least accurate (~1GB RAM)
        - base: Fast, good accuracy (~1GB RAM)
        - small: Balanced (~2GB RAM)
        - medium: Better accuracy (~5GB RAM)
        - large: Best accuracy, slowest (~10GB RAM)
        """
        self.model_size = model_size
        self.model = None
        
        # Set FFmpeg path for Whisper
        self._setup_ffmpeg()
    
    def _setup_ffmpeg(self):
        """Setup FFmpeg path for Whisper to use"""
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
        
        # Add FFmpeg directory to PATH for Whisper
        if ffmpeg_path:
            ffmpeg_dir = str(Path(ffmpeg_path).parent)
            if ffmpeg_dir not in os.environ.get('PATH', ''):
                os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
                print(f"Added FFmpeg to PATH: {ffmpeg_dir}")
        
    def _load_model(self):
        """Lazy load the Whisper model"""
        if self.model is None:
            try:
                import whisper
                print(f"\n{'='*70}")
                print(f"Loading Whisper Model: {self.model_size}")
                print(f"{'='*70}")
                print("This may take a moment on first run (downloading model)...")
                self.model = whisper.load_model(self.model_size)
                print(f"✓ Model loaded successfully!\n")
            except ImportError:
                print("\n✗ ERROR: Whisper not installed!")
                print("Please install: pip install openai-whisper")
                return False
            except Exception as e:
                print(f"\n✗ Error loading model: {e}")
                return False
        return True
    
    def transcribe_file(self, file_path, language=None, save_txt=True):
        """
        Transcribe audio/video file to text
        
        Args:
            file_path: Path to audio/video file
            language: Language code (e.g., 'en', 'hi', 'es') or None for auto-detect
            save_txt: Save transcription as .txt file
            
        Returns:
            Dictionary with transcription results
        """
        if not os.path.exists(file_path):
            print(f"✗ Error: File not found: {file_path}")
            return None
        
        # Load model if not already loaded
        if not self._load_model():
            return None
        
        print(f"\n{'='*70}")
        print(f"Transcribing File")
        print(f"{'='*70}")
        print(f"Input: {file_path}")
        print(f"Language: {language if language else 'Auto-detect'}")
        print(f"{'='*70}\n")
        
        try:
            # Transcribe
            print("Transcribing... (this may take a few minutes)")
            if language:
                result = self.model.transcribe(file_path, language=language)
            else:
                result = self.model.transcribe(file_path)
            
            detected_language = result.get('language', 'unknown')
            text = result['text'].strip()
            
            print(f"\n{'='*70}")
            print(f"✓ Transcription Complete!")
            print(f"{'='*70}")
            print(f"Detected Language: {detected_language}")
            print(f"Text Length: {len(text)} characters")
            print(f"{'='*70}\n")
            
            # Save as text file
            if save_txt:
                txt_path = self._save_as_txt(file_path, text, detected_language)
                print(f"✓ Text file saved: {txt_path}")
            
            # Print preview
            print(f"\n{'='*70}")
            print(f"Transcription Preview:")
            print(f"{'='*70}")
            preview = text[:500] + "..." if len(text) > 500 else text
            print(preview)
            print(f"{'='*70}\n")
            
            return {
                'text': text,
                'language': detected_language,
                'segments': result.get('segments', [])
            }
            
        except Exception as e:
            print(f"\n✗ Error during transcription: {e}")
            return None
    
    def _save_as_txt(self, original_file, text, language):
        """Save transcription as text file"""
        file_path = Path(original_file)
        output_path = file_path.with_suffix('.txt')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Transcription of: {file_path.name}\n")
            f.write(f"Language: {language}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*70}\n\n")
            f.write(text)
        
        return output_path
