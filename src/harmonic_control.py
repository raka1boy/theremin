import tkinter as tk
from tkinter import ttk
from utils import MusicUtils
from sequence_dialog import SequenceDialog
from tkinter import messagebox

class HarmonicControl(ttk.Frame):
    def __init__(self, parent, generator, multiplier, on_remove=None):
        super().__init__(parent)
        self.generator = generator
        self.multiplier = multiplier
        self.on_remove = on_remove
        self.snap_to_note = tk.BooleanVar(value=False)
        self.multiplier_var = tk.StringVar(value=str(multiplier))
        self.pitch_smooth_value = tk.StringVar()
        self.note_var = tk.StringVar()
        self.freq_var = tk.StringVar()
        self.group_var = tk.StringVar()

        
        self._setup_ui()
        self._initialize_values()
        self.update_display()

    def _setup_ui(self):
        # Configure grid columns with weights for proper spacing
        for col in [1, 3, 5, 7, 11]:
            self.columnconfigure(col, weight=1)

        # Multiplier controls
        ttk.Label(self, text="Mult:").grid(row=0, column=0, padx=(5,0), sticky='e')
        self.multiplier_entry = ttk.Entry(self, textvariable=self.multiplier_var, width=6)
        self.multiplier_entry.grid(row=0, column=1, padx=5, sticky='ew')
        ttk.Button(self, text="✏️", width=3, command=self._edit_multiplier).grid(row=0, column=2, padx=(0,5))
        ttk.Button(self, text="+Seq", width=4, command=self._open_sequence_dialog).grid(row=0, column=15, padx=(0,5))

        # Amplitude controls
        ttk.Label(self, text="Amp:").grid(row=0, column=3, padx=(5,0), sticky='e')
        self.amp_slider = ttk.Scale(self, from_=0, to=1, command=self._on_amp_change)
        self.amp_slider.grid(row=0, column=4, sticky="ew", padx=5)

        # Amplitude smoothing
        ttk.Label(self, text="Amp Smooth:").grid(row=0, column=5, padx=(5,0), sticky='e')
        self.amp_smoothing_slider = ttk.Scale(
            self, from_=0, to=1000, command=self._on_amp_smoothing_change)
        self.amp_smoothing_slider.grid(row=0, column=6, sticky="ew", padx=5)

        # Pitch smoothing
        ttk.Label(self, text="Pitch Smooth:").grid(row=0, column=7, padx=(5,0), sticky='e')
        self.pitch_smoothing_slider = ttk.Scale(
            self, from_=0, to=50, command=self._on_pitch_smoothing_change)
        self.pitch_smoothing_slider.grid(row=0, column=8, sticky="ew", padx=5)
        ttk.Label(self, textvariable=self.pitch_smooth_value, width=5).grid(row=0, column=9, padx=(0,5))

        # Note and frequency display
        ttk.Label(self, textvariable=self.note_var, width=8).grid(row=0, column=10, padx=5)
        ttk.Label(self, textvariable=self.freq_var, width=8).grid(row=0, column=11, padx=5)

        # Snap checkbox
        self.snap_cb = ttk.Checkbutton(
            self, text="Snap", variable=self.snap_to_note, command=self._on_snap_change)
        self.snap_cb.grid(row=0, column=12, padx=5)

        # Group assignment dropdown
        self.group_dropdown = ttk.Combobox(
            self, textvariable=self.group_var, width=12, state='readonly')
        self.group_dropdown.grid(row=0, column=13, padx=5)
        self.group_dropdown.bind('<<ComboboxSelected>>', self._on_group_selected)
        self._update_group_dropdown()

        # Remove button
        ttk.Button(self, text="×", width=2, command=self._remove_harmonic).grid(row=0, column=14, padx=(5,10))

    def _open_sequence_dialog(self):
        dialog = SequenceDialog(self, self.multiplier)
        self.wait_window(dialog.top)
        
        if dialog.result:
            code_str, iterations = dialog.result
            self._generate_harmonic_sequence(code_str, iterations)

    def _generate_harmonic_sequence(self, code_str, iterations):
        current_value = self.multiplier
        try:
            # Safely evaluate the code with limited globals
            safe_globals = {
                '__builtins__': None,
                'math': __import__('math'),
                'x': current_value  # Initial value for first iteration
            }
            
            for i in range(iterations):
                try:
                    # Evaluate the code with current_value as 'x'
                    safe_globals['x'] = current_value  # Update x for each iteration
                    new_value = eval(code_str, safe_globals)
                    
                    if not isinstance(new_value, (int, float)):
                        raise ValueError(f"Code must evaluate to a number, got {type(new_value)}")
                    
                    # Add the new harmonic with same settings as parent
                    idx = self.generator._get_harmonic_index(self.multiplier)
                    if idx != -1:
                        parent_harmonic = self.generator.harmonics[idx]
                        self.generator.add_harmonic(
                            multiplier=new_value,
                            initial_amp=parent_harmonic.initial_amp,
                            amp_smoothing=parent_harmonic.amp_smoothing,
                            pitch_smoothing=parent_harmonic.pitch_smoothing,
                            trigger_key=parent_harmonic.trigger_key
                        )
                        
                        # Copy snap setting
                        new_idx = self.generator._get_harmonic_index(new_value)
                        if new_idx != -1:
                            self.generator.harmonics[new_idx].snap_enabled = parent_harmonic.snap_enabled
                    
                    current_value = new_value
                
                except Exception as e:
                    error_msg = (
                        f"Error in iteration {i + 1}:\n"
                        f"Expression: {code_str}\n"
                        f"Current value (x): {current_value}\n"
                        f"Error: {str(e)}"
                    )
                    messagebox.showerror("Sequence Generation Error", error_msg)
                    return
            
            # Trigger UI rebuild
            parent = self.master
            while parent and not hasattr(parent, 'rebuild_ui'):
                parent = parent.master
            if parent:
                parent.rebuild_ui()
                
        except Exception as e:
            error_msg = (
                f"Initialization error:\n"
                f"Expression: {code_str}\n"
                f"Starting value: {self.multiplier}\n"
                f"Error: {str(e)}"
            )
            messagebox.showerror("Sequence Generation Error", error_msg)

    def _initialize_values(self):
        idx = self.generator._get_harmonic_index(self.multiplier)
        if idx != -1:
            harmonic = self.generator.harmonics[idx]
            self.snap_to_note.set(harmonic.snap_enabled)
            self.amp_slider.set(harmonic.initial_amp)
            self.amp_smoothing_slider.set(harmonic.amp_smoothing)
            self.pitch_smoothing_slider.set(harmonic.pitch_smoothing)
            self.pitch_smooth_value.set(f"{int(harmonic.pitch_smoothing)}ms")

    def _edit_multiplier(self):
        try:
            new_mult = float(self.multiplier_var.get())
            if new_mult != self.multiplier and new_mult > 0:
                if self.generator.update_harmonic_multiplier(self.multiplier, new_mult):
                    self.multiplier = new_mult
                    if hasattr(self.master.master, 'rebuild_ui'):
                        self.master.master.rebuild_ui()
                else:
                    self.multiplier_var.set(str(self.multiplier))
        except ValueError:
            self.multiplier_var.set(str(self.multiplier))

    def _update_group_dropdown(self):
        current_groups = list(self.generator.groups.keys())
        self.group_dropdown['values'] = ['(No group)'] + current_groups
        current_group = self.generator.get_group_for_harmonic(self.multiplier)
        self.group_var.set(current_group if current_group else '(No group)')

    def _on_group_selected(self, event=None):
        selected = self.group_var.get()
        if selected == '(No group)':
            self.generator.remove_from_group(self.multiplier)
        else:
            self.generator.assign_to_group(self.multiplier, selected)
        
        parent = self.master
        while parent and not hasattr(parent, 'rebuild_ui'):
            parent = parent.master
        if parent:
            parent.rebuild_ui()

    def _remove_harmonic(self):
        self.generator.remove_harmonic(self.multiplier)
        if self.on_remove:
            self.on_remove(self.multiplier)

    def _on_amp_change(self, value):
        idx = self.generator._get_harmonic_index(self.multiplier)
        if idx != -1:
            self.generator.harmonics[idx].initial_amp = max(0.0, min(1.0, float(value)))
            self.update_display()

    def _on_amp_smoothing_change(self, value):
        idx = self.generator._get_harmonic_index(self.multiplier)
        if idx != -1:
            self.generator.harmonics[idx].amp_smoothing = max(0.0, float(value))

    def _on_pitch_smoothing_change(self, value):
        idx = self.generator._get_harmonic_index(self.multiplier)
        if idx != -1:
            val = max(0.0, float(value))
            self.generator.harmonics[idx].pitch_smoothing = val
            self.pitch_smooth_value.set(f"{int(val)}ms")

    def _on_snap_change(self):
        idx = self.generator._get_harmonic_index(self.multiplier)
        if idx != -1:
            self.generator.harmonics[idx].snap_enabled = self.snap_to_note.get()
            self.update_display()

    def update_display(self):
        idx = self.generator._get_harmonic_index(self.multiplier)
        if idx != -1:
            display_freq = self.generator.harmonics[idx].current_freq
            note_info = MusicUtils.note_from_freq(display_freq)
            self.note_var.set(f"{note_info[0]}{note_info[1]}" if note_info else "")
            self.freq_var.set(f"{display_freq:.1f} Hz")
        else:
            self.note_var.set("")
            self.freq_var.set("")