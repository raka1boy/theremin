import numpy as np
import pyaudio
import keyboard
from pynput import mouse
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
from sine_gen import snap_frequency
import json
from copy import deepcopy

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
    if freq <= 0:
        return freq
    C0 = 16.35
    octaves = np.log2(freq / C0)
    nearest_octave = round(octaves)
    return C0 * (2 ** nearest_octave)

class GroupHeader(ttk.Frame):
    def __init__(self, parent, generator, group_name, on_edit, on_copy, on_remove):
        super().__init__(parent)
        self.generator = generator
        self.container = parent  # Store reference to the container
        self.group_name = group_name
        self.on_edit = on_edit
        self.on_copy = on_copy
        self.on_remove = on_remove
        
        self.configure(style='Group.TFrame')
        
        ttk.Label(self, text=f"Group: {group_name}", style='GroupHeader.TLabel').pack(side=tk.LEFT, padx=5)
        
        self.trigger_key = self.generator.groups[group_name]['trigger_key']
        self.key_label = ttk.Label(self, text=f"Key: {self.trigger_key}", style='GroupHeader.TLabel')
        self.key_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(self, text="✏️", width=3, 
                  command=lambda: self.on_edit(group_name)).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(self, text="⎘", width=3, 
                  command=lambda: self.on_copy(group_name)).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(self, text="×", width=3, 
                  command=lambda: self.on_remove(group_name)).pack(side=tk.LEFT, padx=2)
        
        self.expand_btn = ttk.Button(self, text="▼", width=3, command=self.toggle_expand)
        self.expand_btn.pack(side=tk.RIGHT, padx=5)
        self.expanded = True
    
    def toggle_expand(self):
        self.expanded = not self.expanded
        self.expand_btn.config(text="▼" if self.expanded else "▶")
        # Toggle visibility of all widgets after the header
        for widget in self.container.winfo_children()[1:]:  # Skip header
            if self.expanded:
                widget.pack(fill=tk.X, padx=20)
            else:
                widget.pack_forget()
    
    def update_key_display(self):
        self.trigger_key = self.generator.groups[self.group_name]['trigger_key']
        self.key_label.config(text=f"Key: {self.trigger_key}")

