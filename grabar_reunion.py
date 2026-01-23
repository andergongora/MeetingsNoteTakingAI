#!/usr/bin/env python3
"""
Grabador de Reuniones - Versión Final
Graba micrófono + audio del sistema simultáneamente
Configuración: 44100 Hz para compatibilidad con Focusrite
"""
import pyaudiowpatch as pyaudio
import wave
import numpy as np
from datetime import datetime

class MeetingRecorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.recording = False

    def find_devices(self):
        """Encuentra micrófono y dispositivo loopback automáticamente"""
        mic_device = None
        loopback_device = None

        print("🔍 Buscando dispositivos de audio...\n")

        # Buscar el loopback del dispositivo de salida por defecto
        try:
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_output = self.p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

            # Buscar el dispositivo loopback correspondiente
            for loopback in self.p.get_loopback_device_info_generator():
                if default_output['name'] in loopback["name"]:
                    loopback_device = loopback['index']
                    print(f"✓ Audio del Sistema: {loopback['name']}")
                    print(f"  Sample rate: {int(loopback['defaultSampleRate'])} Hz")
                    break
        except Exception as e:
            print(f"⚠ Error buscando loopback: {e}")
            return None, None

        # Buscar micrófono USB
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            name = info['name'].lower()

            # Evitar dispositivos loopback
            if '[loopback]' in name:
                continue

            if mic_device is None and info['maxInputChannels'] > 0:
                if 'microphone' in name and 'usb' in name:
                    mic_device = i
                    print(f"✓ Micrófono: {info['name']}")
                    print(f"  Sample rate: {int(info['defaultSampleRate'])} Hz")
                    break

        print()
        return mic_device, loopback_device

    def record(self, mic_device, loopback_device, filename):
        """Graba ambas fuentes mezcladas en un archivo WAV"""

        # Configuración de audio
        # IMPORTANTE: Usar 44100 Hz porque Focusrite loopback solo acepta esto
        RATE = 44100
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 2

        print("📊 Configuración de grabación:")
        print(f"   Sample Rate: {RATE} Hz (compatible con ambos dispositivos)")
        print(f"   Canales: {CHANNELS} (Stereo)")
        print(f"   Formato: PCM 16-bit")
        print(f"   Calidad: Sin compresión (alta fidelidad)")
        print()

        # Abrir stream de micrófono
        print("🎤 Abriendo stream de micrófono...")
        try:
            mic_stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=mic_device,
                frames_per_buffer=CHUNK
            )
            print("   ✓ Micrófono abierto correctamente")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return False

        # Abrir stream de loopback (audio del sistema)
        print("🔊 Abriendo stream de audio del sistema (loopback)...")
        try:
            loop_stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=loopback_device,
                frames_per_buffer=CHUNK
            )
            print("   ✓ Loopback abierto correctamente")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            mic_stream.close()
            return False

        # Crear archivo WAV de salida
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)

        # Mostrar información de inicio
        print()
        print("="*70)
        print("✓ GRABACIÓN INICIADA")
        print("="*70)
        print(f"📁 Archivo de salida: {filename}")
        print()
        print("💡 Consejos:")
        print("   • Habla por el micrófono para probar que se graba tu voz")
        print("   • Reproduce algo de audio para verificar el loopback")
        print("   • Presiona Ctrl+C cuando quieras detener la grabación")
        print()

        self.recording = True
        frames_count = 0

        try:
            while self.recording:
                try:
                    # Leer datos de ambos streams
                    mic_data = mic_stream.read(CHUNK, exception_on_overflow=False)
                    loop_data = loop_stream.read(CHUNK, exception_on_overflow=False)

                    # Convertir bytes a numpy arrays para procesamiento
                    mic_array = np.frombuffer(mic_data, dtype=np.int16)
                    loop_array = np.frombuffer(loop_data, dtype=np.int16)

                    # Mezclar ambas fuentes (50% cada una para evitar clipping)
                    # Usamos int32 para evitar overflow en la suma
                    mixed = ((mic_array.astype(np.int32) + loop_array.astype(np.int32)) // 2).astype(np.int16)

                    # Escribir al archivo WAV
                    wf.writeframes(mixed.tobytes())

                    frames_count += 1

                    # Mostrar progreso cada 5 segundos
                    if frames_count % int(5 * RATE / CHUNK) == 0 and frames_count > 0:
                        total_seconds = frames_count * CHUNK / RATE
                        minutes = int(total_seconds // 60)
                        seconds = int(total_seconds % 60)
                        print(f"⏱️  Tiempo grabado: {minutes:02d}:{seconds:02d}", end='\r')

                except IOError:
                    # Buffer overflow/underflow - continuar grabando
                    continue

        except KeyboardInterrupt:
            print("\n\n⏹️  Deteniendo grabación...")
        finally:
            self.recording = False

            # Cerrar streams
            mic_stream.stop_stream()
            mic_stream.close()
            loop_stream.stop_stream()
            loop_stream.close()

            # Cerrar archivo
            wf.close()

            # Calcular estadísticas finales
            total_seconds = frames_count * CHUNK / RATE
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            file_size_mb = (frames_count * CHUNK * 4) / (1024 * 1024)

            # Mostrar resumen
            print()
            print("="*70)
            print("✓ GRABACIÓN FINALIZADA")
            print("="*70)
            print(f"⏱️  Duración total: {minutes:02d}:{seconds:02d}")
            print(f"📁 Archivo guardado: {filename}")
            print(f"💾 Tamaño aproximado: {file_size_mb:.1f} MB")
            print()
            print("🎧 Reproduce el archivo para verificar la calidad de la grabación")

        return True

    def close(self):
        """Cierra PyAudio"""
        self.p.terminate()


def main():
    """Función principal"""
    print("="*70)
    print(" GRABADOR DE REUNIONES")
    print(" Micrófono + Audio del Sistema")
    print("="*70)
    print()

    # Crear instancia del grabador
    recorder = MeetingRecorder()

    try:
        # Buscar dispositivos
        mic_device, loopback_device = recorder.find_devices()

        # Verificar que se encontraron ambos dispositivos
        if mic_device is None:
            print("❌ ERROR: No se encontró un micrófono USB")
            print("\n💡 Solución:")
            print("   1. Conecta un micrófono USB")
            print("   2. Ejecuta 'python disp.py' para ver todos los dispositivos")
            recorder.close()
            return

        if loopback_device is None:
            print("❌ ERROR: No se pudo detectar el dispositivo de loopback")
            print("\n💡 Solución:")
            print("   1. Asegúrate de estar en Windows (WASAPI solo funciona en Windows)")
            print("   2. Ejecuta 'python find_loopback.py' para diagnóstico")
            recorder.close()
            return

        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reunion_{timestamp}.wav"

        # Iniciar grabación
        success = recorder.record(mic_device, loopback_device, filename)

        if not success:
            print("\n❌ La grabación no se pudo iniciar correctamente")
            print("   Ejecuta 'python check_rates.py' para verificar configuración")

    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Siempre cerrar PyAudio
        recorder.close()


if __name__ == "__main__":
    main()
