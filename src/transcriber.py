"""
Audio transcription module using local Whisper model
No API key required - runs completely offline
"""
from pathlib import Path
from typing import Any, Dict, List
import whisper
import torch
from .config import Config
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
import os
from dotenv import load_dotenv

load_dotenv()

HUGGINGFACE_ACCESS_TOKEN = os.getenv("HUGGINGFACE_ACCESS_TOKEN","")


class Transcriber:
    """Transcribes audio files to text using local Whisper model"""

    def __init__(self, model_size: str = None, hf_token: str = HUGGINGFACE_ACCESS_TOKEN):
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
        self.device = ("cuda" if torch.cuda.is_available() else "cpu") # "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

        if self.device == "cuda":
            print(f"   ✓ GPU detectada - usando aceleración CUDA")
        else:
            print(f"   ⚠ GPU no disponible - usando CPU (más lento)")

        # Load Whisper model
        self.model = whisper.load_model(model_size, device=self.device)

        print(f"   ✓ Modelo cargado correctamente\n")

        print(f"📥 Cargando pipeline de diarización de hablantes de Pyannote...")

        self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=hf_token)
        if not self.pipeline:
            print(f"   ✗ Pipeline de diarización no cargado correctamente")
            raise ValueError("Error al cargar el pipeline de diarización de hablantes de Pyannote")
        else:
            self.pipeline.to(torch.device(self.device))
            print(f"   ✓ Pipeline de diarización cargado correctamente\n")


    def transcribe(self, audio_path: Path) -> List[Dict[str, Any]]:
        """
        Transcribe audio file to text

        Args:
            audio_path: Path to the audio file (WAV, MP3, etc.)

        Returns:
            List of dictionaries with 'timestamp' and 'text' keys
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

        if isinstance(result["text"], list):
            text = " ".join([segment["text"] for segment in result["text"]])
        else:
            text = result["text"]

        print(f"✓ Transcripción completada ({len(text)} caracteres)")
        print()

        timestamps = [{"timestamp": (r['start'], r['end']), "text": r['text']} for r in result['segments']]

        return timestamps

    def diarize(self, audio_path: str):
        if self.pipeline is None:
            return None

        try:
            with ProgressHook() as hook:
                diarization = self.pipeline(audio_path, hook=hook)
                return diarization
        except Exception as e:
            raise e

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



    # ----------------------------------------------------------------------

    def transcribe_and_tag(self, audio_path: Path, speaker_id: str, model: whisper.Whisper) -> str:
        """
        Transcribe audio file to text and tag speakers using diarization result

        Args:
            audio_path: Path to the audio file (WAV, MP3, etc.)
            speaker_id: Speaker identifier
            model: Whisper model instance

        Returns:
            Tagged transcribed text
        """
        # Transcribe using Whisper
        result = model.transcribe(
            str(audio_path),
            language="es",  # Spanish
            verbose=False,
            fp16=(self.device == "cuda")  # Use FP16 if GPU available
        )

        if isinstance(result["text"], list):
            text = " ".join([segment["text"] for segment in result["text"]]).strip()
        else:
            text = result["text"].strip()

        # Tag speakers in the transcribed text
        tagged_text = f"[{speaker_id}]: {text}"

        return tagged_text



class SpeakerAligner():
    def align(self, timestamps, diarization):
        speaker_transcriptions = []

        print(f"[DEBUG 🐍] Diarization: {diarization}")
        print("-"*50+"\n"+"-"*50)
        # Find the end time of the last segment in diarization
        last_diarization_end = self.get_last_segment(diarization).end
        print(f"[DEBUG 🐍] Last diarization end: {last_diarization_end}")
        print("-"*50+"\n"+"-"*50)

        print(f"[DEBUG 🐍] Timestamps: {timestamps}")
        print("-"*50+"\n"+"-"*50)
        for chunk in timestamps:
            chunk_start = chunk['timestamp'][0]
            print(f"[DEBUG 🐍] Processing chunk start: {chunk_start}")
            print("-"*50+"\n"+"-"*50)
            chunk_end = chunk['timestamp'][1]
            print(f"[DEBUG 🐍] Processing chunk end: {chunk_end}")
            print("-"*50+"\n"+"-"*50)
            segment_text = chunk['text']
            print(f"[DEBUG 🐍] Processing segment text: {segment_text}")
            print("-"*50+"\n"+"-"*50)

            # Handle the case where chunk_end is None
            if chunk_end is None:
                # Use the end of the last diarization segment as the default end time
                chunk_end = last_diarization_end if last_diarization_end is not None else chunk_start

            # Find the best matching speaker segment
            best_match = self.find_best_match(diarization, chunk_start, chunk_end)
            if best_match:
                speaker = best_match[2]  # Extract the speaker label
                speaker_transcriptions.append((speaker, chunk_start, chunk_end, segment_text))

        # Merge consecutive segments of the same speaker
        speaker_transcriptions = self.merge_consecutive_segments(speaker_transcriptions)
        return speaker_transcriptions

    def find_best_match(self, diarization, start_time, end_time):
        best_match = None
        max_intersection = 0

        for turn, _, speaker in diarization.speaker_diarization.itertracks(yield_label=True):
            turn_start = turn.start
            turn_end = turn.end

            # Calculate intersection manually
            intersection_start = max(start_time, turn_start)
            intersection_end = min(end_time, turn_end)

            if intersection_start < intersection_end:
                intersection_length = intersection_end - intersection_start
                if intersection_length > max_intersection:
                    max_intersection = intersection_length
                    best_match = (turn_start, turn_end, speaker)

        return best_match

    def merge_consecutive_segments(self, segments):
        merged_segments = []
        previous_segment = None

        for segment in segments:
            if previous_segment is None:
                previous_segment = segment
            else:
                if segment[0] == previous_segment[0]:
                    # Merge segments of the same speaker that are consecutive
                    previous_segment = (
                        previous_segment[0],
                        previous_segment[1],
                        segment[2],
                        previous_segment[3] + segment[3]
                    )
                else:
                    merged_segments.append(previous_segment)
                    previous_segment = segment

        if previous_segment:
            merged_segments.append(previous_segment)

        return merged_segments

    def get_last_segment(self, diarization):
        last_segment = None
        for turn, _, _ in diarization.speaker_diarization.itertracks(yield_label=True):
            last_segment = turn
        return last_segment