"""
Speaker Diarization Module
Handles speaker identification and alignment with transcription
"""
import os
import torch
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
from dotenv import load_dotenv

load_dotenv()


class PyannoteDiarizer:
    """Speaker diarization using pyannote.audio"""

    def __init__(self, hf_token: str = None):
        """
        Initialize the diarization pipeline

        Args:
            hf_token: HuggingFace access token (defaults to env variable)
        """
        if hf_token is None:
            hf_token = os.getenv("HUGGINGFACE_ACCESS_TOKEN", "")

        try:
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=hf_token
            )
            if not self.pipeline:
                raise ValueError("Failed to load the diarization pipeline. Check your Hugging Face token and internet connection.")

            # Determine best device
            self.device = torch.device(
                "cuda" if torch.cuda.is_available()
                else "mps" if torch.backends.mps.is_available()
                else "cpu"
            )
            self.pipeline.to(self.device)
            print(f"✅ Diarization pipeline loaded on {self.device}")

        except Exception as e:
            raise ValueError(f"Error initializing diarization pipeline: {e}")

    def diarize(self, audio_path: str):
        """
        Perform speaker diarization on an audio file

        Args:
            audio_path: Path to audio file

        Returns:
            DiarizeOutput object containing speaker segments
        """
        if self.pipeline is None:
            print("❌ Diarization pipeline is not initialized.")
            return None

        try:
            with ProgressHook() as hook:
                diarization = self.pipeline(audio_path, hook=hook)
                return diarization
        except Exception as e:
            print(f"❌ Error during diarization: {e}")
            return None


class SpeakerAligner:
    """Aligns transcription segments with speaker diarization"""

    def align(self, transcription, timestamps, diarization):
        """
        Align transcription chunks with speaker diarization

        Args:
            transcription: Full transcription text
            timestamps: List of dicts with 'timestamp' and 'text' keys
            diarization: DiarizeOutput object from pyannote

        Returns:
            List of tuples (speaker, start_time, end_time, text)
        """
        speaker_transcriptions = []

        # Find the end time of the last segment in diarization
        last_segment = self.get_last_segment(diarization)
        last_diarization_end = last_segment.end if last_segment else None

        for chunk in timestamps:
            chunk_start = chunk['timestamp'][0]
            chunk_end = chunk['timestamp'][1]
            segment_text = chunk['text']

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
        """
        Find the speaker segment that best overlaps with the given time range

        Args:
            diarization: DiarizeOutput object
            start_time: Start time of transcription chunk
            end_time: End time of transcription chunk

        Returns:
            Tuple of (turn_start, turn_end, speaker) for best match, or None
        """
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
        """
        Merge consecutive segments from the same speaker

        Args:
            segments: List of tuples (speaker, start, end, text)

        Returns:
            Merged list of segments
        """
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
                        previous_segment[3] + " " + segment[3]
                    )
                else:
                    merged_segments.append(previous_segment)
                    previous_segment = segment

        if previous_segment:
            merged_segments.append(previous_segment)

        return merged_segments

    def get_last_segment(self, diarization):
        """
        Get the last segment from diarization output

        Args:
            diarization: DiarizeOutput object

        Returns:
            Last segment (Segment object) or None
        """
        last_segment = None
        for turn, _, _ in diarization.speaker_diarization.itertracks(yield_label=True):
            last_segment = turn
        return last_segment
