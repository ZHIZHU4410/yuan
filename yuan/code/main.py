import pyautogui
import tkinter as tk
from gui import GameMacroApp


def main():
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    root = tk.Tk()
    app = GameMacroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
