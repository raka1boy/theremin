import sine_gen
import pyaudio
from pynput import mouse


#вызывать при каждом изменении параметроу
def init():
    gen = sine_gen.SineGen(max_freq=2000, chunk_size=1024, harmonics=[1])
    mouse_listener = mouse.Listener(on_move=gen.on_move)
    mouse_listener.start()
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=gen.sample_rate,
                    output=True,
                    frames_per_buffer=gen.chunk_size,
                    stream_callback=gen.audio_callback)
    stream.start_stream()
    
    try:
        #mainloop
        while stream.is_active():
            pass
    except KeyboardInterrupt:
        pass

    #cleanup
    stream.stop_stream()
    stream.close()
    p.terminate()
    mouse_listener.stop()
    return

init()