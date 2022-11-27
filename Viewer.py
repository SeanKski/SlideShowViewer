from tkinter import *
from tkinter import ttk
from PIL import ImageTk, Image
from pathlib import Path
from torchvision.transforms import Resize
import time
import rclone
import json
"""
Tkinter notes
To create an image: 
This is a two-step process. First, you will create an image "object." Then, you can tell the label to use that object via its image configuration option:
    label = ttk.Label(parent, text='Full name:')
    image = ImageTk.PhotoImage(Image.open('myimage.gif'))
    label['image'] = image

Stickying widgets
If you want the widget to expand to fill up the entire cell, grid it with a sticky value of nsew (north, south, east, west)
 meaning it will stick to every side. This is shown in the bottom left widget in the above figure.
"""


SUPPORTED_IMAGE_TYPES = ['.png', '.jpg', 'jpeg', 'JPEG', 'JPG']

class SlideShowViewer:
    def __init__(self, root_dir='.', image_dir='images', initial_window_size=(500, 500),
                     interval=10, debug=False):
        self.root_dir = Path(root_dir)
        self.image_dir = self.root_dir / image_dir
        self.interval = interval * 1000  # milliseconds each image is shown before switching
        self.button_recently_pressed = False
        self.debug = debug
        # Grabbing starting variables
        if (self.root_dir / 'starting_variables.json').exists():
            with open(self.root_dir/'starting_variables.json', 'r') as f:
                self.starting_variables = json.load(f)
        else:
            self.starting_variables = None

        # Getting images
        self.image_filenames = self._get_filenames()
        self.n_images = len(self.image_filenames)
        # TODO: Have some way of setting up which image is chosen to be the first image
        ####### TODO: E.g., use starting_variables to allow setting of initial_image_idx
        initial_image_idx = 0
        self.viewing_history = [initial_image_idx]
        self.max_viewing_history = 100  # the max number of previous image to track
        self.current_image_idx = initial_image_idx
        # Setting up window
        self.initiate_window(initial_window_size)
        # Start the slideshow : )
        self.run_slideshow()
        # Run mainloop
        self.root.mainloop()

    def _get_starting_variable(self, key):
        # returns starting variable if they exist, otherwise returns none
        if self.starting_variables is not None:
            return self.starting_variables.get(key)
        else:
            return None

    def _set_starting_variable(self, key, value):
        # sets starting variable if it exists, creates it otherwise
        if self.starting_variables is not None:
            # starting variables were initialized
            self.starting_variables[key] = value
        else:
            # starting variables were not initialized
            self.starting_variables = dict(key=value)
        return None

    def set_and_save_starting_variable(self, key, value):
        # update key to value (creating if necessary) and save to local file
        self._set_starting_variable(key, value)
        self._save_starting_variables
            
    def _save_starting_variables(self):
        with open(self.root_dir/'starting_variables.json', 'r') as f:
            json.dump(self.starting_variables, f)
            
    def initiate_window(self, window_size):
        # Initiaites the Tk window, sets up widgets, and sets the grid
        self.root = Tk()
        self.root.title('Slideshow viewer')
        self.root.geometry(f'{window_size[0]}x{window_size[1]}')
        self.viewer = ttk.Frame(self.root)
        self.viewer.grid(column=0, row=0, sticky=(N, W, E, S))
        self.label_image = ttk.Label(self.viewer)
        # Setting up buttons
        self.button_back = ttk.Button(self.viewer, text='<<',
                                      command=lambda: self.backward(button_pressed=True))
        self.button_back.state(['disabled'])
        self.button_forward = ttk.Button(self.viewer, text='>>',
                                         command=lambda: self.forward(button_pressed=True))
        self.button_quit = ttk.Button(self.viewer, text='Quit?', command=self.root.quit)
        # binding key events to the buttons (technically the root but whatevs)
        self.root.bind('<Right>', lambda _: self.forward(button_pressed=True))
        self.root.bind('<Left>', lambda _: self.backward(button_pressed=True))
        self.root.bind('<Escape>', self.root.quit)
        # Setting to the grid
        # The grid consists of 2 rows and three columns
        self.label_image.grid(column=0, row=0, columnspan=3, sticky=(N, E, S, W))  # todo: see if we need "sticky" at all
        self.button_back.grid(column=0, row=1, sticky=[S,W])
        self.button_quit.grid(column=1, row=1, sticky=[S])
        self.button_forward.grid(column=2, row=1, sticky=[S,E])
        # Setting resize parameters
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.viewer.rowconfigure(0, weight=1)
        for i in range(3):
            self.viewer.columnconfigure(i, weight=1)
        # Post initial image
        # TODO: Decide how to setup the initial image correctly
        self._display_image(label_size=window_size)
        # Setup root to auto rescale when window size changes
        self.label_image.bind('<Configure>', lambda _: self._display_image(update=False))
        return None

    def run_slideshow(self):
        print('State: ', self.button_recently_pressed)
        # Go to the next image once the current image has been displayed for long enough
        if not self.button_recently_pressed:
            self.forward()  # equivalent to pressing the forward button
        else:  # since the current image was just changed (via button), don't change image
            if self.debug:
                print('Button was pressed previously, so no switch')
            self.button_recently_pressed = False
        self.root.after(self.interval, self.run_slideshow)

    def sync_image_folder(self):
        pass

    # Button functions
    def backward(self, button_pressed=False, *args):
        if self.button_back.instate(['!disabled']):  # if back button is not disabled
            if button_pressed:
                self.button_recently_pressed = True
            self._decrement_image_idx()
            # Testing to see if we reached the begining images after decrementing
            if len(self.viewing_history) <= 1:  # if we can't go back any more
                self.button_back.state(['disabled'])  # disables the back button
            # now that we went back, we can re-able the forward button if it was disabled
            #TODO: see if below should be uncommented, right now there is no disabling of the forward button
            #          so there is no need to check if it is disabled and then reable it
            # self.button_forward.instate(['disabled'], self.button_forward.state(['!disabled']))
        self._display_image()
        return None

    def forward(self, button_pressed=False, *args):
        if self.button_forward.instate((['!disabled'])):
            if button_pressed:
                self.button_recently_pressed = True
            self._increment_image_idx()
            # now that we went forward, we can re-able the back button if it was disabled
            self.button_back.instate(['disabled'], self.button_back.state(['!disabled']))
            self._display_image()
        return None


    # Image functions
    def _decrement_image_idx(self, *args):
        self.viewing_history.pop()  # takes the current (before decrement) image off the history
        next_image_idx = self.viewing_history[-1]
        self.current_image_idx = next_image_idx
        return next_image_idx

    def _increment_image_idx(self, *args):
        # TODO: Incorporate randomization
        next_image_idx = self.current_image_idx + 1
        # TODO: Change the if statement below once randomization is used
        if next_image_idx >= self.n_images:  # if we have reached the end of our slide show
            next_image_idx = self.viewing_history[0]  # resets the slideshow
            # TODO: See if this^ should start from new random point or initial random point
        self.current_image_idx = next_image_idx
        if len(self.viewing_history) > self.max_viewing_history:
            self.viewing_history.pop(0)
        self.viewing_history.append(next_image_idx)
        return next_image_idx

    def _display_image(self, update=True, label_size=None, *args):
        if update:
            image_filename = self.image_filenames[self.current_image_idx]
            self.original_pil_image = Image.open(str(image_filename))
        # Resize the image to fit the current window size
        self.pil_image = self._resize_image(self.original_pil_image, label_size=label_size)
        # Turn the resized image into a Tk photoimage and update the image label
        self.tk_image = ImageTk.PhotoImage(self.pil_image)
        self.label_image['image'] = self.tk_image
        return None

    def _resize_image(self, image=None, label_size=None):
        """
        Takes the image to be displayed in and then returns the resized* image.
        * in this case, resized images can actually mean edited/altered images
        E.g, for vertical images and that aren't going to be center cropped, the resizing
        could entail just fitting the vertical part of the image to the window and then
        padding the rest of the image and returning that to be displayed
        """
        if image is None:  # if we are not resizing a NEW image, then use current image
            image = self.original_pil_image
        if label_size is None:
            label_size = self.label_image.winfo_width(), self.label_image.winfo_height()
        # TODO: a better resize version: see notes
        """
        Resize options: 
         * use image.resize(**window_size), however this does not keep aspect ratio
         * resize the image to the largest possible size while respecting the aspect ratio
            and then pad the image with white/black/blur of neighboring pixels
        *  resize the image to the max possible size while maintaining aspect ratio and then
            center crop the image to fit to window width
        Post-resizing processing:
        *  Superscale/upscale the image to help fix some artifacts of the resizing move
        """
        if label_size == (1, 1):
            resize_option = 'no-op'
        else:
            # resize_option = 'padded-fit'
            resize_option = 'center-crop'
            # resize_option = 'resize'

        aspect_ratio = image.width / image.height

        if resize_option is 'padded-fit':
            # Resizes the image so that the largest side takes up the full screen and the
            # other size is black/blur padded to fill up the remainder of the screen
            # Thus maintaining the aspect ratio

            candidate_new_height = int(label_size[0] / aspect_ratio)
            candidate_new_width = int(label_size[1] * aspect_ratio)
            if (image.size[0] > image.size[1] and candidate_new_height < label_size[1]) or \
                (image.size[1] >= image.size[0] and candidate_new_width >= label_size[0]):
                new_size = (label_size[0], int(label_size[0] / aspect_ratio))
            else:
                new_size = int(label_size[1] * aspect_ratio), label_size[1]

            refit_image = image.resize(new_size)
            # creating padding for image
            pil_image_to_display = Image.new(image.mode, size=label_size)
            pil_image_to_display.paste(refit_image, box=((label_size[0] - new_size[0]) // 2,
                                                                   (label_size[1] - new_size[1]) // 2))
        
        elif resize_option is 'center-crop':
            image_width, image_height = image.size
            label_width, label_height = label_size
            # Resizes the image so that each edge is at/or above the window (maintaining
            # aspect ratio), and then centers the image in the screen

            def crop_to_center(image, label_size):
                label_center = (label_size[0] // 2, label_size[1] // 2)
                image_center = (image.width // 2, image.height // 2)
                crop_box = (image_center[0] - label_center[0], image_center[1] - label_center[1],
                                image_center[0] + label_center[0], image_center[1] + label_center[1])
                return image.crop(crop_box)


            # check if image is larger than window, if so, just crop to window and return
            if label_width >= image_width and label_height >= image_height:
                refit_image = image
            else: # image is smaller than window, so resize image to be larger than window (keeping aspect ratio)
                # test to see which image edge is farthest from the label boundary
                is_width_farther = (image_width - label_width) >= (image_height - label_height)
                if is_width_farther:
                    # resize window so image_width == label_width
                    new_width = label_width
                    new_height = int(new_width / aspect_ratio)
                else:
                    # resize window so image_height == label_height
                    new_height = label_height
                    new_width = int(new_height * aspect_ratio)
                refit_image = image.resize((new_width, new_height))

            # cropping so that it is center cropped
            pil_image_to_display = crop_to_center(refit_image, label_size)

        elif resize_option is 'resize':
            # resizes with no care for aspect ratio
            new_size = label_size
            pil_image_to_display = image.resize(new_size)

        else:  # no op  (likely due to the gridmanager not being set yet, so labelsize is 1,1
            pil_image_to_display = image.copy()

        if self.debug and resize_option is not 'no-op':
            new_size = pil_image_to_display.size
            print(f'Og Size ({image.width, image.height}, {aspect_ratio:.1f}),\t'
                  f' New Size ({new_size[0], new_size[1]}, {(new_size[0] / new_size[1]):.1f}),\t'
                  f' Label Size {label_size}')
        return pil_image_to_display

    def _get_filenames(self):
        image_filenames = []
        for image_filetype in SUPPORTED_IMAGE_TYPES:
            image_filenames += list(self.image_dir.glob(f'**/*{image_filetype}'))
        assert len(image_filenames) > 0, f'No images were found at (or within) location {self.image_dir}'
        return image_filenames

    def _print_wininfo(self, win_object):
        if win_object.children is not None:
            for child in win_object.grid_slaves():
                self._print_wininfo(child)
        print(win_object.grid_size())



viewer = SlideShowViewer(image_dir='images', debug=True)