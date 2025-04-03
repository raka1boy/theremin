import json
import os
from tkinter import filedialog, messagebox

class ConfigManager:
    @staticmethod
    def save_config(generator, parent_window):
        """Save current configuration to a JSON file"""
        config = {
            'min_freq': generator.min_freq,
            'max_freq': generator.max_freq,
            'global_amp_smoothing': generator.global_amp_smoothing,
            'global_pitch_smoothing': generator.global_pitch_smoothing,
            'harmonics': []
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
        """Load configuration from a JSON file"""
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
            
            # Clear existing harmonics
            for mult in generator.harmonics[:]:
                generator.remove_harmonic(mult)
            
            # Set global parameters
            generator.min_freq = float(config.get('min_freq', generator.min_freq))
            generator.max_freq = float(config.get('max_freq', generator.max_freq))
            generator.global_amp_smoothing = float(config.get('global_amp_smoothing', generator.global_amp_smoothing))
            generator.global_pitch_smoothing = float(config.get('global_pitch_smoothing', generator.global_pitch_smoothing))
            
            # Add harmonics
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
            
            if ui_callback:
                ui_callback()
            
            messagebox.showinfo('Success', 'Configuration loaded successfully!', parent=parent_window)
            return True
            
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load configuration:\n{str(e)}', parent=parent_window)
            return False