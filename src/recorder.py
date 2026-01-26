"""
Audio recording module
Records microphone and system audio simultaneously using PyAudioWPatch
"""
import pyaudiowpatch as pyaudio
import wave
import numpy as np
from pathlib import Path
from datetime import datetime
import winsound
from .config import Config


class AudioRecorder:
    """Records audio from microphone and system (loopback) simultaneously"""

    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.recording = False
        self.mic_device = None
        self.loopback_device = None

    def find_devices(self):
        """Find microphone and loopback devices automatically"""
        print("🔍 Buscando dispositivos de audio...\n")

        # Find loopback device
        try:
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_output = self.p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

            for loopback in self.p.get_loopback_device_info_generator():
                if default_output['name'] in loopback["name"]:
                    self.loopback_device = loopback['index']
                    print(f"✓ Audio del Sistema: {loopback['name']}")
                    break
        except Exception as e:
            print(f"⚠ Error buscando loopback: {e}")
            return False

        # Find microphone
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            name = info['name'].lower()

            if '[loopback]' in name:
                continue

            if self.mic_device is None and info['maxInputChannels'] > 0:
                if 'microphone' in name and 'usb' in name:
                    self.mic_device = i
                    print(f"✓ Micrófono: {info['name']}")
                    break

        print()

        if self.mic_device is None or self.loopback_device is None:
            return False

        return True

    def _play_beep(self):
        """Play a beep sound to indicate recording started"""
        try:
            winsound.Beep(800, 200)
        except:
            pass

    def record(self, output_path: Path = None) -> Path:
        """Record audio to a WAV file"""
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = Config.RECORDINGS_DIR / f"reunion_{timestamp}.wav"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        print("🎤 Inicializando streams de audio...")

        # SMALL chunk for responsive Ctrl+C (256 frames = ~6ms per read)
        CHUNK = 256

        # Create streams - blocking read mode
        mic_stream = self.p.open(
            format=pyaudio.paInt16,
            channels=Config.CHANNELS,
            rate=Config.SAMPLE_RATE,
            input=True,
            input_device_index=self.mic_device,
            frames_per_buffer=CHUNK
        )

        loop_stream = self.p.open(
            format=pyaudio.paInt16,
            channels=Config.CHANNELS,
            rate=Config.SAMPLE_RATE,
            input=True,
            input_device_index=self.loopback_device,
            frames_per_buffer=CHUNK
        )

        print("   ✓ Streams abiertos")

        # Create WAV file
        wf = wave.open(str(output_path), 'wb')
        wf.setnchannels(Config.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(Config.SAMPLE_RATE)

        print()
        print("="*70)
        print("🔴 GRABACIÓN INICIADA")
        print("="*70)
        print(f"📁 Archivo: {output_path.name}")
        print()
        print("🔔 Señal de inicio...")
        self._play_beep()
        print()
        print("💬 Ya puedes hablar - Presiona Ctrl+C para detener")
        print()

        self.recording = True
        frames_count = 0

        # Recording loop - writes directly to disk
        try:
            while self.recording:
                try:
                    # Read small chunks (fast Ctrl+C response)
                    mic_data = mic_stream.read(CHUNK, exception_on_overflow=False)
                    loop_data = loop_stream.read(CHUNK, exception_on_overflow=False)

                    # Mix audio
                    mic_array = np.frombuffer(mic_data, dtype=np.int16)
                    loop_array = np.frombuffer(loop_data, dtype=np.int16)

                    min_len = min(len(mic_array), len(loop_array))
                    mixed = ((mic_array[:min_len].astype(np.int32) +
                             loop_array[:min_len].astype(np.int32)) // 2).astype(np.int16)

                    # Write IMMEDIATELY to disk
                    wf.writeframes(mixed.tobytes())
                    frames_count += 1

                    # Show progress every 5 seconds
                    if frames_count % int(5 * Config.SAMPLE_RATE / CHUNK) == 0 and frames_count > 0:
                        total_seconds = frames_count * CHUNK / Config.SAMPLE_RATE
                        minutes = int(total_seconds // 60)
                        seconds = int(total_seconds % 60)
                        print(f"⏱️  {minutes:02d}:{seconds:02d}", end='\r')

                except IOError:
                    # Buffer overflow/underflow - continue
                    continue

        except KeyboardInterrupt:
            print("\n\n⏹️  Deteniendo...")
        finally:
            self.recording = False

            # Close everything
            print("🔄 Cerrando...")
            wf.close()
            mic_stream.stop_stream()
            mic_stream.close()
            loop_stream.stop_stream()
            loop_stream.close()

            # Calculate duration
            total_seconds = frames_count * CHUNK / Config.SAMPLE_RATE
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)

            print()
            print("="*70)
            print("✓ FINALIZADA")
            print("="*70)
            print(f"⏱️  Duración total: {minutes:02d}:{seconds:02d}")
            print(f"📁 {output_path}")
            print()

        return output_path

    def close(self):
        """Close PyAudio"""
        try:
            self.p.terminate()
        except:
            pass
