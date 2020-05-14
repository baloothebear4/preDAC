import pyaudio, wave


def start_record():
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1024
    RECORD_SECONDS = 10
    WAVE_OUTPUT_FILENAME = "rec.wav"
    audio = pyaudio.PyAudio()

    # start recording
    wav_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    print "recording..."
    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = wav_stream.read(CHUNK)
        frames.append(data)
    print "finished recording"

    # stop recording
    wav_stream.stop_stream()
    wav_stream.close()
    audio.terminate()

    wave_file = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wave_file.setnchannels(CHANNELS)
    wave_file.setsampwidth(audio.get_sample_size(FORMAT))
    wave_file.setframerate(RATE)
    wave_file.writeframes(b''.join(frames))
    wave_file.close()


if __name__ == "__main__":
    try:
        start_record()
    except KeyboardInterrupt:
        pass
