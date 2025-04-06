import tkinter as tk
from tkinter import ttk

class GroupHeader(ttk.Frame):
    def __init__(self, parent, generator, group_name, on_edit, on_copy, on_remove):
        super().__init__(parent)
        self.generator = generator
        self.container = parent
        self.group_name = group_name
        self.on_edit = on_edit
        self.on_copy = on_copy
        self.on_remove = on_remove
        self.expanded = True

        self._setup_ui()

    def _setup_ui(self):
        self.configure(style='Group.TFrame')
        
        ttk.Label(self, text=f"Group: {self.group_name}", style='GroupHeader.TLabel').pack(side=tk.LEFT, padx=5)
        
        self.trigger_key = self.generator.groups[self.group_name].trigger_key
        self.key_label = ttk.Label(self, text=f"Key: {self.trigger_key}", style='GroupHeader.TLabel')
        self.key_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(self, text="✏️", width=3, command=lambda: self.on_edit(self.group_name)).pack(side=tk.LEFT, padx=2)
        ttk.Button(self, text="⎘", width=3, command=lambda: self.on_copy(self.group_name)).pack(side=tk.LEFT, padx=2)
        ttk.Button(self, text="×", width=3, command=lambda: self.on_remove(self.group_name)).pack(side=tk.LEFT, padx=2)
        
        self.expand_btn = ttk.Button(self, text="▼", width=3, command=self._toggle_expand)
        self.expand_btn.pack(side=tk.RIGHT, padx=5)

    def _toggle_expand(self):
        self.expanded = not self.expanded
        self.expand_btn.config(text="▼" if self.expanded else "▶")
        for widget in self.container.winfo_children()[1:]:  # Skip header
            if self.expanded:
                widget.pack(fill=tk.X, padx=20)
            else:
                widget.pack_forget()

    def update_key_display(self):
        self.trigger_key = self.generator.groups[self.group_name].trigger_key
        self.key_label.config(text=f"Key: {self.trigger_key}")