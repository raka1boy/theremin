import json
import tkinter as tk
from tkinter import filedialog, messagebox

class ConfigManager:
    @staticmethod
    def save_config(generator, parent_window):
        config = {
            'min_freq': generator.min_freq,
            'max_freq': generator.max_freq,
            'global_amp_smoothing': generator.global_amp_smoothing,
            'global_pitch_smoothing': generator.global_pitch_smoothing,
            'harmonics': [],
            'groups': {name: {'trigger_key': group.trigger_key, 'harmonics': group.harmonics} 
                      for name, group in generator.groups.items()}
        }
        
        for harmonic in generator.harmonics:
            config['harmonics'].append({
                'multiplier': harmonic.multiplier,
                'amplitude': harmonic.initial_amp,
                'amp_smoothing': harmonic.amp_smoothing,
                'pitch_smoothing': harmonic.pitch_smoothing,
                'snap_enabled': harmonic.snap_enabled,
                'trigger_key': harmonic.trigger_key
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
            
            # Clear existing data
            for harmonic in generator.harmonics[:]:
                generator.remove_harmonic(harmonic.multiplier)
            
            generator.min_freq = float(config.get('min_freq', generator.min_freq))
            generator.max_freq = float(config.get('max_freq', generator.max_freq))
            generator.global_amp_smoothing = float(config.get('global_amp_smoothing', generator.global_amp_smoothing))
            generator.global_pitch_smoothing = float(config.get('global_pitch_smoothing', generator.global_pitch_smoothing))
            
            # Recreate groups
            generator.groups = {}
            generator.group_assignments = {}
            for group_name, group_data in config.get('groups', {}).items():
                generator.create_group(group_name, group_data['trigger_key'], group_data['harmonics'])
            
            # Recreate harmonics
            for harmonic_data in config.get('harmonics', []):
                mult = float(harmonic_data['multiplier'])
                generator.add_harmonic(
                    multiplier=mult,
                    initial_amp=float(harmonic_data.get('amplitude', 1.0)),
                    amp_smoothing=float(harmonic_data.get('amp_smoothing', 100)),
                    pitch_smoothing=float(harmonic_data.get('pitch_smoothing', 1)),
                    trigger_key=harmonic_data.get('trigger_key', 'space')
                )
                idx = generator._get_harmonic_index(mult)
                if idx != -1:
                    generator.harmonics[idx].snap_enabled = bool(harmonic_data.get('snap_enabled', False))
            
            if ui_callback:
                ui_callback()
            
            messagebox.showinfo('Success', 'Configuration loaded successfully!', parent=parent_window)
            return True
            
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load configuration:\n{str(e)}', parent=parent_window)
            return False