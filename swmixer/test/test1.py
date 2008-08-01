import swmixer
import time

swmixer.init(samplerate=44100, chunksize=1024, stereo=True)
swmixer.start()
snd1 = swmixer.StreamingSound("Beat_77.mp3")
print snd1.get_length()
snd2 = swmixer.Sound("test2.wav")
snd1.play(volume=0.2)
snd2.play()
time.sleep(10.0) #don't quit before we hear the sound!
