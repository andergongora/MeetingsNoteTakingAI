#!/usr/bin/env python3
"""
Meeting AI System - Main Application
Records meetings, transcribes audio, and analyzes with AI
"""
import sys
from pathlib import Path
from datetime import datetime

from src.diarizer import PyannoteDiarizer

# Add src to path for importing
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.recorder import AudioRecorder
from src.transcriber import SpeakerAligner, Transcriber
from src.analyzer import MeetingAnalyzer


def print_banner():
    """Print application banner"""
    print("="*70)
    print(" MEETING AI SYSTEM")
    print(" Grabación → Transcripción → Análisis con IA")
    print("="*70)
    print()


def main():
    """Main application flow"""
    print_banner()

    # Step 0: Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print("❌ ERROR DE CONFIGURACIÓN")
        print()
        print(str(e))
        print()
        print("💡 Solución:")
        print("   1. Copia .env.template a .env")
        print("   2. Edita .env y agrega tus API keys")
        print("   3. Ejecuta de nuevo")
        return 1

    # Ensure output directories exist
    Config.ensure_dirs()

    # Generate timestamp for this meeting
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    timestamp = "20260126_173852"  # For testing purposes

    # Define file paths
    audio_path = Config.RECORDINGS_DIR / f"reunion_{timestamp}.wav"
    transcript_path = Config.TRANSCRIPTS_DIR / f"reunion_{timestamp}.txt"
    summary_path = Config.SUMMARIES_DIR / f"reunion_{timestamp}"

    # Step 1: Record meeting
    print("PASO 1/3: GRABACIÓN")
    print("-" * 70)
    print()

    recorder = AudioRecorder()

    if not recorder.find_devices():
        print("❌ No se encontraron dispositivos de audio")
        print()
        print("💡 Ejecuta: python disp.py")
        recorder.close()
        return 1

    try:
        audio_path = recorder.record(audio_path)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ Error grabando: {e}")
        return 1
    finally:
        recorder.close()

    # Ask if user wants to continue with transcription
    print()
    print("¿Continuar con transcripción y análisis? (s/n): ", end='')
    response = input().lower()

    if response != 's':
        print("✓ Grabación guardada. Proceso detenido.")
        return 0

    # Step 2: Transcribe audio
    print()
    print("PASO 2/3: TRANSCRIPCIÓN")
    print("-" * 70)

    try:
        transcriber = Transcriber()
        transcription = transcriber.transcribe(audio_path)

        speaker_aligner = SpeakerAligner()
        # diarizer = PyannoteDiarizer()

        diarization = transcriber.diarize(str(audio_path))

        # Align speaker segments with transcription
        aligned_segments = speaker_aligner.align(transcription, diarization)

        # Create tagged transcript
        tagged_transcript = "\n".join([f"[{speaker}]: {text}" for speaker, start, end, text in aligned_segments])

        transcriber.save_transcript(tagged_transcript, transcript_path)

    except Exception as e:
        print(f"❌ Error transcribiendo: {e}")
        return 1

    # Step 3: Analyze with Gemini
    print()
    print("PASO 3/3: ANÁLISIS CON IA")
    print("-" * 70)

    try:
        analyzer = MeetingAnalyzer()
        analysis = analyzer.analyze(tagged_transcript)
        json_path, md_path = analyzer.save_analysis(analysis, summary_path)
    except Exception as e:
        print(f"❌ Error analizando: {e}")
        print()
        print("💡 Verifica tu GEMINI_API_KEY")
        return 1

    # Final summary
    print()
    print("="*70)
    print("✅ PROCESO COMPLETADO")
    print("="*70)
    print()
    print("📁 Archivos generados:")
    print(f"   🎤 Grabación:     {audio_path}")
    print(f"   📝 Transcripción: {transcript_path}")
    print(f"   🤖 Análisis JSON: {json_path}")
    print(f"   📄 Resumen MD:    {md_path}")
    print()

    # Display summary
    print("="*70)
    print("📋 RESUMEN DE LA REUNIÓN")
    print("="*70)
    print()

    with open(md_path, 'r', encoding='utf-8') as f:
        print(f.read())

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Proceso interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
