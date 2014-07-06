# RPi Telecine Project

This project consists of code and models for an 8mm film scanner project based around a Raspberry Pi model B and camera module.
Most of the code is written in Python.

The project is designed to be able to reliably capture each frame of a reel of 8mm film 
(Super 8 or Standard 8) as a high quality photo. Bracketing is possible to cope with underexposed
or dense film.

Once captured, the folder of image files can be transferred to a PC for further processing.

Design was somewhat inspired by the [Kinograph project](http://kinograph.cc/)

3d printed Gate was inspired [by this design](http://www.mets-telecinesystem.co.uk/index.php/how-its-made/making-the-film-gate).

Chassis makes use of [Makerbeam and accessories](http://www.makerbeam.eu/)

Code makes use of:

* Dave Hughes' [Python picamera library](https://pypi.python.org/pypi/picamera/1.5)
* [OpenCV Python bindings](http://opencv.org/)
* Numpy and Scipy

This is a work in progress, and hasn't yet been used on any precious films. It's a good idea to
test using only 'disposable films'. Ebay is a good source of old 'home movies'. Some test transfers are 
in the examples list below.

Examples
--------

* Overview: http://youtu.be/xm3jTsKSOtE
* London to Brighton: http://youtu.be/7-SdT0FMGkM
* Derby Day: http://youtu.be/9bVeMD78gXc
* Blackpool illuminations: http://youtu.be/ZH1QqgxNLk8
* Wings of Speed: http://youtu.be/DhBY11DGUps