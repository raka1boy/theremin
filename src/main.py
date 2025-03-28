import sine_gen
import sineui
def main():
    generator = sine_gen.SineGen(chunk_size = 128)
    ui = sineui.ControlUI(generator)
    ui.protocol("WM_DELETE_WINDOW", ui.on_closing)
    ui.mainloop()

if __name__ == "__main__":
    main()