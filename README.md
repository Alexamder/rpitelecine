# RPi Telecine Project

This project consists of code and models for a DIY 8mm film scanner project 
based around a Raspberry Pi model B Version 2 and camera module. It uses
a scratch-built film transport that doesn't rely on hacking an old projector.
3d printed and laser cut pieces are used with easily available hardware.

The controller code is written in Python - and a Qt based GUI is under 
construction to make capturing the film pretty straightforward.

RPiTelecine is designed to be able to reliably capture each frame of a reel of 
8mm film (Super 8 or Standard 8) as a high quality photo. 
Bracketing can be used to cope with underexposed or dense film.

Once captured, the folder of image files can be transferred to a PC for further processing.

It isn't very fast - at present it captures at about a frame a second. This is 
due to the speed of the Raspberry Pi camera, and the speed of the SD card. It's 
anticpated that the speed can be increased somewhat by optimising the camera
capture and parallelising various tasks.

Futher information is available in this Github repository:

* [Description of the electronics](docs/electronics.md)
* [Construction details](docs/mechanics.md)
* [Installing the software](docs/software-setup.md)
* [The GUI capture software](docs/software-gui.md)
* [Typical workflow used to digitise films](docs/workflow.md)
* [Hints for post production on a PC](post-production/README.md)
* [Detailed photos available in the images folder](images/)

![Overview of RPI telecine](images/overview.png)

## Video

Some test transfers are on Youtube:

These are from an earlier model, using a cheap dioptre lens, and captured
using a Raspberry Model B

* Overview: http://youtu.be/xm3jTsKSOtE
* London to Brighton: http://youtu.be/7-SdT0FMGkM
* Derby Day: http://youtu.be/9bVeMD78gXc
* Blackpool illuminations: http://youtu.be/ZH1QqgxNLk8
* Wings of Speed: http://youtu.be/DhBY11DGUps

## Acknowledgements

Thanks to [Raspberry Pi](http://raspberrypi.org) for a splendid little computer and excellent camera module!

Rpi Telecine project design was somewhat inspired by the [Kinograph project](http://kinograph.cc/)

3d printed Gate was inspired [by this design](http://www.mets-telecinesystem.co.uk/index.php/how-its-made/making-the-film-gate).

Chassis makes use of [Makerbeam and accessories](http://www.makerbeam.eu/)

Code makes use of:

* Dave Hughes' [Python picamera library](https://pypi.python.org/pypi/picamera)
* [OpenCV Python bindings](http://opencv.org/)
* Numpy, Scipy, PySide

This is a work in progress, and hasn't yet been used on any precious films. It's a good idea to
test using only 'disposable films'. Ebay is a good source of old 'home movies'. 
