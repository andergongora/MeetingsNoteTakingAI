import sounddevice as sd
import numpy as np
import soundfile as sf
import queue
from datetime import datetime

# ================= DEVICE DETECTION =================
def find_wasapi_devices():
    """Encuentra dispositivos WASAPI para micro y audio del sistema"""
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()

    # Encontrar el índice del hostapi WASAPI
    wasapi_hostapi = None
    for i, api in enumerate(hostapis):
        if 'wasapi' in api['name'].lower():
            wasapi_hostapi = i
            break

    if wasapi_hostapi is None:
        print("⚠ WASAPI no disponible en este sistema")
        return None, None

    mic_device = None
    system_device = None

    print(f"Buscando dispositivos WASAPI (hostapi={wasapi_hostapi})...\n")

    for i, dev in enumerate(devices):
        # Solo considerar dispositivos WASAPI
        if dev['hostapi'] != wasapi_hostapi:
            continue

        name = dev['name'].lower()

        # Buscar micrófono USB (preferir dispositivos con "microphone" en el nombre)
        if mic_device is None and dev['max_input_channels'] > 0:
            if 'microphone' in name and 'usb' in name:
                mic_device = i
                print(f"✓ Micrófono encontrado: [{i}] {dev['name']}")
                print(f"  Canales: {dev['max_input_channels']}, Sample rate: {int(dev['default_samplerate'])} Hz")

        # Buscar dispositivo de salida para loopback (PREFERIR "speakers")
        if system_device is None and dev['max_output_channels'] > 0:
            if 'speakers' in name:
                system_device = i
                print(f"✓ Audio del sistema encontrado: [{i}] {dev['name']}")
                print(f"  Canales: {dev['max_output_channels']}, Sample rate: {int(dev['default_samplerate'])} Hz")

    # Si no se encontraron específicos, buscar cualquier dispositivo WASAPI disponible
    if mic_device is None or system_device is None:
        print("⚠ No se encontraron dispositivos específicos, buscando alternativos WASAPI...\n")
        for i, dev in enumerate(devices):
            if dev['hostapi'] != wasapi_hostapi:
                continue

            if mic_device is None and dev['max_input_channels'] > 0:
                mic_device = i
                print(f"⚠ Usando micrófono WASAPI: [{i}] {dev['name']}")
                print(f"  Canales: {dev['max_input_channels']}, Sample rate: {int(dev['default_samplerate'])} Hz")

            if system_device is None and dev['max_output_channels'] > 0:
                system_device = i
                print(f"⚠ Usando salida WASAPI: [{i}] {dev['name']}")
                print(f"  Canales: {dev['max_output_channels']}, Sample rate: {int(dev['default_samplerate'])} Hz")

    print()
    return mic_device, system_device

# ================= CONFIG =================
# Auto-detectar dispositivos
MIC_DEVICE, SYSTEM_DEVICE = find_wasapi_devices()

if MIC_DEVICE is None or SYSTEM_DEVICE is None:
    print("❌ ERROR: No se pudieron detectar los dispositivos de audio necesarios.")
    print("\nEjecuta 'python disp.py' para ver todos los dispositivos disponibles")
    print("y luego edita este archivo para configurar manualmente MIC_DEVICE y SYSTEM_DEVICE")
    exit(1)

# Obtener configuración de los dispositivos
devices = sd.query_devices()

# En modo loopback, usamos los canales de SALIDA del dispositivo como entrada
MIC_CHANNELS = devices[MIC_DEVICE]['max_input_channels']
SYS_CHANNELS = devices[SYSTEM_DEVICE]['max_output_channels']

# Usar 48000 Hz que ambos dispositivos soportan
SAMPLERATE = 48000

print(f"📊 Configuración de grabación:")
print(f"   Micrófono: {MIC_CHANNELS} canales @ {SAMPLERATE} Hz")
print(f"   Sistema (loopback): {SYS_CHANNELS} canales @ {SAMPLERATE} Hz")
print()

BLOCKSIZE = 1024

q_mic = queue.Queue()
q_sys = queue.Queue()

# ================= CALLBACKS =================
def mic_callback(indata, frames, time, status):
    if status:
        print("Mic:", status)
    q_mic.put(indata.copy())

def sys_callback(indata, frames, time, status):
    if status:
        print("System:", status)
    q_sys.put(indata.copy())

# ================= OUTPUT =================
filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
print("🎙️  Grabando en:", filename)
print("📻 Canal izquierdo = sistema | Canal derecho = mic")
print("⏹️  Presiona Ctrl+C para parar\n")

# WASAPI loopback SOLO para el sistema
wasapi_loopback = sd.WasapiSettings()
wasapi_loopback.loopback = True

try:
    with sd.InputStream(
        device=MIC_DEVICE,
        samplerate=SAMPLERATE,
        channels=MIC_CHANNELS,
        blocksize=BLOCKSIZE,
        callback=mic_callback
    ), sd.InputStream(
        device=SYSTEM_DEVICE,
        samplerate=SAMPLERATE,
        channels=SYS_CHANNELS,
        blocksize=BLOCKSIZE,
        callback=sys_callback,
        extra_settings=wasapi_loopback
    ), sf.SoundFile(
        filename,
        mode="w",
        samplerate=SAMPLERATE,
        channels=2,
        subtype="PCM_16"
    ) as file:

        print("✓ Grabación iniciada correctamente!")
        print("  Hablando por el micrófono y reproduciendo audio para probar...\n")

        while True:
            mic = q_mic.get()
            sys = q_sys.get()

            # Convertir ambas fuentes a mono
            if mic.ndim > 1 and mic.shape[1] > 1:
                mic_mono = np.mean(mic, axis=1, keepdims=True)
            else:
                mic_mono = mic.reshape(-1, 1) if mic.ndim == 1 else mic

            if sys.ndim > 1 and sys.shape[1] > 1:
                sys_mono = np.mean(sys, axis=1, keepdims=True)
            else:
                sys_mono = sys.reshape(-1, 1) if sys.ndim == 1 else sys

            # Sincronizar tamaños
            n = min(len(mic_mono), len(sys_mono))
            stereo = np.hstack([sys_mono[:n], mic_mono[:n]])

            file.write(stereo)

except KeyboardInterrupt:
    print("\n✓ Grabación finalizada exitosamente")
    print(f"📁 Archivo guardado: {filename}")
except Exception as e:
    print("\n❌ Error durante la grabación:")
    print(f"   {e}")
    import traceback
    traceback.print_exc()
