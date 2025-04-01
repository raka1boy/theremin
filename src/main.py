from sineui import ControlUI
from sine_gen import SineGen
import sys
import subprocess
import importlib

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

def main():
    # First ensure dependencies are installed
    install_dependencies()
    
    # Now import the modules
    from sineui import ControlUI
    from sine_gen import SineGen

    generator = SineGen(chunk_size=64)
    app = ControlUI(generator)
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main()