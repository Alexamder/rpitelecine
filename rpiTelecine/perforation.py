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
import cv2
import scipy.ndimage.measurements as nd
from timer import Timer

# Types of film 
filmTypes = ['super8', 'std8']

class TelecinePerforation():
    """
    Class that handles the perforation finding
    """
    filmType = ''

    sizeMargin = 0.08	        # Variation in perforation size allowed

    isInitialised = False

    imageSize = ( 0,0 )         # Size of the frame to convert

    ROIslice = None             # Slice for the ROI where the perforation should lie
    ROIxy = ( 0,0 )             # Position of ROI in image
    ROIwh = ( 0,0 )             # Width and height of ROI
    ROIcentrexy = [ 0,0 ]       # Centre xy position of ROI in image

    # Used as temporary image holder when detecting perforation
    ROIimg = None
    
    # Updated when the find method is called
    found = False	# If last detection was successful

    expectedSize = ( 0,0 )      # Expected size of perforation
    position = (0,0)
    centre = (0,0)      # Centre of perforation
    yDiff = 0		# Difference between real and ideal position of perforation

    # Ranges of acceptable values for aspect ratio, height and width of the detected perforation
    aspectRange = ( 0.0, 0.0 )
    widthRange = ( 0,0 )
    heightRange = ( 0,0 )
    threshold = 0.99    # Used for thresholding ROI image
    
    checkEdges = 0
    # 1 - Use top edge of perforation as reference
    # 2 - Use bottom edge only as reference
    # else use centre between detected top and bottom edges as reference
    checkLeftEdge = True

    # Some useful information based on the mm dimensions from the film specifications
    perforationAspectRatio = {'super8':(0.91/1.14), 'std8':(1.8/1.23)} # Standard sizes in mm

    # Frame size in proportion to the perforation size
    # Can be used to automatically set a crop based on detected perforation size in pixels
    frameHeightMultiplier = { 'super8':4.234/1.143, 'std8':3.81/1.23 }
    frameWidthMultiplier = { 'super8':5.69/0.914, 'std8':4.5/1.8 }


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
            self.isInitialised = False
        self.setROI()

    def setROI(self):
        # Sets the ROI where to look for a perforation
        # If an expected perforation size is set, then ROI is based on size of perforation
        img_h,img_w = self.imageSize
        if self.isInitialised:
            # Already know expected size, so use smaller ROI
            # ROI height and position on Y axis
            # Top of ROI for initialised perforation detection
            h = int(img_h/3)  # Use 1/3 of image height for ROI
            if self.filmType == 'super8':
                # Middle of image height
                y = (img_h//2) - (h//2)
            else:
                # Standard 8 - top part of image
                y = int(img_h/50)  # 39 pixels with 1944px high image
            # Base width on previously detected perforation - centre ib ROIcx
            margin = self.expectedSize[0] // 3
            w = (self.expectedSize[0] + margin)//2
            roiL = max(0, self.ROIcentrexy[0]-w)
            roiR = min(img_w, self.ROIcentrexy[0]+w)
            self.ROIcentrexy = [ roiL+(roiR-roiL)//2, y+(h//2) ]
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
        
    def verticalMedian(self,img):
        # Make a vertical section through the image and return an array with
        # the median of each row
        expectedW = self.expectedSize[0]
        win = expectedW // 3
        cx = self.ROIwh[0] // 2
        start = cx-win
        end = cx+win
        if len(img.shape)>2:
            # median value of each channel
            a = np.mean( img[:,start:end],axis=2 )
            # median value of each row to make a single column
            v = np.median( a,axis=1 )
        else:
            v =  np.median(img[:,start:end],axis=1)
        print "vROI shape {}".format(v.shape)
        return v

    def horizontalMedian(self,img,cy):
        # Make a horizontal section through the image and return an array with
        # the median of each column
        w,h = self.ROIwh
        expectedH = self.expectedSize[1]
        win = expectedH // 5
        start = cy-win
        end = cy+win
        if len(img.shape)>2:
            # median value of each channel
            a = np.mean( img[start:end,:],axis=2 )
            # median value of each column
            h = np.median( a,axis=0 )
        else:
            h =  np.median(img[start:end,:],axis=0)
            print "hROI shape {}".format(h.shape)
        return h

    def cropToSlice( self, (x,y, w,h) ):
        # Returns a numpy slice from a list or tuple for extracting a crop from the image (x,y,w,h)
        x = max(x,0)
        y = max(y,0)
        w = max(w,1)
        h = max(h,1)
        return np.index_exp[ y:y+h, x:x+w ]

    def thresholdVal( self, img ):
        #t = img.max() - 1
        t = img.max() * self.threshold
        #print "THRESH: {}".format(t)
        return t

    def findFirstFromCoords( self, img, startPosition, windowWidth ):
        with Timer() as t:
            # Find first perforation and its size from the starting position
            print("findFirstFromCoords")
            self.isInitialised = False
            self.found = False

            self.imageSize = img.shape[:2]
            self.setROI()
            img = img[self.ROIslice]
            xStart, yStart = startPosition
            win = windowWidth//2
            vStart = xStart-win
            vEnd = xStart+win
            hStart = yStart-win
            hEnd = yStart+win

            if len(img.shape)>2:
                # median value of each channel
                a = np.median( img[:,vStart:vEnd],axis=2 )
                b = np.median( img[hStart:hEnd,:],axis=2 )
                # median value of each row to make a single column
                v = np.median( a,axis=1 )
                h = np.median( b,axis=0 )
            else:
                v =  np.median(img[:,vStart:vEnd],axis=1)
                h =  np.median(img[hStart:hEnd,:],axis=0)
            print "vROI shape {}".format(v.shape)
            print "hROI shape {}".format(h.shape)
            threshVal = self.thresholdVal( v )

            #Threshold the vertical strip
            vROI = v < threshVal
            hROI = h < threshVal

            # Check if centre section is clear of data
            if hROI[vStart:vEnd].any() or vROI[hStart:hEnd].any():
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
                print("top {}  bot {}  left {}  right {}".format(top,bot,left,right))
                # Sanity check the aspect ratio of detection
                w = right-left
                h = bot-top
                aspect = w / float(h)
                if self.aspectRange[0] <= aspect <= self.aspectRange[1]:
                    # Aspect Ratio of found perforation is OK - save information
                    self.isInitialised = True
                    cx = x+left+((right-left)//2)
                    cy =  y+top+(h//2)
                    self.centre = (cx,cy)
                    self.ROIcentrexy[0] = cx
                    self.yDiff = cy - self.ROIcentrexy[1]
                    self.setPerforationSize( (w,h) )
                    self.found = True
                    print("SUCCESS")
                else:
                    print( "Perforation aspect {} ratio NOT OK - detection failed. Range: {}".format(aspect,self.aspectRange) )
        print "=> elasped settimg new perforation: %s ms" % t.msecs
            
        
    def setPerfPosition(self,cx,cy):
        # Sets the perforation position based on the centre
        self.centre = ( int(cx), int(cy) )
        self.position = ( int(cx-self.expectedSize[0]/2),int(cy-self.expectedSize[1]/2) )
        self.yDiff = int(self.centre[1]-self.ROIcentrexy[1])

    def findVertical(self):
        # Used for subsequent captures where we know the expected size and 
        # approximate position of perforation
        print( "findVertical" )
        self.found = False
        x,y = self.ROIxy
        w,h = self.ROIwh
        expectedW, expectedH = self.expectedSize
        xStart = w // 2
        yStart = self.ROIcentrexy[1]-y
        vwin = expectedH // 4
        threshold = self.thresholdVal( self.vROImedian )
        self.vROIthresh = self.vROImedian < threshold
        # Check if centre section is clear of data
        if self.vROIthresh[yStart-vwin:yStart+vwin].any():
            # Image data in centre area
            print "Image data in window"
        else:
            # Now to find the edges
            bot   = self.vROIthresh[yStart:].argmax()
            bot   = yStart+bot if bot>0 else h
            vROI = self.vROIthresh[:yStart]
            top   = vROI[::-1].argmax()
            top   = yStart-top if top>0 else 0
            # Check if detected is close to correct aspect ratio of perforation
            aspect =  float(expectedW) / float(bot-top)
            if self.aspectRange[0] <= aspect <= self.aspectRange[1]:
                if self.checkEdges==1:
                    # use top edge as reference and extrapolate bottom edge
                    bot = top+expectedH
                elif self.checkEdges==2:
                    # use bottom edge as reference
                    top = bot-expectedH                
                self.setPerfPosition( x + xStart, y + top + ((bot-top)//2) )
                self.found = True
            else:
                print( "Perforation aspect {} ratio NOT OK - detection failed. Range: {}".format(aspect,self.aspectRange) )
        if not(self.found):
            # Try alternative method 
            self.findVerticalAlternative()

    
    def findVerticalAlternative(self):
        # This is an alternative method, a bit more expensive
        # than findVertical, and is called on failure of
        # the previous findVertical. It uses Scipy labelling to segment the a strip 
        # of data from the ROI
        print( "findVerticalAlternative" )
        self.found = False
        cx = self.ROIwh[0]//2
        expectedW, expectedH = self.expectedSize

        candidate = None
        if self.vROIthresh.min() != self.vROIthresh.max(): 
            # Prevent a divide by zero because roi is all the same value. 
            # e.g. we have a frame completely white or black
            lbl,numLbl = nd.label(np.invert(self.vROIthresh))
            obj = nd.find_objects(lbl)
            brightest = 0
            for s in obj:
                # s is an np.slice object
                sBright = np.mean(self.vROImedian[s])
                #print s,sBright
                if sBright > brightest:
                    # Brightest area - if we get a brighter area after
                    # finding a potential candidate, reset the candidate
                    # to prevent false detection
                    brightest = sBright
                    candidate = None
                sHeight = s[0].stop - s[0].start
                if (self.heightRange[0] <= sHeight <= self.heightRange[1]) and sBright == brightest:
                    # Correct height and brightest
                    candidate = s[0]
        if candidate:
            x,y = self.ROIxy
            top = y+candidate.start
            bot = y+candidate.stop
            if self.checkEdges==1:
                # use top edge as reference and extrapolate bottom edge
                bot = top+expectedH
            elif self.checkEdges==2:
                # use bottom edge as reference
                top = bot-expectedH
            self.setPerfPosition( x + cx, top + ((bot-top)//2) )
            self.found = True

    def findLeftEdge(self):
        # Find the left edge of the perforation.
        # This can be used to compensate for any horizontal
        # movement of the film in the frame - this should be called
        # after finding the vertical position. The left edge is used
        # as the right may be overwhelmed with a bright image.
        # It uses the same ROI image created in findVertical
        print("findLeftEdge")
        if self.found:
            xStart = self.centre[0]-self.ROIxy[0]
            hROI = self.hROImedian[:xStart]
            # Horizontal section, and threshold
            threshVal = self.thresholdVal(hROI)
            #Make a single pixel wide strip, with the median of all the columns - and threshold it
            hROIthresh = hROI < threshVal
            # Position of edge of perforation
            left  = hROIthresh[::-1].argmax() 
            left  = xStart-left if left>0 else 0
            self.position = ( left + self.ROIxy[0], self.position[1] )
            self.centre = (left + (self.expectedSize[0]//2) + self.ROIxy[0], self.centre[1] )
        else:
            raise Exception('Error - Cannot do findLeftEdge until vertical has been found')

    def find(self,img):
        # Find perforation position in the image
        if self.isInitialised:
            self.vROImedian = self.verticalMedian(img[self.ROIslice])
            self.findVertical()
            if self.found and self.checkLeftEdge:
                cy = self.centre[1]-self.ROIxy[1]
                self.hROImedian = self.horizontalMedian( img[self.ROIslice], cy )
                self.findLeftEdge()
        else:
            # We haven't initialised or run findFirstFromCoords 
            raise Exception('Error - Perforation detection not initialised.')

