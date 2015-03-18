# RPi Telecine job setuo widget class
#
# Widget class to setup a telecine job
#
# Shows a zoomable preview of the full captured frame with crop lines and
# detected perforation.
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

from __future__ import division
import os
import numpy as np
import time
import cv2
from PySide import QtCore, QtGui 

from rpiTelecine.ui.setupJob import *
import rpiTelecine.guiCommon as guiCommon

class CameraPreviewUpdater(QtCore.QThread):
    # Thread to update camera preview image
    # It will take a picture immediate on a call to takePicture
    # or after 1/2 second after calling updatePicture
    # to allow for updates in the UI before taking picture
    pictureReady = QtCore.Signal(np.ndarray)
    timer = QtCore.QTimer()
    mutex = QtCore.QMutex()
    delay = 500
    exiting = False
    ready = False
    active = True

    def __init__(self,camera,parent = None):
        super(CameraPreviewUpdater, self).__init__(parent)
        self.camera=camera
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.takePicture)

    def takePicture(self):
        self.ready=True
        
    def updatePicture(self):
        self.ready = False
        self.timer.stop()
        self.timer.start(self.delay)

    def run(self):
        global previewImg
        while not self.exiting:
            if self.active and self.ready:
                print "Taking picture"
                self.ready = False
                img = self.camera.take_picture()
                self.mutex.lock()
                previewImg = img
                print("Picture shape: {}".format(img.shape))
                self.mutex.unlock()
                print "Picture taken"
                self.pictureReady.emit(img)
            else:
                # Needed to keep UI responsive
                QtCore.QThread.msleep(50)

    def pause(self, p=True):
        self.active = not(p)

    def stop(self):
        self.mutex.lock()
        self.exiting = True
        self.mutex.unlock()
        self.wait()
