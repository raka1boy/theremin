import numpy as np
import pyaudio
import keyboard
from pynput import mouse
import tkinter as tk
from tkinter import ttk, simpledialog
from sine_gen import snap_frequency

SCREEN_X, SCREEN_Y = 1920, 1080

def note_from_freq(frequency):
    if frequency <= 0:
        return None
    A4 = 440.0
    C0 = A4 * (2 ** (-4.75))
    half_steps = 12 * np.log2(frequency / C0)
    key_number = round(half_steps)
    note = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][key_number % 12]
    octave = key_number // 12
    return (note, octave)

def snap_to_c(freq):
    """Snap frequency to nearest C note in 12-TET scale"""
    if freq <= 0:
        return freq
    C0 = 16.35  # Fundamental frequency of C0
    # Calculate number of octaves from C0
    octaves = np.log2(freq / C0)
    # Round to nearest whole octave
    nearest_octave = round(octaves)
    return C0 * (2 ** nearest_octave)

class HarmonicControl(ttk.Frame):
    def __init__(self, parent, generator, multiplier, on_remove=None):
        super().__init__(parent)
        self.generator = generator
        self.multiplier = multiplier
        self.on_remove = on_remove
        self.snap_to_note = tk.BooleanVar(value=False)
        self.trigger_key = "space"
        self.key_btn = ttk.Button(
            self, text="Key: space", command=self.set_trigger_key, width=8
        )
        self.key_btn.grid(row=0, column=7, padx=5)
        
        # Configure grid weights
        for col in [1, 3, 5]:
            self.columnconfigure(col, weight=1)
        
        # Row 0: Multiplier and basic controls
        ttk.Label(self, text=f"{multiplier}x").grid(row=0, column=0, padx=5, sticky='w')
        
        # Amplitude controls
        ttk.Label(self, text="Amp:").grid(row=0, column=1, padx=(10,0), sticky='e')
        self.amp_slider = ttk.Scale(
            self, from_=0, to=1, value=1.0,
            command=lambda v: [self.generator.set_harmonic_amp(self.multiplier, float(v)),
                               self.update_display()]
        )
        self.amp_slider.grid(row=0, column=2, sticky="ew", padx=5)
        
        # Amp Smoothing
        ttk.Label(self, text="Amp Smooth:").grid(row=0, column=3, padx=(10,0), sticky='e')
        self.amp_smoothing_slider = ttk.Scale(
            self, from_=0, to=1000, value=100,
            command=lambda v: self.generator.set_harmonic_amp_smoothing(self.multiplier, float(v))
        )
        self.amp_smoothing_slider.grid(row=0, column=4, sticky="ew", padx=5)
        
        # Pitch Smoothing
        ttk.Label(self, text="Pitch Smooth:").grid(row=0, column=5, padx=(10,0), sticky='e')
        self.pitch_smoothing_slider = ttk.Scale(
            self, 
            from_=0, 
            to=50,
            value=0,
            command=lambda v: [
                self.generator.set_harmonic_pitch_smoothing(self.multiplier, float(v)),
                self.pitch_smooth_value.set(f"{int(float(v))}ms")
            ]
        )
        self.pitch_smoothing_slider.grid(row=0, column=6, sticky="ew", padx=5)

        # Add a label showing exact value
        self.pitch_smooth_value = tk.StringVar()
        self.pitch_smooth_value.set("0ms")
        ttk.Label(self, textvariable=self.pitch_smooth_value, width=5).grid(row=0, column=7, padx=(0,5))
        
        # Key binding
        self.key_btn = ttk.Button(
            self, text="Set Key", command=self.set_trigger_key, width=8
        )
        self.key_btn.grid(row=0, column=7, padx=5)
        
        # Note display
        self.note_var = tk.StringVar()
        ttk.Label(self, textvariable=self.note_var, width=8).grid(row=0, column=8, padx=5)
        
        # Frequency display
        self.freq_var = tk.StringVar()
        ttk.Label(self, textvariable=self.freq_var, width=8).grid(row=0, column=9, padx=5)
        
        # Snap to note checkbox
        self.snap_cb = ttk.Checkbutton(
            self, text="Snap", variable=self.snap_to_note,
            command=lambda: [self.generator.set_harmonic_snap(self.multiplier, self.snap_to_note.get()),
                             self.update_display()]
        )
        self.snap_cb.grid(row=0, column=10, padx=5)
        
        # Remove button
        ttk.Button(self, text="×", width=2, command=self.remove_harmonic).grid(row=0, column=11, padx=5)

    def set_trigger_key(self):
        key = simpledialog.askstring(
            "Set Trigger Key",
            f"Press a key to trigger harmonic {self.multiplier}x (or 'space' for spacebar):",
            parent=self
        )
        if key:
            if key.lower() in ["space", " "]:
                key = "space"
            elif len(key) == 1:
                key = key.lower()
            else:
                return
            
            self.trigger_key = key
            display_text = "space" if key == "space" else key
            self.key_btn.config(text=f"Key: {display_text}")
            self.generator.set_harmonic_key(self.multiplier, self.trigger_key)

    def remove_harmonic(self):
        self.generator.remove_harmonic(self.multiplier)
        if self.on_remove:
            self.on_remove(self.multiplier)

    def update_display(self):
        if hasattr(self.generator, 'mouse_x') and hasattr(self.generator, 'harmonics'):
            try:
                idx = self.generator.harmonics.index(self.multiplier)
                display_freq = self.generator.current_freqs[idx]
                
                note_info = note_from_freq(display_freq)
                self.note_var.set(f"{note_info[0]}{note_info[1]}" if note_info else "")
                self.freq_var.set(f"{display_freq:.1f} Hz")
            except ValueError:
                self.note_var.set("")
                self.freq_var.set("")

