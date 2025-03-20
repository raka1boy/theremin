import numpy as np
import pyaudio
import keyboard
from pynput import mouse
import tkinter as tk
from tkinter import ttk

SCREEN_X, SCREEN_Y = 1920, 1080

class ControlUI(tk.Tk):
    def __init__(self, generator):
        
        super().__init__()
        self.generator = generator
        self.title("Терменбокс")
        self.geometry("400x450")
        
        self.setup_ui()
        self.setup_audio()

    def setup_ui(self):
        ttk.Label(self, text="размер куска").pack(pady=5)
        self.harmonic_entry = ttk.Entry(self)
        self.harmonic_entry.pack()

        ttk.Label(self, text="умножатель").pack(pady=5)
        self.harmonic_entry = ttk.Entry(self)
        self.harmonic_entry.pack()
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="+", command=self.add_harmonic).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="-", command=self.remove_harmonic).pack(side=tk.LEFT)
        
        ttk.Label(self, text="Гармоники:").pack(pady=5)
        self.harmonics_list = tk.Listbox(self, height=4)
        self.harmonics_list.pack(fill=tk.X, padx=10)
        
        ttk.Label(self, text="Smoothing (ms):").pack(pady=5)
        self.smoothing_slider = ttk.Scale(self, from_=0, to=1000, command=lambda v: setattr(self.generator, 'smoothing_time', float(v)))
        self.smoothing_slider.set(100)
        self.smoothing_slider.pack(fill=tk.X, padx=10)

        # Minimum Frequency Slider
        ttk.Label(self, text="Минимальная частота").pack(pady=5)
        self.min_freq_slider = ttk.Scale(self, from_=1, to=10000, command=lambda v: setattr(self.generator, 'min_freq', float(v)))
        self.min_freq_slider.set(10)
        self.min_freq_slider.pack(fill=tk.X, padx=10)

        # Maximum Frequency Slider
        ttk.Label(self, text="Максимальная частота").pack(pady=5)
        self.max_freq_slider = ttk.Scale(self, from_=1, to=10000, command=lambda v: setattr(self.generator, 'max_freq', float(v)))
        self.max_freq_slider.set(1500)
        self.max_freq_slider.pack(fill=tk.X, padx=10)

    def add_harmonic(self):
        try:
            mult = float(self.harmonic_entry.get())
            self.generator.add_harmonic(mult)
            self.harmonics_list.insert(tk.END, mult)
            self.harmonic_entry.delete(0, tk.END)
        except ValueError:
            pass

    def remove_harmonic(self):
        selection = self.harmonics_list.curselection()
        if selection:
            mult = float(self.harmonics_list.get(selection[0]))
            self.generator.remove_harmonic(mult)
            self.harmonics_list.delete(selection[0])

    def setup_audio(self):
        def on_move(x, y):
            self.generator.mouse_x = x
            self.generator.mouse_y = y

        self.mouse_listener = mouse.Listener(on_move=on_move)
        self.mouse_listener.start()
        
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=self.generator.sample_rate,
            output=True,
            frames_per_buffer=self.generator.chunk_size,
            stream_callback=self.generator.audio_callback
        )
        self.stream.start_stream()

    def on_closing(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()
        self.mouse_listener.stop()
        self.destroy()