'''
Class for the preview image - showing camera image, crop lines, etc.
Elements we show are: Current frame image from camera, optional overlay
showing clipped pixel values; crop rectangle in green; detected perforation 
in red; perforation detection area in yellow; offset between detected 
perforation and centre of detection area used for correcting transport to
the next frame
'''
class PreviewScene( QtGui.QGraphicsScene ):


    histRectChanged = QtCore.Signal()
    doubleClicked = QtCore.Signal(tuple)

    def __init__(self,parent=None):
        super(PreviewScene,self).__init__(parent)

        self.setBackgroundBrush(QtGui.QColor(64,64,64))

        # Set up the various objects on the view
        # Pixmap of preview image
        print "Adding pixmap"
        self.pixmap = self.addPixmap(QtGui.QPixmap(500,500))
        print self.pixmap

        # Pixmap for clipped image
        self.clippedPixmap = self.addPixmap(QtGui.QPixmap(500,500))
        #self.clippedPixmap.setOpacity(0.75)
        self.clippedPixmap.setVisible(False)

        # Crop rectangle
        pen = QtGui.QPen(QtCore.Qt.green, 11, QtCore.Qt.SolidLine)
        self.cropRect = self.addRect(0,0,100,100,pen)

        # Perforation rectangle
        pen.setColor(QtCore.Qt.red)
        self.perfRect = self.addRect(0,0,110,110,pen)

        # ROI rectangle
        pen.setColor(QtCore.Qt.yellow)
        self.ROIrect = self.addRect(0,0,50,50,pen)

        # Area for histogram calculation
        pen = QtGui.QPen(QtCore.Qt.green, 5, QtCore.Qt.DotLine)
        self.histRect = self.addRect(0,0,60,60,pen)
        self.histRectProportion = 0.75

        # Perforation offset line
        pen = QtGui.QPen(QtCore.Qt.darkBlue, 5, QtCore.Qt.DotLine)
        self.vDiffLine = self.addLine(0,0,0,100,pen)

        # Show or hide the guideline items
        self.guidelineList = ( self.cropRect,
                               self.histRect,
                               self.perfRect,
                               self.ROIrect,
                               self.vDiffLine )
        self.guidelinesVisible = False
        # We can dim the guidelines if we haven't detected a perforation
        self.guildelinesBright = True
        # Offset from centre of perforation to top left of crop rectangle
        
        self.cropOffset = None
        self.perforationCentre = None

    @property
    def guidelinesVisible(self):
        return self._guidelinesVisible
    
    @guidelinesVisible.setter
    def guidelinesVisible(self,visible):
        visible = (visible==True)
        self._guidelinesVisible = visible
        for item in self.guidelineList:
            item.setVisible( visible )

    @property
    def guidelinesBright(self):
        return self._guidelinesBright
    
    @guidelinesBright.setter
    def guidelinesBright(self,bright):
        bright = (bright==True)
        self._guidelinesBright = bright
        opacity = 0.8 if bright else 0.4
        for item in self.guidelineList:
            item.setOpacity( opacity )

    @property
    def cropOffset(self):
        return self._cropOffset

    @cropOffset.setter
    def cropOffset(self,offset):
        if type(offset) == tuple:
            self._cropOffset = offset
            # update crop rectangle position
            perfCentre = self.perfRect.rect().center()
            newCropTopLeft = perfCentre + QtCore.QPoint(*offset)
            self.cropRect.setPos( newCropTopLeft )
        else:
            self._cropOffset = None

    @property
    def cropSize(self):
        return self._cropSize

    @cropSize.setter
    def cropSize(self,size):
        self._cropSize = size
        self.cropRect.rect().setSize(*size)

    @property
    def perforationCentre(self):
        return self._perforationCentre

    @perforationCentre.setter
    def perforationCentre(self,centre):
        if type(centre) == tuple:
            self._perforationCentre = centre
            # Calulate offset between centre and top left of perforation
            offset = (self.perfRect.rect().size() / 2).toTuple()
            perfCentre = QtCore.QPoint(*centre)
            newPos = perfCentre - QtCore.QPoint(*offset)
            self.perfRect.setPos(newPos)
            # Now work out difference between centre and roi Centre
            roiCentre = self.ROIrect.rect().centre()
            self.vDiffLine.setLine( roiCentre, perfCentre )
        else:
            self._perforationCentre = None
            

    @property
    def perforationSize(self):
        return self._perforationSize

    @perforationSize.setter
    def perforationSize(self,size):
        self._perforationSize = size
        # Resize the perforation rectangle and centre it on the original centre
        centre = self.perfRect.rect().center().toTuple()
        self.perfRect.rect().setSize(*size)
        self.perforationCentre = centre

    @property
    def roiRect(self):
        return self._roiRect

    @roiRect.setter
    def roiRect(self,rect):
        self._roiRect = rect
        self.ROIrect.setRect( *rect )
        
    @property 
    def mainPixmap(self):
        return self.pixmap.pixmap()
    
    @mainPixmap.setter
    def mainPixmap(self,qimg):
        self.pixmap.setPixmap( QtGui.QPixmap.fromImage(qimg) )
        self.setSceneRect( self.pixmap.pixmap().rect() )

    @property
    def clipPixmap(self):
        return self.clippedPixmap.pixmap()
    
    @clipPixmap.setter
    def clipPixmap(self,qimg):
        if type(qimg) == QtGui.QImage:
            # display clipped pixmap and make visible
            self.clippedPixmap.setPixmap( QtGui.QPixmap.fromImage(qimg) )
            self.clippedPixmap.setVisible(True)
        else:
            self.clippedPixmap.setVisible(False)

    def mouseDoubleClickEvent(self,event):
        # Emits the integer coordinates of a double-click
        pos = event.scenePos().toPoint().toTuple()
        print( "Doubleclicked on scene: {}".format(pos) )
        self.doubleClicked.emit( pos )

    @property
    def histCropProportion(self):
        return self._histCropProportion


    def updateCrop( self, x,y,w,h ):
        self.cropRect.setRect(x,y,w,h)
        self.updateHistRect()  

    def updateHistArea(self,val):
        self.histRectProportion = float(val) / 100
        self.updateHistRect()

    def updateHistRect(self):
        # Set histogram rectangle inside crop rectangle
        x,y,w,h = self.cropRect.rect().getRect()
        hw, hh = w*self.histRectProportion, h*self.histRectProportion
        hx, hy = x+((w-hw)/2), y+((h-hh)/2)
        self.histRect.setRect(hx,hy,hw,hh)
        self.histRectChanged.emit()

    def getHistogramRect(self):
        # Returns histogram rectangle
        x,y,w,h = self.histRect.rect().getRect()
        visible = self.histRect.isVisible()
        return (visible, x,y,w,h)

