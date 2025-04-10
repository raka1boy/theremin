from dependency_manager import DependencyManager
from sine_ui import ControlUI
from sine_gen import SineGen

def main():
    # First ensure dependencies are installed
    DependencyManager.install_dependencies()
    
    # Now create and run the application
    generator = SineGen(chunk_size=64)
    app = ControlUI(generator)
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main()