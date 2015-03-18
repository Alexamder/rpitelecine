# RPi Telecine - Perforation finding and detection
#
# Perforation location and frame extraction for Super 8 and
# Standard 8 film.
# 
# This has been tested using Super8 amateur film with 
# black film base, commercial 8mm film with a clear film base.
# 
# Quite a few assumtions are made with regards to the position of
# each perforation in the frame - that they lie in the left hand 
# side of the frame - Super 8 perforations are situated in the
# middle vertically, and Standard 8 perforations are towards the
# top of the frame. The film gate holds the film horizontally
# with little movement laterally.
#
# A more complex method based on the openCV squares.py example program was tried - 
# and was pretty successful, but ran very slowly on the Raspberry Pi, and not 100% reliable
# so this simpler method was developed instead.
#
# Copyright (c) 2015, Jason Lane
# 
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this 
# list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice, 
# this list of conditions and the following disclaimer in the documentation and/or 
# other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its contributors 
# may be used to endorse or promote products derived from this software without 
# specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR 
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; 
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON 
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS 
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import division
import numpy as np
import scipy.ndimage.measurements as nd

# Types of film 
filmTypes = ['super8', 'std8']

class TelecinePerforation():
    """
    Class that handles the perforation finding
    """
    filmType = ''

    sizeMargin = 0.2	        # Margin around ROI - 0.2=20%
    windowWidth = 0             # Width of window used to detect 

    isInitialised = False

    imageSize = ( 0,0 )         # Size of the frame to convert

    ROIslice = None             # Slice for the ROI where the perforation should lie
    ROIxy = ( 0,0 )             # Position of ROI in image
    ROIwh = ( 0,0 )             # Width and height of ROI
    ROIcentrexy = [ 0,0 ]       # Centre xy position of ROI in image
    ROIthreshold = 0            # Threshold for sprocket detection

    # Used as temporary image holder when detecting perforation
    ROIimg = None
    
    # If converting colour image, use green channel otherwise do greyscale conversion (slower)
    ROIuseGreenChannel = True
    
    # Updated when the find method is called
    found = False	# If last detection was successful

    thresholdVal = 0.98 # 

    expectedSize = ( 0,0 )      # Expected size of perforation
    position = (0,0)
    centre = (0,0)	# Centre of perforation
    yDiff = 0		# Difference between real and ideal position of perforation

    # Ranges of acceptable values for aspect ratio, height and width of the detected perforation
    aspectRange = ( 0.0, 0.0 )
    widthRange = ( 0,0 )
    heightRange = ( 0,0 )
    
    checkEdges = 0
    # 1 - Use top edge of perforation as reference
    # 2 - Use bottom edge only as reference
    # else use centre between detected top and bottom edges as reference
    checkLeftEdge = True
    
    # Some useful information based on the mm dimensions from the film specifications
    perforationAspectRatio = {'super8':(0.91/1.14), 'std8':(1.8/1.23)} # Standard sizes in mm

    # Frame size in proportion to the perforation size
    # Can be used to automatically set a crop based on detected perforation size in pixels
    frameHeightMultiplier = { 'super8':4.23/1.143, 'std8':3.81/1.23 }
    frameWidthMultiplier = { 'super8':5.46/0.91, 'std8':4.5/1.8 }

    useBGR = True # Use OpenCV BGR images for grey conversion

    # Utility routines
    def convert2grey(img):
        # Return grayscale version of the image
        if self.useBGR:
            return np.dot(img[...,:3], [0.144, 0.587, 0.299]).astype(np.uint8)
        else:
            return np.dot(img[...,:3], [0.299, 0.587, 0.144]).astype(np.uint8)

    def init(self, filmType, imageSize, expectedSize, cx):
        # cx is the perforation film line
        # size is a (w,h) tuple of a perforation size
        if imageSize[0]>imageSize[1]:
            self.imageSize = (imageSize[1],imageSize[0])
        self.setFilmType(filmType)
        self.ROIcentrexy[0] = int(cx)
        self.setPerforationSize( expectedSize )
        
    def setFilmType(self,filmType):
        if filmType in filmTypes:
            # Set aspect ratio bounds
            self.isInitialised = False
            self.filmType = filmType
            aspectRatio = self.perforationAspectRatio[filmType]
            aspectMargin = aspectRatio * (self.sizeMargin/2)
            self.aspectRange = ( aspectRatio-aspectMargin, aspectRatio+aspectMargin)
        else:
            raise Exception("Error - '{}' is an incorrect film type.".format(filmType))

    def setPerforationSize(self,size):
        # Sets the expected size of the perforation, and a margin for error
        w,h = size
        if w>0 and h>0:
            w_margin = int(w*self.sizeMargin)
            h_margin = int(h*self.sizeMargin)
            self.widthRange = ( w-w_margin , w+w_margin )
            self.heightRange = ( h-h_margin , h+h_margin )
            self.expectedSize = size
            self.isInitialised = True
        else:
            self.expectedSize = (0,0)
            self.ROIimg = None
            self.isInitialised = False
        self.setROI()

    def setROI(self):
        # Sets the ROI where to look for a perforation
        # If an expected perforation size is set, then ROI is based on size of perforation
        img_h,img_w = self.imageSize
        if self.isInitialised:
            print "IS INITIALISED"
            # Already know expected size, so use smaller ROI
            # ROI height and position on Y axis
            # Top of ROI for initialised perforation detection
            h = int(img_h/2)  # Use 1/2 of image height for ROI
            if self.filmType == 'super8':
                # Middle of image height
                y = int(img_h/4)
            else:
                # Standard 8 - top part of image
                y = int(img_h/50)  # 39 pixels with 1944px high image
            # Base width on previously detected perforation - centre ib ROIcx
            w = int((self.expectedSize[0] + (self.expectedSize[0]*self.sizeMargin))/2)
            roiL = max(0, self.ROIcentrexy[0]-w)
            roiR = min(img_w, self.ROIcentrexy[0]+w)
            self.ROIcentrexy = [ int(roiL+(roiR-roiL)/2), int(y+(h/2)) ]
        else:
            # Not found before - so use larger area for detection
            # Use whole image height + half image width
            y = 0
            h = img_h
            roiL = 0
            roiR = int(img_w/2)
            self.ROIcentrexy = [0,0]
        self.ROIxy = ( roiL, y )
        self.ROIwh = ( roiR-roiL, h )
        self.ROIslice = np.index_exp[ y:y+h, roiL:roiR ]         # Create the slice object for making the ROI
        print("img: {} roiR: {} roiL: {} h: {}".format(self.imageSize, roiR,roiL,h))
        self.ROIimg = np.zeros( (roiR-roiL, h), dtype=np.uint8)  # Initialise space for the ROI image 

    def setROIimg(self,img):
        # Sets the ROI image - converting to greyscale if necessary
        if img.shape[:2] == self.imageSize:
            # Expected image size OK
            if len(img.shape)>2:
                # Colour image, so convert it
                if self.ROIuseGreenChannel:
                    i = img[self.ROIslice]
                    self.ROIimg = i[:,:,1]
                else:
                    # do 'proper' greyscale conversion
                    self.ROIimg = self.convert2grey(img[self.ROIslice])
            else:
                # greyscale image already
                self.ROIimg = img[self.ROIslice]
        else:
            # We have an incorrect image size - this shouldn't happen
            raise Exception('Image size incorrect. Expected: {} Received: {}'.format(self.imageSize,img.shape[:2]) )
    
    def cropToSlice( self, (x,y, w,h) ):
        # Returns a numpy slice from a list or tuple for extracting a crop from the image (x,y,w,h)
        x = max(x,0)
        y = max(y,0)
        w = max(w,1)
        h = max(h,1)
        return np.index_exp[ y:y+h, x:x+w ]

    def findFirstFromCoords( self, img, startPosition, windowWidth ):
        # Find first perforation and its size from the starting position
        self.isInitialised = False
        self.found = False

        self.imageSize = img.shape[:2]
        self.setROI()
        self.setROIimg(img)
 
        xStart = startPosition[0]
        yStart = startPosition[1]

        win = windowWidth//2

        #take a vertical section of pixels from the ROI and threshold it
        vROI = self.ROIimg[:,xStart-win:xStart+win]
        threshVal = int(vROI.max()*self.thresholdVal)

        #Make a single pixel wide strip, with the median of all the rows - and threshold it
        vROI = np.median(vROI,axis=1) < threshVal

        # And horizontal...
        hROI = self.ROIimg[yStart-win:yStart+win,:]
        
        #Make a single pixel wide strip, with the median of all the columns - and threshold it
        hROI = np.median(hROI,axis=0) < threshVal

        # Check if centre section is clear of data
        if hROI[xStart-win:xStart+win].any() or vROI[yStart-win:yStart+win].any():
            print( "Image data, so can't locate perforation at: {}".format(startPosition) )
        else:
            x,y = self.ROIxy
            w,h = self.ROIwh
            # Now to find the edges
            bot   = vROI[yStart:].argmax()
            bot   = yStart+bot if bot>0 else h

            vROI = vROI[:yStart]
            top   = vROI[::-1].argmax()
            top   = yStart-top if top>0 else 0

            right = hROI[xStart:].argmax()
            right   = xStart+right if right>0 else w

            hROI = hROI[:xStart]
            left  = hROI[::-1].argmax() 
            left  = xStart-left if left>0 else 0

            # Sanity check the aspect ratio of detection
            w = right-left
            h = bot-top
            aspect = float(w) / float(h)
            if self.aspectRange[0] <= aspect <= self.aspectRange[1]:
                # Aspect Ratio of found perforation is OK - save information
                self.setPerforationSize( (w,h) )
                self.setPerfPosition( x+left+((right-left)/2), y+top+(h/2) )
                self.windowWidth = w - (w*self.sizeMargin*2)
                self.isInitialised = True
                # Now adjust ROI to match found perforation
                self.ROIcentrexy[0] = self.centre[0]
                self.setROI()
                self.found = True
            else:
                print( "Perforation aspect {} ratio NOT OK - detection failed. Range: {}".format(aspect,self.aspectRange) )

    def setPerfPosition(self,cx,cy):
        # Sets the perforation position based on the centre
        self.centre = ( int(cx), int(cy) )
        self.position = ( int(cx-self.expectedSize[0]/2),int(cy-self.expectedSize[1]/2) )
        self.yDiff = int(self.centre[1]-self.ROIcentrexy[1])

    def findVertical(self, img):
        # Used for subsequent captures where we know the expected size and 
        # approximate horizontal position of perforation

        self.found = False
        self.setROIimg(img)

        expectedW, expectedH = self.expectedSize

        xStart = self.ROIwh[0]//2
        #xStart = self.centre[0]-ROIxy[0]
        yStart = self.ROIcentrexy[1]-self.ROIxy[1]
        win = (expectedW - (expectedW*self.sizeMargin) )//2 

        vROI = self.ROIimg[:,xStart-win:xStart+win]
        threshVal = int(vROI.max() * self.thresholdVal)

        vROI = np.median(vROI,axis=1) < threshVal
        #print "FindVertical: vROI"
        #print "shape: {}".format(vROI.shape)

        x,y = self.ROIxy
        w,h = self.ROIwh
        # Now to find the edges
        bot   = vROI[yStart:].argmax()
        #print("bot:{}".format(bot))
        #print vROI[yStart:]
        bot   = yStart+bot if bot>0 else h

        vROI = vROI[:yStart]
        top   = vROI[::-1].argmax()
        #print("top:{}".format(top))
        #print vROI[::-1]
        top   = yStart-top if top>0 else 0
  
        if self.checkEdges==1:
            # use top edge as reference and extrapolate bottom edge
            bot = top+expectedH
        elif self.checkEdges==2:
            # use bottom edge as reference
            top = bot-expectedH
        # Check if detected is close to correct aspect ratio of perforation
        aspect =  float(expectedW) / float(bot-top)
        if self.aspectRange[0] <= aspect <= self.aspectRange[1]:
            # Aspect Ratio of found perforation is OK - save information
            #print( "Aspect ratio OK" )
            x,y = self.ROIxy
            self.setPerfPosition( x + xStart, y + top + ((bot-top)/2) )
            self.found = True
        else:
            print( "Perforation aspect {} ratio NOT OK - detection failed. Range: {}".format(aspect,self.aspectRange) )
        if not(self.found):
            # Try alternative method
            self.findVerticalAlternative()

    def findVerticalAlternative(self):
        # This is an alternative method, a bit more expensive
        # than the first version, and is called on failure of
        # the previous findVertical. It uses Scipy labelling to segment the a strip 
        # of data from the ROI
        self.found = False
        cx = self.ROIwh[0]//2
        expectedW, expectedH = self.expectedSize

        win = (expectedW - (expectedW*self.sizeMargin) )//2 
        #take a vertical section of pixels from the ROI and threshold it
        vROI = self.ROIimg[:,cx-win:cx+win]

        #Make a single pixel wide strip, with the median of all the rows 
        vROI = np.median(vROI,axis=1)
        threshVal = int(vROI.max() * self.thresholdVal)
        vROIthres = vROI >= threshVal
        candidate = None
        if vROIthres.min() != vROIthres.max(): 
            # Prevent a divide by zero because roi is all the same value. 
            # e.g. we have a frame completely white or black
            lbl,numLbl = nd.label(vROIthres)
            obj = nd.find_objects(lbl)
            brightest = 0
            for s in obj:
                print s
                # s is an np.slice object
                sBright = np.mean(vROI[s]) 
                sHeight = s[0].stop - s[0].start
                if (self.heightRange[0] <= sHeight <= self.heightRange[1]) and sBright > brightest:
                    candidate = s[0]
                    brightest = sBright
        if candidate:
            self.setPerfPosition( self.ROIcentrexy[0], self.ROIxy[1]+candidate.start + ((candidate.stop-candidate.start)/2 )) 
            self.found = True

    def findLeftEdge(self):
        # Find the left edge of the perforation.
        # This can be used to compensate for any horizontal
        # movement of the film in the frame - this should be called
        # after finding the vertical position. The left edge is used
        # as the right may be overwhelmed with a bright image.
        # It uses the same ROI image created in findVertical
        if self.found:
            # Horizontal section, and threshold

            expectedW, expectedH = self.expectedSize

            win = (expectedH - (expectedH*self.sizeMargin) )//2 

            #Centre of current perforation
            centre = (self.centre[0]-self.ROIxy[0], self.centre[1]-self.ROIxy[1] )
            # Horizontal strip of pixels of ROI up to centre of perforation
            hROI = self.ROIimg[ centre[1]-win:centre[1]+win, :centre[0] ]

            threshVal = int(hROI.max() * self.thresholdVal)

            #Make a single pixel wide strip, with the median of all the columns - and threshold it
            hROI = np.median(hROI, axis=0) < threshVal

            # Position of edge of perforation
            left  = hROI[::-1].argmax() 
            left  = centre[0]-left if left>0 else 0

            self.position = ( left + self.ROIxy[0], self.position[1] )
            self.centre = (left + (self.expectedSize[0]//2) + self.ROIxy[0], self.centre[1] )
        else:
            raise Exception('Error - Cannot do findLeftEdge until vertical has been found')

    def find(self,img):
        # Find perforation position in the image
        if self.isInitialised:
            self.findVertical(img)
            if self.found and self.checkLeftEdge:
                self.findLeftEdge()
        else:
            # We haven't initialised or run findFirstFromCoords 
            raise Exception('Error - Perforation detection not initialised.')

