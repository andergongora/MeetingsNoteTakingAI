import pyaudiowpatch as pyaudio

p = pyaudio.PyAudio()

print("Buscando dispositivo loopback de WASAPI...\n")

# Intentar obtener el loopback device
try:
    # Get default WASAPI info
    wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    print(f"WASAPI Host API Index: {wasapi_info['index']}")
    print(f"Default Output Device: {wasapi_info['defaultOutputDevice']}")
    print(f"Default Input Device: {wasapi_info['defaultInputDevice']}")
    print()

    # Get default output device
    default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
    print(f"Default Speakers: {default_speakers['name']}")

    # Check if loopback device exists
    if default_speakers["isLoopbackDevice"]:
        print("✓ Es un dispositivo loopback!")
    else:
        print("✗ No es un dispositivo loopback")

        # Try to get loopback
        print("\nBuscando dispositivo loopback correspondiente...")
        for loopback in p.get_loopback_device_info_generator():
            print(f"  [{loopback['index']}] {loopback['name']}")
            if default_speakers["name"] in loopback["name"]:
                print(f"  ✓ ¡Encontrado! Usar device index: {loopback['index']}")
                break

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

p.terminate()
