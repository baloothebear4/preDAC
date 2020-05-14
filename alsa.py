

import alsaaudio, struct, time, math, wave, wavio
import numpy as np

# constants
CHANNELS        = 2
INFORMAT        = alsaaudio.PCM_FORMAT_S16_LE
RATE            = 44100
FRAMESIZE       = 1024
ADCMODE         = alsaaudio.PCM_CAPTURE
duration        = 10
maxValue        = float(2**8)
bars            = 30
offset          = 1
scale           = 0.3
RMSNOISEFLOOR   = -66  #dB

RECORD_SECONDS = 10
WAVE_OUTPUT_FILENAME = "rec.wav"

WINDOW          = 15 # 4 = Hanning
FIRSTCENTREFREQ = 31.25        # Hz
OCTAVE          = 3
NUMPADS         = 0
BINBANDWIDTH    = RATE/(FRAMESIZE + NUMPADS) #ie 43.5 Hz for 44.1kHz/1024
DCOFFSETSAMPLES = 200


class ProcessAudio():
    def __init__(self):
        # set up audio input
        self.recorder = alsaaudio.PCM(type=alsaaudio.PCM_CAPTURE, mode=alsaaudio.PCM_NORMAL)
        self.recorder.setchannels(CHANNELS)
        self.recorder.setrate(int(RATE))
        self.recorder.setformat(INFORMAT)
        self.recorder.setperiodsize(FRAMESIZE)

        print("ProcessAudio: reading from soundcard ", self.recorder.cardname())



    def start_record(self):
        print("recording from ", self.recorder.cardname())
        frames  = []
        retry   = 0
        datalen = 0

        for i in range(0, int(RATE / FRAMESIZE * RECORD_SECONDS)):

            while datalen < FRAMESIZE:
                datalen, raw_data    = self.recorder.read()
                if datalen< 0: print('ProcessAudio.start_record> *** datalen %d, buffer size %d' % (datalen, len(raw_data)))

            while retry<5:
                try:
                    data        = np.frombuffer( raw_data, dtype=np.int16 )

                    dataL       = data[0::2]
                    dataR       = data[1::2]
                    frames.append(data)
                    # frames.append(dataR)



                    break

                except Exception as e:
                    print("ProcessAudio.process> Failed decode ", e)
                    retry += 1

        print("finished recording")

        # stop recording
        self.recorder.close()
        # T = 3
        # t = np.linspace(0, T, T*RATE, endpoint=False)
        # x = np.sin(2*np.pi * 1000 * t)
        #
        # wavio.write("sine24.wav", np.array(x), RATE, sampwidth=2)

        wave_file = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wave_file.setnchannels(2)
        wave_file.setsampwidth(2)
        wave_file.setframerate(RATE)
        wave_file.writeframes(b''.join(frames))
        wave_file.close()



if __name__ == "__main__":
    try:
        p = ProcessAudio()
        p.start_record()

    except KeyboardInterrupt:
        pass
