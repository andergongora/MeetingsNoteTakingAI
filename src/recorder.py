"""
Audio recording module
Records microphone and system audio simultaneously using PyAudioWPatch
"""
import threading
import time
import wave
from pathlib import Path
from datetime import datetime
import winsound
import numpy as np
import pyaudiowpatch as pyaudio

from .config import Config


class AudioRecorder:
    """Records audio from microphone and system (loopback) simultaneously"""

    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.recording = False
        self.mic_device = None
        self.loopback_device = None
        self._worker = None
        self._stop_event = threading.Event()
        self._samples_written = 0  # Thread-safe sample counter
        self._lock = threading.Lock()  # For thread-safe access

    def find_devices(self):
        """Find microphone and loopback devices automatically (robust)"""
        print("🔍 Buscando dispositivos de audio...\n")
        self.mic_device = None
        self.loopback_device = None

        # Try to find WASAPI loopback first (Windows)
        try:
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_output_index = wasapi_info.get("defaultOutputDevice")
            default_output = None
            if default_output_index is not None and default_output_index >= 0:
                default_output = self.p.get_device_info_by_index(default_output_index)

            # Search loopback devices
            for loopback in self.p.get_loopback_device_info_generator():
                name = loopback.get("name", "")
                if default_output and default_output.get("name", "") in name:
                    self.loopback_device = loopback['index']
                    print(f"✓ Audio del Sistema: {loopback['name']}")
                    break

            # If not found, try any device that has '[loopback]' in name
            if self.loopback_device is None:
                for i in range(self.p.get_device_count()):
                    info = self.p.get_device_info_by_index(i)
                    if '[loopback]' in info.get('name', '').lower():
                        self.loopback_device = i
                        print(f"✓ Audio del Sistema (fallback): {info['name']}")
                        break
        except Exception as e:
            print(f"⚠ Error buscando loopback: {e}")

        # Find microphone (prefer USB / 'microphone' in name), otherwise first input device
        try:
            best_candidate = None
            for i in range(self.p.get_device_count()):
                info = self.p.get_device_info_by_index(i)
                name = info.get('name', '').lower()
                if info.get('maxInputChannels', 0) > 0:
                    # skip loopback devices if any
                    if '[loopback]' in name:
                        continue
                    if 'microphone' in name and 'usb' in name:
                        self.mic_device = i
                        print(f"✓ Micrófono: {info['name']}")
                        break
                    if best_candidate is None:
                        best_candidate = i

            if self.mic_device is None and best_candidate is not None:
                self.mic_device = best_candidate
                info = self.p.get_device_info_by_index(best_candidate)
                print(f"✓ Micrófono (fallback): {info['name']}")

        except Exception as e:
            print(f"⚠ Error buscando micrófono: {e}")

        print()
        if self.mic_device is None or self.loopback_device is None:
            print("✗ No se han encontrado ambos dispositivos (mic y loopback).")
            return False
        return True

    def _play_beep(self):
        """Play a beep sound to indicate recording started"""
        try:
            winsound.Beep(800, 200)
        except Exception:
            pass

    def _mix_and_clip(self, mic_bytes: bytes, loop_bytes: bytes):
        """Return mixed int16 bytes from two input byte-strings (handles different lengths)"""
        mic_array = np.frombuffer(mic_bytes, dtype=np.int16)
        loop_array = np.frombuffer(loop_bytes, dtype=np.int16)

        min_len = min(len(mic_array), len(loop_array))
        if min_len == 0:
            # One stream returned nothing; return whichever has data (or silence)
            if len(mic_array) > 0:
                return mic_array.astype(np.int16).tobytes(), len(mic_array)
            if len(loop_array) > 0:
                return loop_array.astype(np.int16).tobytes(), len(loop_array)
            return (b'\x00' * 0), 0

        # Mix with int32 accumulator and clip to int16
        mic32 = mic_array[:min_len].astype(np.int32)
        loop32 = loop_array[:min_len].astype(np.int32)
        mixed32 = mic32 + loop32

        # Prevent overflow by clipping to int16 range
        mixed32 = np.clip(mixed32, -32768, 32767)
        mixed16 = mixed32.astype(np.int16)

        return mixed16.tobytes(), mixed16.size  # size = number of samples

    def _record_worker(self, mic_stream, loop_stream, wf):
        """Worker thread: reads from streams, mixes and writes to wave file"""
        CHUNK = 256
        local_samples = 0
        last_update = time.time()
        channels = Config.CHANNELS
        sample_rate = Config.SAMPLE_RATE

        # Pre-calculate silence buffer
        silence_bytes = b'\x00' * (CHUNK * channels * 2)

        try:
            while not self._stop_event.is_set():
                try:
                    # Read microphone - blocking (primary source)
                    mic_data = mic_stream.read(CHUNK, exception_on_overflow=False)

                    # Check if loopback has data available
                    loop_available = loop_stream.get_read_available()

                    if loop_available >= CHUNK:
                        # Loopback has data - read and mix
                        loop_data = loop_stream.read(CHUNK, exception_on_overflow=False)
                    else:
                        # No loopback data - use silence (mic-only recording)
                        loop_data = silence_bytes

                    # Mix audio
                    mixed_bytes, n_samples = self._mix_and_clip(mic_data, loop_data)

                    if n_samples > 0:
                        wf.writeframes(mixed_bytes)
                        local_samples += n_samples

                        # Update shared counter every 0.5 seconds
                        now = time.time()
                        if now - last_update >= 0.5:
                            with self._lock:
                                self._samples_written = local_samples
                            last_update = now

                except IOError:
                    # Buffer overflow/underflow - skip and continue
                    continue
                except Exception as e:
                    print(f"\n❌ Error en grabación: {e}")
                    break

        finally:
            # Final update
            with self._lock:
                self._samples_written = local_samples

    def record(self, output_path: Path = None) -> Path:
        """Record audio to a WAV file. Returns path to saved file."""
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = Config.RECORDINGS_DIR / f"reunion_{timestamp}.wav"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        print("🎤 Inicializando streams de audio...")

        CHUNK = 256

        # Open streams - blocking read mode
        try:
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
        except Exception as e:
            print(f"✗ Error abriendo streams: {e}")
            raise

        print("   ✓ Streams abiertos")

        wf = wave.open(str(output_path), 'wb')
        wf.setnchannels(Config.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(Config.SAMPLE_RATE)

        print()
        print("=" * 70)
        print("🔴 GRABACIÓN INICIADA")
        print("=" * 70)
        print(f"📁 Archivo: {output_path.name}")
        print()
        print("🔔 Señal de inicio...")
        self._play_beep()
        print()
        print("💬 Ya puedes hablar - Presiona Ctrl+C para detener")
        print()

        # Reset counters
        self._stop_event.clear()
        self.recording = True
        with self._lock:
            self._samples_written = 0

        # Start worker thread
        self._worker = threading.Thread(
            target=self._record_worker, args=(mic_stream, loop_stream, wf), daemon=False
        )

        # Start timing
        start_time = time.time()
        self._worker.start()

        # Main thread - monitor and display progress
        last_display = 0
        try:
            while self._worker.is_alive():
                time.sleep(0.1)

                # Calculate elapsed real time
                elapsed_real = time.time() - start_time

                # Get current samples from worker thread
                with self._lock:
                    current_samples = self._samples_written

                # Calculate audio duration from samples
                total_seconds = current_samples / (Config.SAMPLE_RATE * Config.CHANNELS)

                # Display progress every second
                if int(elapsed_real) > last_display:
                    last_display = int(elapsed_real)

                    real_mins = int(elapsed_real // 60)
                    real_secs = int(elapsed_real % 60)
                    audio_mins = int(total_seconds // 60)
                    audio_secs = int(total_seconds % 60)

                    print(f"⏱️  Tiempo real: {real_mins:02d}:{real_secs:02d} | Audio grabado: {audio_mins:02d}:{audio_secs:02d}",
                          end='\r', flush=True)

        except KeyboardInterrupt:
            # Mark stop time
            stop_time = time.time()
            elapsed_total = stop_time - start_time

            print("\n")
            print("=" * 70)
            print("⏹️  CTRL+C DETECTADO")
            print("=" * 70)
            mins = int(elapsed_total // 60)
            secs = int(elapsed_total % 60)
            print(f"⏰ Tiempo real transcurrido: {mins:02d}:{secs:02d}")
            print("=" * 70)
            print()

            self._stop_event.set()

            # Stop streams to unblock reads
            try:
                mic_stream.stop_stream()
            except:
                pass
            try:
                loop_stream.stop_stream()
            except:
                pass

        # Wait for worker to finish
        if self._worker:
            self._worker.join(timeout=3.0)

        # Cleanup
        self.recording = False
        print("\n🔄 Cerrando archivos...")

        # Close WAV file
        try:
            wf.close()
        except Exception as e:
            print(f"⚠ Error cerrando WAV: {e}")

        # Close streams
        try:
            if mic_stream.is_active():
                mic_stream.stop_stream()
            mic_stream.close()
        except:
            pass

        try:
            if loop_stream.is_active():
                loop_stream.stop_stream()
            loop_stream.close()
        except:
            pass

        # Calculate final statistics
        with self._lock:
            final_samples = self._samples_written

        total_seconds = final_samples / (Config.SAMPLE_RATE * Config.CHANNELS)
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)

        # Calculate real elapsed time
        try:
            real_elapsed = time.time() - start_time
            real_mins = int(real_elapsed // 60)
            real_secs = int(real_elapsed % 60)
            time_diff = real_elapsed - total_seconds
        except:
            real_elapsed = 0
            real_mins = 0
            real_secs = 0
            time_diff = 0

        print()
        print("=" * 70)
        print("✓ GRABACIÓN FINALIZADA")
        print("=" * 70)
        print(f"⏰ Tiempo real total: {real_mins:02d}:{real_secs:02d} ({real_elapsed:.2f}s)")
        print(f"⏱️  Audio grabado:    {minutes:02d}:{seconds:02d} ({total_seconds:.2f}s)")
        print(f"📊 Samples: {final_samples:,} | Rate: {Config.SAMPLE_RATE}Hz | Channels: {Config.CHANNELS}")

        if abs(time_diff) > 0.5:
            if time_diff > 0:
                print(f"⚠️  Diferencia: {time_diff:.2f}s de audio perdido")
            else:
                print(f"ℹ️  Diferencia: {abs(time_diff):.2f}s")
        else:
            print(f"✓ Diferencia: {time_diff:.2f}s (excelente sincronización)")

        print(f"📁 Guardado en: {output_path}")

        # Verify file
        if output_path.exists():
            file_size = output_path.stat().st_size / (1024 * 1024)
            print(f"💾 Tamaño: {file_size:.2f} MB")

        print()

        return output_path

    def close(self):
        """Close PyAudio"""
        try:
            self._stop_event.set()
            if self._worker and self._worker.is_alive():
                self._worker.join(timeout=2.0)
            self.p.terminate()
        except:
            pass
