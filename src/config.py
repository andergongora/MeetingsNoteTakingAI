"""
Configuration management for Meeting AI System
Loads API keys and settings from environment variables
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the application"""

    # API Keys (only Gemini required now - Whisper runs locally)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # Model Configuration
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
    print(f"🤖 Modelo: Whisper {WHISPER_MODEL} (local)")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    print(f"🤖 Modelo: Gemini {GEMINI_MODEL}")

    # Audio Recording Settings
    SAMPLE_RATE = 44100  # Compatible with Focusrite
    CHUNK_SIZE = 1024
    CHANNELS = 2

    # Paths
    BASE_DIR = Path(__file__).parent.parent
    OUTPUTS_DIR = BASE_DIR / "outputs"
    RECORDINGS_DIR = OUTPUTS_DIR / "recordings"
    TRANSCRIPTS_DIR = OUTPUTS_DIR / "transcripts"
    SUMMARIES_DIR = OUTPUTS_DIR / "summaries"
    PROMPTS_DIR = BASE_DIR / "prompts"

    @classmethod
    def validate(cls):
        """Validate that required API keys are set"""
        errors = []

        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY not set in .env")

        if errors:
            raise ValueError("Missing configuration:\n" + "\n".join(f"  - {e}" for e in errors))

        return True

    @classmethod
    def ensure_dirs(cls):
        """Ensure all output directories exist"""
        cls.RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        cls.TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
