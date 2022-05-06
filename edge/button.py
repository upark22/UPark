from threading import Thread
from time import time


from gpiozero import Button

button = Button(3)


import tkinter as tk

from PIL import Image as im 
from PIL import ImageTk
from tkinter import *

def on_escape(event=None):
    print("escaped")
    root.destroy()


class check_button(Thread):

    def __init__(self, display, canvas, root):
        Thread.__init__(self)
        self.display = display
        self.canvas = canvas
        self.root = root
        self.b = False

    def checkloop(self):
        while True:
            if button.is_pressed:
                if self.b == False :
                    self.canvas.delete(display)
                    img = ImageTk.PhotoImage(im.open("9.jpeg").resize([screen_width,screen_height]))
                    self.display = self.canvas.create_image(0,0,anchor ="nw", image=img)
                    self.b = True 
                    #self.root.mainloop()
                else:
                    self.canvas.delete(display)
                    img = ImageTk.PhotoImage(im.open("7.jpeg").resize([screen_width,screen_height]))
                    self.display = self.canvas.create_image(0,0,anchor ="nw", image=img)
                    self.b = False 
                    #self.root.mainloop()
                while button.is_pressed: pass


root = tk.Tk()

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.attributes("-fullscreen", True) # run fullscreen
root.wm_attributes("-topmost", True) # keep on top

root.bind("<Escape>", on_escape)
#root.bind("<space>", update_image)

canvas = tk.Canvas(root, width=screen_width, height=screen_height)
canvas.pack(fill='both', expand=True)
img = ImageTk.PhotoImage(im.open("5.jpeg").resize([screen_width,screen_height])) 
display = canvas.create_image(0,0,anchor ="nw", image=img) 


chk1 = check_button(display, canvas, root)
c1 = Thread(target=chk1.checkloop)
c1.start()

root.mainloop()
print("holamola")