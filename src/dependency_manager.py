import sys
import subprocess
import importlib

class DependencyManager:
    @staticmethod
    def install_dependencies():
        required = [
            ('numpy', 'numpy'),
            ('pyaudio', 'pyaudio'),
            ('keyboard', 'keyboard'),
            ('pynput', 'pynput'),
            ('tkinter', 'tkinter')  # Usually comes with Python
        ]
        
        missing = []
        for (import_name, package_name) in required:
            try:
                importlib.import_module(import_name)
            except ImportError:
                missing.append(package_name)
        
        if missing:
            print(f"Installing missing dependencies: {', '.join(missing)}")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
                print("Dependencies installed successfully!")
            except subprocess.CalledProcessError:
                print("Failed to install dependencies. Please install them manually:")
                print(f"pip install {' '.join(missing)}")
                sys.exit(1)