class HarmonicControl(ttk.Frame):
    def __init__(self, parent, generator, multiplier, on_remove=None):
        super().__init__(parent)
        self.generator = generator
        self.multiplier = multiplier
        self.on_remove = on_remove
        self.snap_to_note = tk.BooleanVar(value=False)
        
        for col in [1, 3, 5]:
            self.columnconfigure(col, weight=1)
        
        ttk.Label(self, text=f"{multiplier}x").grid(row=0, column=0, padx=5, sticky='w')
        
        ttk.Label(self, text="Amp:").grid(row=0, column=1, padx=(10,0), sticky='e')
        self.amp_slider = ttk.Scale(
            self, from_=0, to=1, value=1.0,
            command=lambda v: [self.generator.set_harmonic_amp(self.multiplier, float(v)),
                              self.update_display()]
        )
        self.amp_slider.grid(row=0, column=2, sticky="ew", padx=5)
        
        ttk.Label(self, text="Amp Smooth:").grid(row=0, column=3, padx=(10,0), sticky='e')
        self.amp_smoothing_slider = ttk.Scale(
            self, from_=0, to=1000, value=100,
            command=lambda v: self.generator.set_harmonic_amp_smoothing(self.multiplier, float(v))
        )
        self.amp_smoothing_slider.grid(row=0, column=4, sticky="ew", padx=5)
        
        ttk.Label(self, text="Pitch Smooth:").grid(row=0, column=5, padx=(10,0), sticky='e')
        self.pitch_smoothing_slider = ttk.Scale(
            self, from_=0, to=50, value=0,
            command=lambda v: [
                self.generator.set_harmonic_pitch_smoothing(self.multiplier, float(v)),
                self.pitch_smooth_value.set(f"{int(float(v))}ms")
            ]
        )
        self.pitch_smoothing_slider.grid(row=0, column=6, sticky="ew", padx=5)

        self.pitch_smooth_value = tk.StringVar()
        self.pitch_smooth_value.set("0ms")
        ttk.Label(self, textvariable=self.pitch_smooth_value, width=5).grid(row=0, column=7, padx=(0,5))
        
        self.note_var = tk.StringVar()
        ttk.Label(self, textvariable=self.note_var, width=8).grid(row=0, column=8, padx=5)
        
        self.freq_var = tk.StringVar()
        ttk.Label(self, textvariable=self.freq_var, width=8).grid(row=0, column=9, padx=5)
        
        self.snap_cb = ttk.Checkbutton(
            self, text="Snap", variable=self.snap_to_note,
            command=lambda: [self.generator.set_harmonic_snap(self.multiplier, self.snap_to_note.get()),
                            self.update_display()]
        )
        self.snap_cb.grid(row=0, column=10, padx=5)
        
        # Group assignment dropdown
        self.group_var = tk.StringVar()
        self.group_dropdown = ttk.Combobox(
            self, textvariable=self.group_var, width=12, state='readonly'
        )
        self.group_dropdown.grid(row=0, column=11, padx=5)
        self.group_dropdown.bind('<<ComboboxSelected>>', self.on_group_selected)
        self.update_group_dropdown()
        
        ttk.Button(self, text="×", width=2, command=self.remove_harmonic).grid(row=0, column=12, padx=5)
        
        if multiplier in self.generator.harmonics:
            idx = self.generator.harmonics.index(multiplier)
            self.snap_to_note.set(self.generator.snap_enabled[idx])
            self.amp_slider.set(self.generator.harmonic_amps[idx])
            self.amp_smoothing_slider.set(self.generator.harmonic_amp_smoothing[idx])
            self.pitch_smoothing_slider.set(self.generator.harmonic_pitch_smoothing[idx])

    def update_group_dropdown(self):
        current_groups = list(self.generator.groups.keys())
        self.group_dropdown['values'] = ['(No group)'] + current_groups
        
        current_group = self.generator.get_group_for_harmonic(self.multiplier)
        if current_group:
            self.group_var.set(current_group)
        else:
            self.group_var.set('(No group)')

    def on_group_selected(self, event=None):
        selected = self.group_var.get()
        if selected == '(No group)':
            self.generator.remove_from_group(self.multiplier)
        else:
            self.generator.assign_to_group(self.multiplier, selected)
        # Find the HarmonicsContainer in the parent hierarchy
        parent = self.master
        while parent and not hasattr(parent, 'rebuild_ui'):
            parent = parent.master
        if parent:
            parent.rebuild_ui()

    def remove_harmonic(self):
        self.generator.remove_harmonic(self.multiplier)
        if self.on_remove:
            self.on_remove(self.multiplier)

    def update_display(self):
        try:
            if self.multiplier in self.generator.harmonics:
                idx = self.generator.harmonics.index(self.multiplier)
                display_freq = self.generator.current_freqs[idx]
                note_info = note_from_freq(display_freq)
                self.note_var.set(f"{note_info[0]}{note_info[1]}" if note_info else "")
                self.freq_var.set(f"{display_freq:.1f} Hz")
            else:
                self.note_var.set("")
                self.freq_var.set("")
        except (ValueError, IndexError):
            self.note_var.set("")
            self.freq_var.set("")

