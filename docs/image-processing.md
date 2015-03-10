#Capturing flow

##Image capture

The Pi camera takes a full 5MP image and returns a BGR 8bit image
as an OpenCV compatible Numpy array. A full image capture takes about
0.7 seconds before the data is available. 

##Perforation detection

Perforation detection uses a region of interest - a small part of the whole image
in one channel in order to minimise the amount of processing required.

The perforation will be the largest, brightest area in the ROI image. A vertical 
slice of the ROI is made, and the median value of each row is used to make a 
single column representation of the brightness of the width. This column is
thresholded to create a binary array, and the position of the top and bottom
edge of the perforation is established.

Using a median value across the width of the perforation allows for damaged
sprocket holes. This seems to work quite well.

Optionally the same process is repeated for the left hand edge of the perforation
in order to compensate for horizontal weaving.

The output of the detection is the centre point of the perforation in the image.

##Cropping

The centre point established by the perforation detection is used to calculate
the slice used to crop the film frame from the whole image.

The crop is specified by an offset from the centre point, and its width and 
height. A slice object is created, and the sliced image is sent to the writing
queue.

##Writing

The cut-out frames are placed in a queue with the filename/frame number where 
they are taken by a separate thread and output to SD card or other storage. 
Writing the image data is time consuming. Depending on the size of the image
crop and file format, output is typically 0.8 to 1.5 seconds per frame with
a Raspberry Pi 2 and a reasonably fast Micro-SD card.
 
Using a separate thread to write the images means that the image writing works 
in parallel with moving the film to the next frame, and waiting for the camera
to take the next picture.

##Speed considerations

50 feet of 8mm film has around 3600 frames.
The Pi camera requires 0.7 seconds to set up the camera and take a 5MP still
picture and get the RGB data for further analysis and processing.
The other time consuming process is the saving of the cropped image. A crop that is
about 1800x1300 pixels large takes about 0.9 seconds to write as a 620K JPG, or 
1.4 seconds to write a 3.3MB PNG. 

Experiments have shown that OpenCV is the fastest at saving of images. I have
tried using PIL and Qt, and the PNG save takes in excess of 3-4 seconds. So
it's back to using OpenCV.

Total job time is therefore determined by either the picture taking, or the
image saving elements of the process - whichever is longest.

At present, it doesn't seem possible to increase the speed of the camera. In 
order to get the consistent exposure needed by the telecine, the stills 
port is required. My attemps at trying to get full resolution images using
the Pi's video port have failed. It would be nice to be able to get
multiple images per second out of the camera.

It may be possible to use multiple threads to write the data files - but
this will be limited by the maximum IO speed, either over the USB if 
saving to an external drive, or using the SD card interface. JPEG and PNG
compression require quite a lot of processing power, so it might be beneficial
to have the writing threads on separate processor cores.
