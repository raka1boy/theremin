from sineui import ControlUI
from sine_gen import SineGen

def main():
    generator = SineGen(chunk_size=64)
    app = ControlUI(generator)
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main()