class HarmonicsContainer(ttk.Frame):
    def __init__(self, parent, generator):
        super().__init__(parent)
        self.generator = generator
        self.group_frames = {}
        
        style = ttk.Style()
        style.configure('Group.TFrame', background='#f0f0f0')
        style.configure('GroupHeader.TLabel', background='#f0f0f0', font=('Helvetica', 10, 'bold'))
        
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.inner_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        
        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.rebuild_ui()

    def rebuild_ui(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        
        self.group_frames = {}
        
        ungrouped = [m for m in self.generator.harmonics 
                    if not self.generator.get_group_for_harmonic(m)]
        
        if ungrouped:
            ttk.Label(self.inner_frame, text="Ungrouped Harmonics", font=('Helvetica', 10, 'bold')).pack(fill=tk.X, pady=(5,0))
            for mult in ungrouped:
                control = HarmonicControl(self.inner_frame, self.generator, mult, 
                                        on_remove=self.on_harmonic_removed)
                control.pack(fill=tk.X, pady=2, padx=10)
        
        for group_name in self.generator.groups:
            self.add_group_ui(group_name)
        
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def add_group_ui(self, group_name):
        group_data = self.generator.groups[group_name]
        
        group_container = ttk.Frame(self.inner_frame)
        group_container.pack(fill=tk.X, pady=(10,0))
        self.group_frames[group_name] = group_container
        
        header = GroupHeader(
            group_container, self.generator, group_name,
            on_edit=self.on_group_edit,
            on_copy=self.on_group_copy,
            on_remove=self.on_group_remove
        )
        header.pack(fill=tk.X, padx=5, pady=5)
        
        harmonics_frame = ttk.Frame(group_container)
        harmonics_frame.pack(fill=tk.X, padx=20)
        
        for mult in group_data['harmonics']:
            if mult in self.generator.harmonics:
                control = HarmonicControl(harmonics_frame, self.generator, mult, 
                                        on_remove=self.on_harmonic_removed)
                control.pack(fill=tk.X, pady=2)


    def add_group_ui(self, group_name):
        group_data = self.generator.groups[group_name]
        
        group_container = ttk.Frame(self.inner_frame)
        group_container.pack(fill=tk.X, pady=(10,0))
        self.group_frames[group_name] = group_container
        
        header = GroupHeader(
            group_container,  # Pass the container as parent
            self.generator, 
            group_name,
            on_edit=self.on_group_edit,
            on_copy=self.on_group_copy,
            on_remove=self.on_group_remove
        )
        header.pack(fill=tk.X, padx=5, pady=5)
        
        harmonics_frame = ttk.Frame(group_container)
        harmonics_frame.pack(fill=tk.X, padx=20)
        
        for mult in group_data['harmonics']:
            if mult in self.generator.harmonics:
                control = HarmonicControl(harmonics_frame, self.generator, mult, 
                                        on_remove=self.on_harmonic_removed)
                control.pack(fill=tk.X, pady=2)

    def on_harmonic_removed(self, multiplier):
        self.rebuild_ui()

    def on_group_edit(self, group_name):
        new_key = simpledialog.askstring(
            "Edit Group Trigger",
            f"Enter new trigger key for group '{group_name}':",
            initialvalue=self.generator.groups[group_name]['trigger_key']
        )
        if new_key:
            self.generator.set_group_key(group_name, new_key)
            self.rebuild_ui()

    def on_group_copy(self, group_name):
        new_name = simpledialog.askstring(
            "Copy Group",
            f"Enter name for copied group:",
            initialvalue=f"{group_name}_copy"
        )
        if new_name:
            try:
                # Create new group with same trigger key
                original_group = self.generator.groups[group_name]
                self.generator.create_group(new_name, original_group['trigger_key'])
                
                # Create new harmonics with slightly modified multipliers
                for mult in original_group['harmonics']:
                    if mult in self.generator.harmonics:
                        idx = self.generator.harmonics.index(mult)
                        
                        # Create a new unique multiplier (add 0.1 to original)
                        new_mult = mult + 0.1
                        while new_mult in self.generator.harmonics:
                            new_mult += 0.1
                        
                        # Add new harmonic with same settings
                        self.generator.add_harmonic(
                            multiplier=new_mult,
                            initial_amp=self.generator.harmonic_amps[idx],
                            amp_smoothing=self.generator.harmonic_amp_smoothing[idx],
                            pitch_smoothing=self.generator.harmonic_pitch_smoothing[idx],
                            trigger_key=self.generator.harmonic_keys[idx]
                        )
                        
                        # Copy snap setting
                        self.generator.set_harmonic_snap(new_mult, self.generator.snap_enabled[idx])
                        
                        # Add to new group
                        self.generator.assign_to_group(new_mult, new_name)
                
                self.rebuild_ui()
                messagebox.showinfo("Success", f"Group '{group_name}' copied to '{new_name}' with new harmonics")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def on_group_remove(self, group_name):
        self.generator.remove_group(group_name)
        self.rebuild_ui()

class ControlUI(tk.Tk):
    def __init__(self, generator):
        super().__init__()
        self.generator = generator
        self.generator.screen_x = self.winfo_screenwidth()
        self.generator.screen_y = self.winfo_screenheight()
        self.title("Theremin")
        self.geometry("1200x700")
        
        self.min_freq_var = tk.StringVar()
        self.max_freq_var = tk.StringVar()
        
        self.setup_ui()
        self.setup_audio()
        self.setup_updater()

    def setup_ui(self):
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(self.main_frame, text="Multiplier").pack(pady=5)
        entry_frame = ttk.Frame(self.main_frame)
        entry_frame.pack(fill=tk.X)
        
        self.harmonic_entry = ttk.Entry(entry_frame)
        self.harmonic_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.harmonic_entry.bind('<Return>', self.add_harmonic)
        
        ttk.Button(entry_frame, text="+", command=self.add_harmonic).pack(side=tk.LEFT)
        
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
            command=self.create_group
        ).pack(side=tk.LEFT, padx=5)
        
        self.harmonics_container = HarmonicsContainer(self.main_frame, self.generator)
        self.harmonics_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        global_controls = ttk.Frame(self.main_frame)
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
            command=lambda: ConfigManager.load_config(self.generator, self, self.harmonics_container.rebuild_ui)
        ).pack(side=tk.LEFT, padx=5)
        
        freq_frame = ttk.Frame(self.main_frame)
        freq_frame.pack(fill=tk.X, pady=5)
        
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

    def create_group(self):
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

    def add_harmonic(self, event=None):
        try:
            mult = float(self.harmonic_entry.get())
            if mult not in self.generator.harmonics:
                self.generator.add_harmonic(mult)
                self.harmonics_container.rebuild_ui()
                self.harmonic_entry.delete(0, tk.END)
        except ValueError:
            pass

    def update_min_freq(self, value):
        snapped_freq = snap_to_c(float(value))
        if abs(self.generator.min_freq - snapped_freq) > 0.1:
            self.generator.min_freq = snapped_freq
            self.min_freq_var.set(f"{snapped_freq:.1f} Hz")
            original_cmd = self.min_freq.cget('command')
            self.min_freq.config(command=lambda v: None)
            self.min_freq.set(snapped_freq)
            self.min_freq.config(command=original_cmd)

    def update_max_freq(self, value):
        snapped_freq = snap_to_c(float(value))
        if abs(self.generator.max_freq - snapped_freq) > 0.1:
            self.generator.max_freq = snapped_freq
            self.max_freq_var.set(f"{snapped_freq:.1f} Hz")
            original_cmd = self.max_freq.cget('command')
            self.max_freq.config(command=lambda v: None)
            self.max_freq.set(snapped_freq)
            self.max_freq.config(command=original_cmd)

    def setup_updater(self):
        def update_all():
            for child in self.harmonics_container.inner_frame.winfo_children():
                if isinstance(child, HarmonicControl):
                    child.update_display()
                else:  # For group containers
                    for subchild in child.winfo_children():
                        if isinstance(subchild, HarmonicControl):
                            subchild.update_display()
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

