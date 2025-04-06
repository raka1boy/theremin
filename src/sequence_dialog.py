import tkinter as tk
from tkinter import ttk, messagebox

class SequenceDialog:
    def __init__(self, parent, initial_value):
        self.top = tk.Toplevel(parent)
        self.top.title("Generate Harmonic Sequence")
        self.result = None
        
        self._setup_ui(initial_value)

    def _setup_ui(self, initial_value):
        main_frame = ttk.Frame(self.top, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Code input
        ttk.Label(main_frame, text="Python expression (use 'x' as input):").pack(anchor=tk.W)
        self.code_entry = ttk.Entry(main_frame, width=40)
        self.code_entry.pack(fill=tk.X, pady=(0,10))
        self.code_entry.insert(0, f"x * {initial_value}")  # Default example
        
        # Iterations input
        ttk.Label(main_frame, text="Number of harmonics to generate:").pack(anchor=tk.W)
        self.iterations_entry = ttk.Entry(main_frame, width=10)
        self.iterations_entry.pack(fill=tk.X, pady=(0,10))
        self.iterations_entry.insert(0, "3")  # Default value
        
        # Example label
        example_text = "Example: x*2 (will double frequency each time)"
        ttk.Label(main_frame, text=example_text, font=('TkDefaultFont', 9)).pack(anchor=tk.W, pady=(0,10))
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10,0))
        
        ttk.Button(button_frame, text="Generate", 
                  command=self._on_generate).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=self._on_cancel).pack(side=tk.RIGHT)

    def _on_generate(self):
        code_str = self.code_entry.get().strip()
        iterations_str = self.iterations_entry.get().strip()
        
        if not code_str or not iterations_str:
            messagebox.showerror("Error", "Both fields are required")
            return
        
        try:
            iterations = int(iterations_str)
            if iterations <= 0 or iterations > 20:  # Reasonable limit
                raise ValueError("Iterations must be between 1 and 20")
        except ValueError:
            messagebox.showerror("Error", "Iterations must be a positive integer (max 20)")
            return
        
        # Basic code validation
        if not all(c.isalnum() or c in ' x_().*+-/^%' for c in code_str):
            messagebox.showerror("Error", "Code contains invalid characters")
            return
        
        self.result = (code_str, iterations)
        self.top.destroy()

    def _on_cancel(self):
        self.top.destroy()