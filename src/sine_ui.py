import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import pyaudio
import keyboard
from pynput import mouse
from harmonic_control import HarmonicControl
from group_header import GroupHeader
from config_manager import ConfigManager
from utils import MusicUtils

class HarmonicsContainer(ttk.Frame):
    def __init__(self, parent, generator):
        super().__init__(parent)
        self.generator = generator
        self.group_frames = {}
        
        self._setup_styles()
        self._setup_scrollable_area()
        self.rebuild_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.configure('Group.TFrame', background='#f0f0f0')
        style.configure('GroupHeader.TLabel', background='#f0f0f0', font=('Helvetica', 10, 'bold'))

    def _setup_scrollable_area(self):
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.inner_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def rebuild_ui(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        
        self.group_frames = {}
        
        # Show ungrouped harmonics first
        ungrouped = [h.multiplier for h in self.generator.harmonics 
                    if not h.group]
        
        if ungrouped:
            ttk.Label(self.inner_frame, text="Ungrouped Harmonics", font=('Helvetica', 10, 'bold')).pack(fill=tk.X, pady=(5,0))
            for mult in ungrouped:
                control = HarmonicControl(self.inner_frame, self.generator, mult, 
                                        on_remove=self._on_harmonic_removed)
                control.pack(fill=tk.X, pady=2, padx=10)
        
        # Then show groups
        for group_name in self.generator.groups:
            self._add_group_ui(group_name)
        
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _add_group_ui(self, group_name):
        group_container = ttk.Frame(self.inner_frame)
        group_container.pack(fill=tk.X, pady=(10,0))
        self.group_frames[group_name] = group_container
        
        header = GroupHeader(
            group_container,
            self.generator, 
            group_name,
            on_edit=self._on_group_edit,
            on_copy=self._on_group_copy,
            on_remove=self._on_group_remove
        )
        header.pack(fill=tk.X, padx=5, pady=5)
        
        harmonics_frame = ttk.Frame(group_container)
        harmonics_frame.pack(fill=tk.X, padx=20)
        
        for mult in self.generator.groups[group_name].harmonics:
            idx = self.generator._get_harmonic_index(mult)
            if idx != -1:
                control = HarmonicControl(harmonics_frame, self.generator, mult, 
                                        on_remove=self._on_harmonic_removed)
                control.pack(fill=tk.X, pady=2)
                control.update_display()

    def _on_harmonic_removed(self, multiplier):
        self.rebuild_ui()

    def _on_group_edit(self, group_name):
        new_key = simpledialog.askstring(
            "Edit Group Trigger",
            f"Enter new trigger key for group '{group_name}':",
            initialvalue=self.generator.groups[group_name].trigger_key
        )
        if new_key:
            self.generator.set_group_key(group_name, new_key)
            self.rebuild_ui()

    def _on_group_copy(self, group_name):
        new_name = simpledialog.askstring(
            "Copy Group",
            f"Enter name for copied group:",
            initialvalue=f"{group_name}_copy"
        )
        if new_name:
            try:
                original_group = self.generator.groups[group_name]
                self.generator.create_group(new_name, original_group.trigger_key)
                
                for mult in original_group.harmonics:
                    idx = self.generator._get_harmonic_index(mult)
                    if idx != -1:
                        harmonic = self.generator.harmonics[idx]
                        new_mult = self._find_unique_multiplier(mult)
                        
                        self.generator.add_harmonic(
                            multiplier=new_mult,
                            initial_amp=harmonic.initial_amp,
                            amp_smoothing=harmonic.amp_smoothing,
                            pitch_smoothing=harmonic.pitch_smoothing,
                            trigger_key=harmonic.trigger_key
                        )
                        
                        new_idx = self.generator._get_harmonic_index(new_mult)
                        self.generator.harmonics[new_idx].snap_enabled = harmonic.snap_enabled
                        self.generator.assign_to_group(new_mult, new_name)
                
                self.rebuild_ui()
                messagebox.showinfo("Success", f"Group '{group_name}' copied to '{new_name}' with new harmonics")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _find_unique_multiplier(self, base_mult):
        new_mult = base_mult + 0.1
        while any(abs(h.multiplier - new_mult) < 0.0001 for h in self.generator.harmonics):
            new_mult += 0.1
        return new_mult

    def _on_group_remove(self, group_name):
        self.generator.remove_group(group_name)
        self.rebuild_ui()

class ControlUI(tk.Tk):
    def __init__(self, generator):
        super().__init__()
        self.generator = generator
        self.generator.screen_x = self.winfo_screenwidth()
        self.generator.screen_y = self.winfo_screenheight()
        
        self._setup_window()
        self._setup_ui()
        self._setup_audio()
        self._setup_updater()

    def _setup_window(self):
        self.title("Theremin")
        self.geometry("1200x700")

    def _setup_ui(self):
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._setup_harmonic_entry()
        self._setup_group_creation()
        self._setup_harmonics_container()
        self._setup_global_controls()
        self._setup_config_buttons()
        self._setup_frequency_controls()

    def _setup_harmonic_entry(self):
        ttk.Label(self.main_frame, text="Multiplier").pack(pady=5)
        entry_frame = ttk.Frame(self.main_frame)
        entry_frame.pack(fill=tk.X)
        
        self.harmonic_entry = ttk.Entry(entry_frame)
        self.harmonic_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.harmonic_entry.bind('<Return>', self._add_harmonic)
        
        ttk.Button(entry_frame, text="+", command=self._add_harmonic).pack(side=tk.LEFT)

    def _setup_group_creation(self):
        group_frame = ttk.Frame(self.main_frame)
        group_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(group_frame, text="New Group Name:").pack(side=tk.LEFT)
        self.group_name_entry = ttk.Entry(group_frame, width=15)
        self.group_name_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(group_frame, text="Trigger Key:").pack(side=tk.LEFT)
        self.group_key_entry = ttk.Entry(group_frame, width=5)
        self.group_key_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            group_frame, 
            text="Create Group", 
            command=self._create_group
        ).pack(side=tk.LEFT, padx=5)

    def _setup_harmonics_container(self):
        self.harmonics_container = HarmonicsContainer(self.main_frame, self.generator)
        self.harmonics_container.pack(fill=tk.BOTH, expand=True, pady=5)

    def _setup_global_controls(self):
        global_controls = ttk.Frame(self.main_frame)
        global_controls.pack(fill=tk.X, pady=5)
        
        ttk.Label(global_controls, text="Global Smoothing (ms):").pack(side=tk.LEFT)
        self.global_smoothing = ttk.Scale(
            global_controls,
            from_=0,
            to=1000,
            value=self.generator.global_amp_smoothing,
            command=lambda v: setattr(self.generator, 'global_amp_smoothing', float(v)))
        self.global_smoothing.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    def _setup_config_buttons(self):
        config_btn_frame = ttk.Frame(self.main_frame)
        config_btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            config_btn_frame, 
            text="Save Config", 
            command=lambda: ConfigManager.save_config(self.generator, self)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            config_btn_frame, 
            text="Load Config", 
            command=lambda: ConfigManager.load_config(self.generator, self, 
                                                     self.harmonics_container.rebuild_ui)
        ).pack(side=tk.LEFT, padx=5)

    def _setup_frequency_controls(self):
        self.min_freq_var = tk.StringVar()
        self.max_freq_var = tk.StringVar()
        
        # Set reasonable frequency bounds (human hearing range is ~20Hz-20kHz)
        self.min_freq_bound = 20
        self.max_freq_bound = 20000
        
        freq_frame = ttk.Frame(self.main_frame)
        freq_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(freq_frame, text="Min Freq:").pack(side=tk.LEFT)
        self.min_freq = ttk.Scale(
            freq_frame,
            from_=0,
            to=1,
            value=MusicUtils.inv_log_scale(
                MusicUtils.snap_to_c(self.generator.min_freq),
                self.min_freq_bound, self.max_freq_bound
            ),
            command=self._update_min_freq
        )
        self.min_freq.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(freq_frame, textvariable=self.min_freq_var, width=8).pack(side=tk.LEFT)
        self.min_freq_var.set(f"{MusicUtils.snap_to_c(self.generator.min_freq):.1f} Hz")
        
        ttk.Label(freq_frame, text="Max Freq:").pack(side=tk.LEFT)
        self.max_freq = ttk.Scale(
            freq_frame,
            from_=0,
            to=1,
            value=MusicUtils.inv_log_scale(
                MusicUtils.snap_to_c(self.generator.max_freq),
                self.min_freq_bound, self.max_freq_bound
            ),
            command=self._update_max_freq
        )
        self.max_freq.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(freq_frame, textvariable=self.max_freq_var, width=8).pack(side=tk.LEFT)
        self.max_freq_var.set(f"{MusicUtils.snap_to_c(self.generator.max_freq):.1f} Hz")

    def _create_group(self):
        group_name = self.group_name_entry.get().strip()
        trigger_key = self.group_key_entry.get().strip()
        
        if not group_name:
            messagebox.showerror("Error", "Group name cannot be empty")
            return
        
        try:
            self.generator.create_group(group_name, trigger_key)
            self.harmonics_container.rebuild_ui()
            self.group_name_entry.delete(0, tk.END)
            self.group_key_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _add_harmonic(self, event=None):
        try:
            mult = float(self.harmonic_entry.get())
            if mult not in [h.multiplier for h in self.generator.harmonics]:
                self.generator.add_harmonic(mult)
                self.harmonics_container.rebuild_ui()
                self.harmonic_entry.delete(0, tk.END)
        except ValueError:
            pass

    def _update_min_freq(self, value):
        # Convert linear slider position (0-1) to logarithmic frequency
        freq = MusicUtils.log_scale(float(value), self.min_freq_bound, self.max_freq_bound)
        snapped_freq = MusicUtils.snap_to_c(freq)
        
        if abs(self.generator.min_freq - snapped_freq) > 0.1:
            self.generator.min_freq = snapped_freq
            self.min_freq_var.set(f"{snapped_freq:.1f} Hz")
            
            # Update slider position to snapped value
            original_cmd = self.min_freq.cget('command')
            self.min_freq.config(command=lambda v: None)
            self.min_freq.set(MusicUtils.inv_log_scale(
                snapped_freq, self.min_freq_bound, self.max_freq_bound))
            self.min_freq.config(command=original_cmd)

    def _update_max_freq(self, value):
        # Convert linear slider position (0-1) to logarithmic frequency
        freq = MusicUtils.log_scale(float(value), self.min_freq_bound, self.max_freq_bound)
        snapped_freq = MusicUtils.snap_to_c(freq)
        
        if abs(self.generator.max_freq - snapped_freq) > 0.1:
            self.generator.max_freq = snapped_freq
            self.max_freq_var.set(f"{snapped_freq:.1f} Hz")
            
            # Update slider position to snapped value
            original_cmd = self.max_freq.cget('command')
            self.max_freq.config(command=lambda v: None)
            self.max_freq.set(MusicUtils.inv_log_scale(
                snapped_freq, self.min_freq_bound, self.max_freq_bound))
            self.max_freq.config(command=original_cmd)

    def _setup_audio(self):
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

    def _setup_updater(self):
        def update_all():
            # Find all HarmonicControl widgets in the UI
            def find_harmonic_controls(widget):
                controls = []
                for child in widget.winfo_children():
                    if isinstance(child, HarmonicControl):
                        controls.append(child)
                    else:
                        controls.extend(find_harmonic_controls(child))
                return controls
            
            controls = find_harmonic_controls(self.harmonics_container.inner_frame)
            for control in controls:
                control.update_display()
                
            self.after(100, update_all)
        
        update_all()

    def on_closing(self):
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'pa'):
            self.pa.terminate()
        if hasattr(self, 'mouse_listener'):
            self.mouse_listener.stop()
        self.destroy()