class ConfigManager:
    @staticmethod
    def save_config(generator, parent_window):
        config = {
            'min_freq': generator.min_freq,
            'max_freq': generator.max_freq,
            'global_amp_smoothing': generator.global_amp_smoothing,
            'global_pitch_smoothing': generator.global_pitch_smoothing,
            'harmonics': [],
            'groups': generator.groups
        }
        
        for i, mult in enumerate(generator.harmonics):
            config['harmonics'].append({
                'multiplier': mult,
                'amplitude': generator.harmonic_amps[i],
                'amp_smoothing': generator.harmonic_amp_smoothing[i],
                'pitch_smoothing': generator.harmonic_pitch_smoothing[i],
                'snap_enabled': generator.snap_enabled[i],
                'trigger_key': generator.harmonic_keys[i]
            })
        
        filepath = filedialog.asksaveasfilename(
            parent=parent_window,
            defaultextension='.json',
            filetypes=[('JSON config files', '*.json')],
            title='Save configuration'
        )
        
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    json.dump(config, f, indent=4)
                messagebox.showinfo('Success', 'Configuration saved successfully!', parent=parent_window)
            except Exception as e:
                messagebox.showerror('Error', f'Failed to save configuration:\n{str(e)}', parent=parent_window)

    @staticmethod
    def load_config(generator, parent_window, ui_callback=None):
        filepath = filedialog.askopenfilename(
            parent=parent_window,
            defaultextension='.json',
            filetypes=[('JSON config files', '*.json')],
            title='Load configuration'
        )
        
        if not filepath:
            return False
        
        try:
            with open(filepath, 'r') as f:
                config = json.load(f)
            
            for mult in generator.harmonics[:]:
                generator.remove_harmonic(mult)
            
            generator.min_freq = float(config.get('min_freq', generator.min_freq))
            generator.max_freq = float(config.get('max_freq', generator.max_freq))
            generator.global_amp_smoothing = float(config.get('global_amp_smoothing', generator.global_amp_smoothing))
            generator.global_pitch_smoothing = float(config.get('global_pitch_smoothing', generator.global_pitch_smoothing))
            
            generator.groups = config.get('groups', {})
            generator.group_assignments = {}
            
            for harmonic in config.get('harmonics', []):
                mult = float(harmonic['multiplier'])
                generator.add_harmonic(
                    multiplier=mult,
                    initial_amp=float(harmonic.get('amplitude', 1.0)),
                    amp_smoothing=float(harmonic.get('amp_smoothing', 100)),
                    pitch_smoothing=float(harmonic.get('pitch_smoothing', 50)),
                    trigger_key=harmonic.get('trigger_key', 'space')
                )
                generator.set_harmonic_snap(mult, bool(harmonic.get('snap_enabled', False)))
            
            for group_name, group_data in generator.groups.items():
                for mult in group_data['harmonics']:
                    if mult in generator.harmonics:
                        generator.group_assignments[mult] = group_name
            
            if ui_callback:
                ui_callback()
            
            messagebox.showinfo('Success', 'Configuration loaded successfully!', parent=parent_window)
            return True
            
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load configuration:\n{str(e)}', parent=parent_window)
            return False