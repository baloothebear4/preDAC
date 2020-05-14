import pyaudio, wave


def start_record():
    FORMAT = pyaudio.paInt16
    CHANNELS = 2
    RATE = 44100
    CHUNK = 1024
    RECORD_SECONDS = 10
    WAVE_OUTPUT_FILENAME = "rec.wav"
    try:
        audio = pyaudio.PyAudio()

    # start recording
    # wav_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

        wav_stream = audio.open(format = FORMAT,rate = RATE,channels = CHANNELS, \
                    input_device_index = 0,input = True, \
                    frames_per_buffer=CHUNK)
    except Exception as e:
        print("PyAudio init error ", e)

    print("recording from ", audio.get_default_input_device_info()['name'])
    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = wav_stream.read(CHUNK)
        dataL       = data[0::2]

        dataR       = data[1::2]
        print("L", dataL,"R",dataR)
        frames.append(data)
    print("finished recording")

    # stop recording
    wav_stream.stop_stream()
    wav_stream.close()
    audio.terminate()

    wave_file = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wave_file.setnchannels(2)
    wave_file.setsampwidth(audio.get_sample_size(FORMAT))
    wave_file.setframerate(RATE)
    wave_file.writeframes(b''.join(frames))
    wave_file.close()



def dev():

    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    #for each audio device, determine if is an input or an output and add it to the appropriate list and dictionary
    for i in range (0,numdevices):
            if p.get_device_info_by_host_api_device_index(0,i).get('maxInputChannels')>0:
                    print ("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0,i).get('name'))

            if p.get_device_info_by_host_api_device_index(0,i).get('maxOutputChannels')>0:
                    print ("Output Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0,i).get('name'))

    devinfo = p.get_device_info_by_index(1)
    print( "Selected device is ",devinfo.get('name'))
    if p.is_format_supported(rate=44100.0,
                             input_device=1,
                             input_channels=2,
                             input_format=pyaudio.paFloat32):
        print( 'Yay!')
    p.terminate()


if __name__ == "__main__":
    try:
        dev()
        start_record()
    except KeyboardInterrupt:
        pass