class ControlUI(tk.Tk):
    def __init__(self, generator):
        super().__init__()
        self.generator = generator
        self.generator.screen_x = self.winfo_screenwidth()
        self.generator.screen_y = self.winfo_screenheight()
        self.title("Theremin")
        self.geometry("1000x650")
        
        self.min_freq_var = tk.StringVar()
        self.max_freq_var = tk.StringVar()
        
        self.setup_ui()
        self.setup_audio()
        self.setup_updater()

    def setup_ui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(main_frame, text="Multiplier").pack(pady=5)
        entry_frame = ttk.Frame(main_frame)
        entry_frame.pack(fill=tk.X)
        
        self.harmonic_entry = ttk.Entry(entry_frame)
        self.harmonic_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.harmonic_entry.bind('<Return>', lambda event: self.add_harmonic())
        
        ttk.Button(entry_frame, text="+", command=self.add_harmonic).pack(side=tk.LEFT)
        
        harmonics_container = ttk.LabelFrame(main_frame, text="Harmonics", height=250)
        harmonics_container.pack(fill=tk.BOTH, expand=True, pady=5)
        harmonics_container.pack_propagate(False)
        
        canvas_frame = ttk.Frame(harmonics_container)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.harmonics_canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.harmonics_canvas.yview)
        self.harmonics_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.harmonics_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.inner_harmonics_frame = ttk.Frame(self.harmonics_canvas)
        self.harmonics_canvas.create_window((0, 0), window=self.inner_harmonics_frame, anchor="nw")
        
        self.inner_harmonics_frame.bind(
            "<Configure>",
            lambda e: self.harmonics_canvas.configure(
                scrollregion=self.harmonics_canvas.bbox("all")
            )
        )
        
        global_controls = ttk.Frame(main_frame)
        global_controls.pack(fill=tk.X, pady=5)
        
        ttk.Label(global_controls, text="Global Smoothing (ms):").pack(side=tk.LEFT)
        self.global_smoothing = ttk.Scale(
            global_controls,
            from_=0,
            to=1000,
            value=100,
            command=lambda v: setattr(self.generator, 'global_amp_smoothing', float(v))
        )
        self.global_smoothing.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        freq_frame = ttk.Frame(main_frame)
        freq_frame.pack(fill=tk.X, pady=5)
        
        # Min Frequency controls
        ttk.Label(freq_frame, text="Min Freq:").pack(side=tk.LEFT)
        self.min_freq = ttk.Scale(
            freq_frame,
            from_=1,
            to=20000,
            value=snap_to_c(self.generator.min_freq),
            command=self.update_min_freq
        )
        self.min_freq.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(freq_frame, textvariable=self.min_freq_var, width=8).pack(side=tk.LEFT)
        self.min_freq_var.set(f"{snap_to_c(self.generator.min_freq):.1f} Hz")
        
        # Max Frequency controls
        ttk.Label(freq_frame, text="Max Freq:").pack(side=tk.LEFT)
        self.max_freq = ttk.Scale(
            freq_frame,
            from_=1,
            to=20000,
            value=snap_to_c(self.generator.max_freq),
            command=self.update_max_freq
        )
        self.max_freq.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(freq_frame, textvariable=self.max_freq_var, width=8).pack(side=tk.LEFT)
        self.max_freq_var.set(f"{snap_to_c(self.generator.max_freq):.1f} Hz")

    def update_min_freq(self, value):
        # Only update if the value has actually changed
        snapped_freq = snap_to_c(float(value))
        if abs(self.generator.min_freq - snapped_freq) > 0.1:  # Small threshold to prevent floating point issues
            self.generator.min_freq = snapped_freq
            self.min_freq_var.set(f"{snapped_freq:.1f} Hz")
            # Temporarily disable the command to prevent recursion
            original_cmd = self.min_freq.cget('command')
            self.min_freq.config(command=lambda v: None)
            self.min_freq.set(snapped_freq)
            self.min_freq.config(command=original_cmd)

    def update_max_freq(self, value):
        # Only update if the value has actually changed
        snapped_freq = snap_to_c(float(value))
        if abs(self.generator.max_freq - snapped_freq) > 0.1:  # Small threshold to prevent floating point issues
            self.generator.max_freq = snapped_freq
            self.max_freq_var.set(f"{snapped_freq:.1f} Hz")
            # Temporarily disable the command to prevent recursion
            original_cmd = self.max_freq.cget('command')
            self.max_freq.config(command=lambda v: None)
            self.max_freq.set(snapped_freq)
            self.max_freq.config(command=original_cmd)

    def add_harmonic(self):
        try:
            mult = float(self.harmonic_entry.get())
            if mult not in self.generator.harmonics:
                self.generator.add_harmonic(mult)
                self.add_harmonic_control(mult)
                self.harmonic_entry.delete(0, tk.END)
        except ValueError:
            pass

    def add_harmonic_control(self, multiplier):
        def remove_callback(mult):
            for child in self.inner_harmonics_frame.winfo_children():
                if hasattr(child, 'multiplier') and child.multiplier == mult:
                    child.destroy()
        
        control = HarmonicControl(
            self.inner_harmonics_frame,
            self.generator,
            multiplier,
            on_remove=remove_callback
        )
        control.pack(fill=tk.X, pady=2)
        control.update_display()
        self.harmonics_canvas.configure(scrollregion=self.harmonics_canvas.bbox("all"))

    def setup_updater(self):
        def update_all():
            for child in self.inner_harmonics_frame.winfo_children():
                if isinstance(child, HarmonicControl):
                    child.update_display()
            self.after(100, update_all)
        update_all()

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
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'pa'):
            self.pa.terminate()
        if hasattr(self, 'mouse_listener'):
            self.mouse_listener.stop()
        self.destroy()