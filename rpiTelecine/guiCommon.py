# RPi Telecine common Pyside/GUI functions
#
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

import numpy as np
import cv2
from PySide import QtGui, QtCore

bins = np.arange(64).reshape(64,1)

def makeHistImage(img):
    h = np.zeros((300,256,3))
    h.fill(255)
    color = [ (255,0,0),(0,255,0),(0,0,255) ]
    for ch, col in enumerate(color):
        hist_item = cv2.calcHist([img],[ch],None,[64],[0,256])
        cv2.normalize(hist_item,hist_item,0,255,cv2.NORM_MINMAX)
        hist=np.int32(np.around(hist_item))
        pts = np.int32(np.column_stack((bins*4,hist)))
        cv2.polylines(h,[pts],False,col)
    return np.flipud(h)
    
def makeHistGreyImage(img, ch=None):
    h = np.zeros((200,256,3),dtype=np.uint8)
    h.fill(255)
    if ch==None or ch>2:
        # convert to grey
        img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    else:
        img = img[...,ch]
    histItem = cv2.calcHist([img],channels=[0],mask=None,histSize=[256],ranges=[0,256])
    histItem = cv2.normalize(histItem,alpha=0, beta=200, norm_type=cv2.NORM_MINMAX)
    hist = np.int32(np.around(histItem))
    for x,y in enumerate(hist):
        h[0:y,x,0:3]=0
    return np.flipud(h)

def makeQimage(img):
    h,w = img.shape[:2]
    bgra = np.empty( (h,w,4),dtype=np.uint8,order='C' )
    bgra[...,:3] = img 
    #bgra[...,3].fill(255)
    qi = QtGui.QImage(bgra.data,w,h,QtGui.QImage.Format_RGB32)
    qi.ndimage = bgra   # Need to save the underlying Numpy array with the Qimage
    return qi

# Class to implement the zoomable ImageViewer by subclassing QScrollArea
# Will probably want to extend this 

class ClickableLabel(QtGui.QLabel):

    clicked = QtCore.Signal(QtCore.QPoint)
    doubleClicked = QtCore.Signal(QtCore.QPoint)

    def __init(self, parent=None):
        super(ClickableLabel).__init__(self, parent)
 
    def mouseReleaseEvent(self, ev):
        self.clicked.emit(ev.pos())
    
    def mouseDoubleClickEvent(self, ev):
        self.doubleClicked.emit(ev.pos())

class ImageViewer(QtGui.QScrollArea):
    
    minScale = 0.1
    maxScale = 3.0
    fitContents = True
    scaleFactor = 1.0

    def __init__(self,parent=None):
        super(ImageViewer, self).__init__(parent)
        self.imageLabel = ClickableLabel()
        self.imageLabel.setBackgroundRole(QtGui.QPalette.Base)
        self.imageLabel.setSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Ignored)
        self.imageLabel.setScaledContents(True)
        self.setBackgroundRole(QtGui.QPalette.Dark)
        self.setWidget(self.imageLabel)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.imageLabel.doubleClicked.connect(self.clickedOnImage)
        #self.imageLabel.clicked.connect(self.clickedOnImage)
        
    def clickedOnImage(self,pos):
        print "CLICKED!"
        print "On label {} scale {} on image{}".format(pos,self.scaleFactor,pos/self.scaleFactor)
        

    def setImage(self,qimage):
        #self.qimage = qimage # keep reference to qimage around
        self.imageLabel.setPixmap(QtGui.QPixmap.fromImage(qimage))

    def zoomIn(self):
        self.scaleImage(1.25)

    def zoomOut(self):
        self.scaleImage(0.8)

    def normalSize(self):
        self.imageLabel.adjustSize()
        self.scaleFactor = 1.0

    def fitToWindow(self):
        self.imageLabel.adjustSize()
        wfactor = float( self.width()) / self.imageLabel.pixmap().width()
        hfactor = float( self.height() ) / self.imageLabel.pixmap().height()
        print ("fitToWindow w x h: {} x {}".format( self.width(),self.height() ))
        if wfactor > hfactor:
            newfactor = hfactor
        else:
            newfactor = wfactor
        factor = newfactor / self.scaleFactor * 0.98
        self.scaleImage(factor)

    def scaleImage(self, factor):
        self.scaleFactor = self.scaleFactor*factor
        self.scaleFactor = max(self.scaleFactor,self.minScale)
        self.scaleFactor = min(self.scaleFactor,self.maxScale)
        print("Scale factor: {}".format(self.scaleFactor))
        self.imageLabel.resize(self.scaleFactor * self.imageLabel.pixmap().size())
        self.adjustScrollBar(self.horizontalScrollBar(), factor)
        self.adjustScrollBar(self.verticalScrollBar(), factor)

    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value()
                                + ((factor - 1) * scrollBar.pageStep()/2)))
        
    