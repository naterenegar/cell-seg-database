from imagetypes import SubImage 

import numpy as np
import cv2

import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector, Slider, Button, RadioButtons, TextBox
import matplotlib.patches as patches
from matplotlib.backend_bases import MouseEvent

# This class takes in a Database object and presents a gui that allows the user
# to generate sequences of images

# WARNING: This implementation makes some assumptions about the structure of
# the database. If this tool is generalized to other datasets than the one it
# was built on, this will probably need to change

# Inputs: Database object with get_dict method
# Outputs: list of subimage metadata

class ImageSequencer(object):

    def __init__(self, database):
        # get_dict returns a deep copy of the dictionary, so we can modify
        # however we need 
        self.redef_data(database)

    def redef_data(self, database):
        self.image_dict = database.get_dict()['data']['experiments']


    def get_sequence(self):

        # This gets the experiment number 
        valid_exp = False
        while valid_exp == False:
            # grab all image metadata in relevant experiment
            try:
                exp = int(input("Please enter desired experiment number: "))
                exp = 'exp' + ('0' + str(exp) if exp < 10 else str(exp))
                exp_images = self.image_dict[exp]['images']['image_array']
                num_exp_images = self.image_dict[exp]['images']['num_images']
                duration = self.image_dict[exp]['duration'] 
                h, v = exp_images[0]['resolution']
                print(exp, "has", self.image_dict[exp]['duration'], 
                        "hours of data, consisting of", num_exp_images, "images.")
                valid_exp = True
            except (KeyError, ValueError) as e:
                print("You entered an invalid experiment number. Valid numbers are:")
                exp_strings = list(self.image_dict.keys())
                exp_strings = [int(x.split('exp')[1]) for x in exp_strings]
                print(str(exp_strings))

        # Get start and ending hours
        times = [img['time'] for img in exp_images]

        fig,ax = plt.subplots(ncols=2, nrows=1, sharey=True, sharex=True)
        ax = ax.ravel()
        im0 = cv2.imread(exp_images[0]['path']) 
        im0 = cv2.cvtColor(im0, cv2.COLOR_BGR2RGB)
        im1 = cv2.imread(exp_images[-1]['path']) 
        im1 = cv2.cvtColor(im1, cv2.COLOR_BGR2RGB)
        artist_0 = ax[0].imshow(im0)
        ax[0].set_title('First image at time = ' + str(times[0]) + " hours")
        artist_1 = ax[1].imshow(im1)
        ax[1].set_title('Last image at time = ' + str(times[-1]) + " hours")
    
        axcolor = 'lightgoldenrodyellow'
        start_ax = plt.axes([0.25, 0.15, 0.65, 0.03], facecolor=axcolor)
        end_ax   = plt.axes([0.25, 0.10, 0.65, 0.03], facecolor=axcolor)
        update_ax = plt.axes([0.25, 0.025, 0.1, 0.04])
        next_ax = plt.axes([0.8, 0.025, 0.1, 0.04])

        s_start = Slider(start_ax, 'Start time (hrs)', times[0], times[-1], valinit=times[0], valstep=(times[1] - times[0]))
        s_end   = Slider(end_ax, 'End time (hrs)', times[0], times[-1],valinit=times[-1], valstep=(times[1] - times[0]))
        update = Button(update_ax, 'Update', color=axcolor, hovercolor='0.975')
        next_button = Button(next_ax, 'Next', color=axcolor, hovercolor='0.975')

        def update_start(val):
            ts = s_start.val
            te = s_end.val
            if ts > te:
                s_end.set_val(ts)
                
        def update_end(val):
            ts = s_start.val
            te = s_end.val
            if te < ts:
                s_start.set_val(te)
                
        def get_closest_time_idx(val):
            cl_time, cl_idx = 0, 0
            for idx, time in list(enumerate(times)):
                if (abs(val - time) < abs(cl_time - time)):
                    cl_time = time
                    cl_idx = idx

            return cl_idx, cl_time

        def update_images(event):
            s_idx, st = get_closest_time_idx(s_start.val)
            e_idx, et = get_closest_time_idx(s_end.val)
            s_start.set_val(st)
            s_end.set_val(et)

            im0 = cv2.imread(exp_images[s_idx]['path']) 
            im0 = cv2.cvtColor(im0, cv2.COLOR_BGR2RGB)
            im1 = cv2.imread(exp_images[e_idx]['path']) 
            im1 = cv2.cvtColor(im1, cv2.COLOR_BGR2RGB)
            artist_0.set_data(im0)
            ax[0].set_title('First image at time = ' + str(st) + " hours")
            artist_1.set_data(im1) 
            ax[1].set_title('Last image at time = ' + str(et) + " hours")

        def proceed(event):
            update_images(None)
            plt.close()

        s_start.on_changed(update_start)
        s_end.on_changed(update_end)
        update.on_clicked(update_images)
        next_button.on_clicked(proceed)
        plt.show()

        start_ax.remove()
        end_ax.remove()
        update_ax.remove()
        next_ax.remove()

        start_idx, start_hr = get_closest_time_idx(s_start.val)
        end_idx, end_hr = get_closest_time_idx(s_end.val) 

        # Set up figure for ROI settings
        fig,ax = plt.subplots(ncols=2, nrows=1, sharey=True, sharex=True)
        ax = ax.ravel()
        im0 = cv2.imread(exp_images[start_idx]['path']) 
        im0 = cv2.cvtColor(im0, cv2.COLOR_BGR2RGB)
        im1 = cv2.imread(exp_images[end_idx]['path']) 
        im1 = cv2.cvtColor(im1, cv2.COLOR_BGR2RGB)
        artist_0 = ax[0].imshow(im0)
        ax[0].set_title('First image at time = ' + str(start_hr) + " hours")
        artist_1 = ax[1].imshow(im1)
        ax[1].set_title('Last image at time = ' + str(end_hr) + " hours")

        # set up new axes, sliders, and buttons for annotations
        h_grid_ax = plt.axes([0.15, 0.10, 0.20, 0.03], facecolor=axcolor)
        v_grid_ax = plt.axes([0.15, 0.15, 0.20, 0.03], facecolor=axcolor)
        h_res_ax = plt.axes([0.50, 0.10, 0.05, 0.03])
        v_res_ax = plt.axes([0.50, 0.15, 0.05, 0.03])
        h_pad_ax = plt.axes([0.70, 0.10, 0.05, 0.03])
        v_pad_ax = plt.axes([0.70, 0.15, 0.05, 0.03])
        update_ax = plt.axes([0.15, 0.05, 0.05, 0.03]) 
        stride_ax = plt.axes([0.40, 0.8, 0.05, 0.03])

        h_strech = Slider(h_grid_ax, 'H Grid',1,3,valinit=1, valstep=0.05)
        v_strech = Slider(v_grid_ax, 'V Grid',1,3,valinit=1, valstep=0.05)
        h_res = TextBox(h_res_ax, 'H Res', initial='256')
        v_res = TextBox(v_res_ax, 'V Res', initial='256')
        h_pad_box = TextBox(h_pad_ax, 'H Pad', initial='256')
        v_pad_box = TextBox(v_pad_ax, 'V Pad', initial='256')
        update_button = Button(update_ax, 'Update', color=axcolor, hovercolor='0.975')
        stride_box = TextBox(stride_ax, 'Sampling Stride',initial='1')

        # radio buttons to toggle between two modes

        def draw_grid():
            for a in ax:
                for p in a.patches:
                    p.set_visible(True)

            fig.canvas.draw()

        def clear_grid():
            for a in ax:
                for p in a.patches:
                    p.set_visible(False)
            fig.canvas.draw()

        def reset_grid():
            for a in ax:
                a.patches = []

        def get_num_rois():
            num_rois = 0
            for rect in ax[0].patches:
                if rect.get_edgecolor() == (1.0, 0.0, 0.0, 1):
                    num_rois = num_rois + 1
            return num_rois

        def click_roi(event):
            if type(event) == MouseEvent:
                try:
                    click_x, click_y = event.xdata, event.ydata

                    for idx, rect in list(enumerate(ax[0].patches)):
                        xmin, ymin = rect.get_xy()
                        xmax, ymax = xmin + rect.get_width(), ymin + rect.get_height()
                        if ((click_x >= xmin and click_x <= xmax) and
                            (click_y >= ymin and click_y <= ymax)):
                                color = rect.get_edgecolor()                    
                                clicked_color = (1.0, 0.0, 0.0, 1)
                                if color != clicked_color:
                                    rect.set_edgecolor('r')
                                    ax[1].patches[idx].set_edgecolor('r')
                                elif color == clicked_color:
                                    rect.set_edgecolor('g')
                                    ax[1].patches[idx].set_edgecolor('g')
                except TypeError:
                    pass
      
            num_rois = get_num_rois()
            stride = int(stride_box.text)
            num_sample_imgs = num_rois * ((end_idx - start_idx) // stride)
            fig.suptitle('ROIS: ' + str(num_rois) + 
                    '; Source Images: ' + str((end_idx - start_idx) // stride) + 
                    '; Sample Images: ' + str(num_sample_imgs))

            fig.canvas.draw_idle()

        def update_grid_drawing(event):
            reset_grid()

            h_size = int(h_res.text)
            v_size = int(v_res.text)
            h_pad = int(h_pad_box.text)
            v_pad = int(v_pad_box.text)

            max_hs = (h - h_pad - h_size) // int(h_size * h_strech.val)
            max_vs = (v - v_pad - v_size) // int(v_size * v_strech.val)
            h_starts = np.linspace(h_pad, h - h_pad - h_size, max_hs)
            v_starts = np.linspace(v_pad, v - v_pad - v_size, max_vs) 

            maximum_ts = max_hs * max_vs

            starts = []
            for i in range(maximum_ts):
                starts.append((int(h_starts[i % max_hs]), int(v_starts[i // max_hs])))

            # Create the grid based on the settings given to us
            for start in starts:
                for a in ax:
                    rect = patches.Rectangle(start,h_size,v_size,linewidth=1,edgecolor='g',facecolor='none')
                    a.add_patch(rect)
            fig.canvas.draw_idle()
            click_roi(None) # update ROI and image counts
        
        update_grid_drawing(None)
        update_button.on_clicked(update_grid_drawing)
        stride_box.on_submit(click_roi)
        click_roi_id = plt.connect('button_press_event', click_roi)

        plt.show()
        
        stride = int(stride_box.text)
        num_rois = get_num_rois()
        num_sample_images = num_rois * ((end_idx - start_idx) // stride)


        # Construct list of subimages to be appended 
        img_idxs = [(start_idx + i*stride) for i in range((end_idx - start_idx) // stride)] 
        roi_corners = []
        for rect in ax[0].patches:
            color = rect.get_edgecolor()                    
            clicked_color = (1.0, 0.0, 0.0, 1)
            if color == clicked_color:
                roi_corners.append(rect.get_xy())
        
        tmp_img = SubImage()
        img_list = []
        for idx in img_idxs:
            for offset in roi_corners:
                d = tmp_img.dict
                d['size'] = (int(h_res.text), int(v_res.text))
                d['source_offset'] = offset
                d['source_path'] = exp_images[idx]['path'] 
                d['source_name'] = exp_images[idx]['name']
                img_list.append(tmp_img.get_dict())  

        for img in img_list:
            print(img)

        return img_list 