# This is the View of the preview scene - allows zooming and panning
class PreviewView( QtGui.QGraphicsView ):

    def __init__(self,scene=None,parent=None):
        super(PreviewView,self).__init__(scene,parent)
        # Mouse dragging to move preview
        self.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)

        # Set an initial scale of 33%
        self.scale(0.33,0.33)
        self.centerOn(self.scene().pixmap)
        self.scaleFactor = 1.15

    def wheelEvent(self, event):
        # Use mouse for zooming the preview image and limit extents
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        if event.delta() > 0:
            self.zoomIn()
        else:
            self.zoomOut()

    def One2one(self):
        # Set the view to 100%
        self.setTransform(QtGui.QTransform.fromScale(1.0, 1.0))

    def fitToWindow(self):
        # Resize to fit image in view window
        self.fitInView(self.scene().pixmap, QtCore.Qt.KeepAspectRatio)

    def zoomIn(self):
        # Use mouse for zooming the preview image and limit extents
        if self.transform().m11() < 4.0: 
            self.scale(self.scaleFactor, self.scaleFactor);

    def zoomOut(self):
        if self.transform().m11() > 0.1:
            #Zoom out
            self.scale(1.0 / self.scaleFactor, 1.0 / self.scaleFactor)

class SetupJob( QtGui.QWidget ):

    # Signals
    filmTypeChanged = QtCore.Signal(str) # Emits new film type
    jobNameChanged = QtCore.Signal(str) # Emits a change of job name
    outputDirectoryChanged = QtCore.Signal(str) # Emits new output dir name

    cropAspectRatio = None

    def __init__(self,camera,tc,pf,parent=None):
        super(SetupJob, self).__init__(parent)

        self.camera = camera

        self.filmType = 'super8'
        self.pf = pf
        self.tc = tc
        
        self.perforationFound = False

        self.ui = Ui_SetupJobForm()
        self.ui.setupUi(self)
        self.statusbar = parent.ui.statusbar

        self.scene = PreviewScene(parent)

        # Set up preview with blank image
        w,h = self.imageWidth, self.imageHeight = self.camera.MAX_IMAGE_RESOLUTION
        self.previewImg = np.zeros( (h,w,3), dtype=np.uint8 )
        self.clippedImg = np.zeros( (h,w,3), dtype=np.uint8 )
        self.previewQimg = QtGui.QImage(w, h, QtGui.QImage.Format_RGB32)
        self.previewQimg.fill(QtGui.QColor(50,50,50))
        self.scene.mainPixmap = self.previewQimg

        # Timer used so we don't constantly update histogram
        self.histogramTimer = QtCore.QTimer()
        self.histogramTimer.setSingleShot(True)
        self.histogramTimer.timeout.connect(self.makeHistogram)
        self.scene.histRectChanged.connect( self.makeHistogramDelayed )

        # Preview Window
        self.view = PreviewView(self.scene,self)
        self.ui.layoutPreview.insertWidget(0,self.view)
        self.ui.btnOne2one.clicked.connect( self.view.One2one )
        self.ui.btnZoomIn.clicked.connect( self.view.zoomIn )
        self.ui.btnZoomOut.clicked.connect( self.view.zoomOut )
        self.ui.btnFit.clicked.connect( self.view.fitToWindow )

        # Job Setup tab
        self.ui.btnChangeJobName.clicked.connect(self.changeJobName)
        self.ui.btnChooseDir.clicked.connect(self.chooseOutputDirectory)
        self.ui.btnChangeFilm.clicked.connect(self.changeFilmType)
        self.ui.spinShutter.valueChanged.connect( self.updateCameraShutterSpeed )
        self.ui.spinGainR.valueChanged.connect( self.updateCameraGains )
        self.ui.spinGainB.valueChanged.connect( self.updateCameraGains )
        self.ui.chkShowClipped.stateChanged.connect( self.makeClippedImage )

        # Set crop position, size
        self.ui.spinCropX.valueChanged.connect( self.updateCropRect )
        self.ui.spinCropY.valueChanged.connect( self.updateCropRect )
        self.ui.spinCropW.valueChanged.connect( self.updateCropWidth )
        self.ui.spinCropH.valueChanged.connect( self.updateCropHeight )
        self.ui.spinHistArea.valueChanged.connect( self.scene.updateHistArea )

        self.ui.cmbAspectFix.currentIndexChanged.connect( self.setAspectRatio )

        # Preview updater thread
        self.previewUpdater = CameraPreviewUpdater(self.camera,parent)
        self.previewUpdater.pictureReady.connect(self.updatePicture)
        self.previewUpdater.start()
        self.ui.btnStop.clicked.connect( self.previewUpdater.updatePicture )

        # Update or initialise perforation detection
        self.scene.doubleClicked.connect( self.locatePerforation )

    def close(self):
        # Need to gracefully stop the preview update
        print "Exiting preview"
        self.previewUpdater.stop()

    def pauseUpdating(self,p=True):
        self.previewUpdater.pause(p)

    def changeJobName(self):
        # Uses input dialog to get job name from user
        ok = False
        message = "Enter job name."
        while not ok:
            text, result = QtGui.QInputDialog.getText(self, "Change Job Name", message)
            ok = True
            if result:
                # Sanitise job name as we'll be using it as a folder name
                delchars = ''.join(c for c in map(chr, range(256)) if not c.isalnum())
                jobName = text.encode('ascii','ignore')
                jobName = jobName.translate(None,delchars)
                if jobName:
                    self.ui.lblJobName.setText(jobName)
                    self.jobNameChanged.emit(jobName)
                else:
                    # Invalid job name
                    ok = False
                    message = "Invalid characters. Try again.<br>Enter job name."

    def chooseOutputDirectory(self):
        # Sets the output directory
        d = os.path.dirname(self.ui.lblProjectDir.text())
        d = d if os.path.exists(d) else os.getcwd()
        flags = QtGui.QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly
        d = QtGui.QFileDialog.getExistingDirectory(self, "Open Directory", d, flags)
        if os.path.exists(d):
            self.ui.lblProjectDir.setText(d)
            self.outputDirectoryChanged.emit(d)

    def changeFilmType(self):
        # Warning message before changing film
        f = ('Standard 8','Super 8') if self.filmType=='std8' else ('Super 8','Standard 8')
        message = 'Are you sure you want to change<br>from <b>{}</b> to <b>{}</b> film?<br>Some settings will be reset.'.format(*f)
        reply = QtGui.QMessageBox.question(self, 'Message',message, QtGui.QMessageBox.Yes | 
            QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            f = 'super8' if self.filmType=='std8' else 'std8'
            self.setFilmType(f,forceChange=True)

    def setFilmType(self, f, forceChange=False):
        # Sets up the film type - resets the perforation detection
        if forceChange or f != self.filmType:
            fname = 'Standard 8' if f=='std8' else 'Super 8'
            self.ui.lblFilmType.setText(fname)
            self.filmType = f
            self.pf.init( f, imageSize=self.camera.resolution, expectedSize=(0,0), cx=0 )
            self.filmTypeChanged.emit(f)

    def updateCameraShutterSpeed(self):
        # Called when using the spinbox
        self.camera.shutter_speed = int(self.ui.spinShutter.value())
        self.previewUpdater.updatePicture()

    def updateCameraGains(self):
        awb_gains = ( float(self.ui.spinGainR.value()),
                      float(self.ui.spinGainB.value()) )
        self.camera.awb_gains = awb_gains
        self.previewUpdater.updatePicture()

    def setCameraExposure(self,shutter,gain_r,gain_b):
        self.camera.setup_cam( shutter = int(shutter), 
                               awb_gains = ( float(gain_r),float(gain_b) ) )
        self.ui.spinShutter.setValue(self.camera.shutter_speed)
        self.ui.spinGainR.setValue(float(gain_r))
        self.ui.spinGainB.setValue(float(gain_b))

    def updateExposureControls(self):
        self.ui.spinShutter.setValue(self.camera.shutter_speed)
        gain_r, gain_b = self.camera.awb_gains           
        self.ui.spinGainR.setValue(float(gain_r))
        self.ui.spinGainB.setValue(float(gain_b))

    def jobName(self):
        return self.ui.lblJobName.text()

    def setJobName(self, jobName):
        self.ui.lblJobName.setText( jobName )

    def jobDir(self):
        return self.ui.lblJobDir.text()

    def setJobDir(self, jobDir):
        # Update the job dir label
        self.ui.lblJobDir.setText( jobDir )

    def projectDir(self):
        return self.ui.lblProjectDir.text()

    def setProjectDir(self, projectDir):
        # Update the job dir label
        self.ui.lblProjectDir.setText( projectDir )

    def updatePicture(self,img):
        # Updates the preview image and histogram
        print("Updating picture {}".format(id(img)))
        # keep preview image around to be able to recreate histogram
        self.previewImg = img
        self.previewQimg = guiCommon.makeQimage(img)
        self.scene.mainPixmap = self.previewQimg
        #self.scene.updatePixmap(self.previewQimg)
        w,h = self.camera.resolution
        self.imageWidth, self.imageHeight = w,h
        print("Width {}, Height {}".format(self.imageWidth, self.imageHeight))
        self.view.setSceneRect(0, 0, w, h)
        self.makeHistogram()
        self.makeClippedImage()
        
        self.scene.guidelinesVisible = self.perforationFound
        if self.perforationFound:
            pass
        
    def makeHistogramDelayed(self):
        if self.histogramTimer.isActive():
            # reset and restart timer
            self.histogramTimer.stop()
        self.histogramTimer.start(250)

    def makeHistogram(self):
        # Makes the histogram from the image based on rect in preview scene
        # But only do so if the timer isn't running
        visible, x,y,w,h = self.scene.getHistogramRect()
        if visible:
            img = self.previewImg[y:y+h,x:x+w]
            hist = guiCommon.makeHistImage(img)
        else:
            hist = guiCommon.makeHistImage(self.previewImg)
        print("Make histogram v:{} x:{} y:{} w:{} h:{} shape:{}".format(visible, x,y,w,h,hist.shape))
        self.histqi = guiCommon.makeQimage(hist)
        self.ui.lblHistogram.setPixmap(QtGui.QPixmap.fromImage(self.histqi))
        
    def makeClippedImage(self, state=0):
        # Makes an image of clipped pixels - i.e 254/255 using OpenCV
        if self.ui.chkShowClipped.isChecked():
            ret,img = cv2.threshold(self.previewImg,254,255,cv2.THRESH_BINARY)
            self.clippedImg = img
            self.clippedQimg = guiCommon.makeQimage(img)
            self.scene.clippedPixmap = self.clippedQimg
            #self.scene.updateClippedPixmap(self.clippedQimg)
        else:
            self.scene.clippedPixmap = None
            #self.scene.updateClippedPixmap(None)

    def setAspectRatio(self,idx):
        txt = self.ui.cmbAspectFix.itemText(idx)
        if txt == "4:3":
            self.cropAspectRatio = 4.0/3.0
        elif txt == "16:9":
            self.cropAspectRatio = 16.0/9.0
        else:
            self.cropAspectRatio = None
        self.updateCropHeight( self.ui.spinCropH.value() )
    
    '''
    Crop handling
    Setting the crop is available when there is a perforation, as the crop
    is based on an offset from the centre of the perforation
    '''
    @property
    def crop( self ):
        x = self.ui.spinCropX.value()
        y = self.ui.spinCropY.value()
        w = self.ui.spinCropW.value()
        h = self.ui.spinCropH.value()
        ha = self.ui.spinHistArea.value()
        return (x,y,w,h,ha) 

    @crop.setter
    def crop( self, crop ):
        x,y,w,h,ha = crop
        # Set up crop controls
        self.ui.spinCropX.setValue( x )
        self.ui.spinCropY.setValue( y )
        self.ui.spinCropW.setValue( w )
        self.ui.spinCropH.setValue( h )
        self.ui.spinHistArea.setValue( ha )
        self.updateCropRect()
    
    def updateSpinBox(self,sb,val):
        # Update a spinbox while blocking signals
        # Useful while adjusting a fixed aspect ratio crop
        sb.blockSignals(True)
        sb.setValue(val)
        sb.blockSignals(False)
    
    def updateCropWidth(self,w):
        # called on change of size
        maxW = self.imageWidth-50
        print "updating W: maxW {}".format(maxW)
        self.ui.spinCropX.setRange( 25,maxW-w )
        self.ui.spinCropW.setRange( 50,maxW )
        if type(self.cropAspectRatio) is float:
            print "update width aspect"
            maxH = self.imageHeight-50
            h = min(w // self.cropAspectRatio,maxH)
            self.updateSpinBox( self.ui.spinCropH, h )
            w = min(h * self.cropAspectRatio,maxW)
            self.updateSpinBox( self.ui.spinCropW, w )
        self.updateCropRect()

    def updateCropHeight(self,h):
        # called on change of size
        maxH = self.imageHeight-50
        self.ui.spinCropY.setRange( 25,maxH-h )
        self.ui.spinCropH.setRange( 50,maxH )
        print "updating H: maxH {}".format(maxH)
        if type(self.cropAspectRatio) is float:
            print "update height aspect"
            maxW = self.imageWidth-50
            w = min(h * self.cropAspectRatio,maxW)
            self.updateSpinBox( self.ui.spinCropW, w )
            h = min(w // self.cropAspectRatio,maxH)
            self.updateSpinBox( self.ui.spinCropH, h )
        self.updateCropRect()

    def updateCropX(self,x):
        # called on change of size
        w = self.ui.spinCropW.value()
        maxX = self.imageWidth-50-w
        self.ui.spinCropX.setRange( 25,maxX )
        self.updateCropRect()   

    def updateCropY(self,y):
        # called on change of size
        h = self.ui.spinCropH.value()
        maxY = self.imageHeight-50-h
        self.ui.spinCropY.setRange( 25,maxY )
        self.updateCropRect()   

    def updateCropRect(self,val=0):
        # updates crop rectangle from UI, sets limits
        # updates offset to centre of perforation rectangle
        maxW = self.imageWidth-50
        maxH = self.imageHeight-50
        w = self.ui.spinCropW.value()
        h = self.ui.spinCropH.value()
        self.ui.spinCropX.setRange( 25,maxW-w )
        self.ui.spinCropW.setRange( 50,maxW )
        self.ui.spinCropY.setRange( 25,maxH-h )
        self.ui.spinCropH.setRange( 50,maxH )
        x = self.ui.spinCropX.value()
        y = self.ui.spinCropY.value()
        if x+w > maxW:
            x = max( maxW-w, 25 )
            self.updateSpinBox( self.ui.spinCropX, x )
        if y+h > maxH:
            y = max( maxH-h, 25 )
            self.updateSpinBox( self.ui.spinCropY, y )
        self.scene.updateCrop( x,y,w,h )
        self.cropPos = (x,y)
        self.cropSize = (w,h)        
        print("Crop: pos:{} size:{} maxW:{} maxH:{}".format(self.cropPos,self.cropSize,self.ui.spinCropW.maximum(),self.ui.spinCropH.maximum()) )

    @property
    def perforation(self):
        filmType = self.pf.filmType
        cx = self.pf.ROIcentrexy[0]
        w, h = self.pf.expectedSize
        return ( filmType, int(cx), int(w), int(h) )

    @perforation.setter
    def perforation(self,settings):
        filmType, cx, w, h = settings
        cam_crop = self.camera.camera_crop
        imageSize = cam_crop[2:]
        expectedSize = (w,h)
        self.pf.init( filmType, imageSize,expectedSize,int(cx) )
        print "expectedSize: {}".format(expectedSize)
        
    def locatePerforation(self, pos ):
        # Do an initial perforation find based on the supplied coordinates
        self.pf.findFirstFromCoords( self.previewImg, pos, 20 )
        if self.pf.found:
            x,y = self.pf.position
            w,h = self.pf.expectedSize
            # Now do a normal find
            self.pf.find( self.previewImg )
            if self.pf.found:
                print "Perforation found: {} {}".format(self.pf.position,self.pf.expectedSize)
                text = "<b>Perforation found</b><br><br>Centre: {} Size: {}".format(self.pf.position,self.pf.expectedSize)
            else:
                text = "<b>Perforation not found</b><br><br>Try adjusting exposure and double clicking again in the centre of the perforation."
            self.ui.lblPerforationInfo.setText(text)
            
                    




