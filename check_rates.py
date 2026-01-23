import pyaudiowpatch as pyaudio

p = pyaudio.PyAudio()

print("PROBANDO CONFIGURACIONES DE SAMPLE RATE\n")

# Encontrar dispositivos
wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
default_output = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

loopback_device = None
for loopback in p.get_loopback_device_info_generator():
    if default_output['name'] in loopback["name"]:
        loopback_device = loopback['index']
        print(f"Loopback: {loopback['name']}")
        print(f"  Default SR: {int(loopback['defaultSampleRate'])} Hz\n")
        break

mic_device = None
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    name = info['name'].lower()
    if '[loopback]' not in name and info['maxInputChannels'] > 0:
        if 'microphone' in name and 'usb' in name:
            mic_device = i
            print(f"Micrófono: {info['name']}")
            print(f"  Default SR: {int(info['defaultSampleRate'])} Hz\n")
            break

if not mic_device or not loopback_device:
    print("No se encontraron dispositivos")
    p.terminate()
    exit()

# Probar diferentes sample rates
test_rates = [44100, 48000]

for rate in test_rates:
    print(f"Probando {rate} Hz:")

    # Test micrófono
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=2,
            rate=rate,
            input=True,
            input_device_index=mic_device,
            frames_per_buffer=1024
        )
        stream.close()
        print(f"  ✓ Micrófono OK @ {rate} Hz")
    except Exception as e:
        print(f"  ✗ Micrófono falla @ {rate} Hz: {e}")

    # Test loopback
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=2,
            rate=rate,
            input=True,
            input_device_index=loopback_device,
            frames_per_buffer=1024
        )
        stream.close()
        print(f"  ✓ Loopback OK @ {rate} Hz")
    except Exception as e:
        print(f"  ✗ Loopback falla @ {rate} Hz: {e}")

    print()

p.terminate()

print("\nRECOMENDACIÓN:")
print("Usa el sample rate que funcione para AMBOS dispositivos")
