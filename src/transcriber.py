"""
Audio transcription module using local Whisper model
No API key required - runs completely offline
"""
from pathlib import Path
import whisper
import torch
from .config import Config


class Transcriber:
    """Transcribes audio files to text using local Whisper model"""

    def __init__(self, model_size: str = None):
        """
        Initialize transcriber with Whisper model

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
                       If None, uses Config.WHISPER_MODEL
        """
        if model_size is None:
            model_size = Config.WHISPER_MODEL

        print(f"📥 Cargando modelo Whisper '{model_size}'...")

        # Check if CUDA (GPU) is available
        device = "cuda" if torch.cuda.is_available() else "cpu"

        if device == "cuda":
            print(f"   ✓ GPU detectada - usando aceleración CUDA")
        else:
            print(f"   ⚠ GPU no disponible - usando CPU (más lento)")

        # Load Whisper model
        self.model = whisper.load_model(model_size, device=device)
        self.device = device

        print(f"   ✓ Modelo cargado correctamente\n")

    def transcribe(self, audio_path: Path) -> str:
        """
        Transcribe audio file to text

        Args:
            audio_path: Path to the audio file (WAV, MP3, etc.)

        Returns:
            Transcribed text
        """
        print()
        print("="*70)
        print("📝 TRANSCRIBIENDO AUDIO")
        print("="*70)
        print(f"📁 Archivo: {audio_path.name}")
        print(f"🤖 Modelo: Whisper {Config.WHISPER_MODEL} (local)")
        print(f"⚙️  Dispositivo: {self.device.upper()}")
        print()
        print("⏳ Transcribiendo...")

        # Transcribe using Whisper
        result = self.model.transcribe(
            str(audio_path),
            language="es",  # Spanish
            verbose=False,
            fp16=(self.device == "cuda")  # Use FP16 if GPU available
        )

        text = result["text"]

        print(f"✓ Transcripción completada ({len(text)} caracteres)")
        print()

        return text

    def save_transcript(self, text: str, output_path: Path) -> Path:
        """
        Save transcript to a text file

        Args:
            text: Transcribed text
            output_path: Where to save the transcript

        Returns:
            Path to the saved transcript file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)

        print(f"💾 Transcripción guardada: {output_path}")
        print()

        return output_path
