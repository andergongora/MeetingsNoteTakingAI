import sounddevice as sd

print("HOST APIs:")
for i, api in enumerate(sd.query_hostapis()):
    print(f"{i}: {api['name']}")

print("\nDISPOSITIVOS:")
for i, dev in enumerate(sd.query_devices()):
    print(
        f"{i}: {dev['name']} | "
        f"hostapi={dev['hostapi']} | "
        f"in={dev['max_input_channels']} "
        f"out={dev['max_output_channels']}"
    )
