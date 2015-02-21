# Setting up the rpiTelecine software

These are the steps required to get the Python scripts working with my 
telecine hardware. I am currently using a Raspberry Pi B version 2 - as the telecine 
processing really benefits from additional memory and the extra processor cores.
Other prerequisites are OpenCV, WiringPi2 and WiringPi2-Python

## Download and install NOOBS

Get the latest version from http://www.raspberrypi.org/downloads/
These instructions were tested using NOOBS 1.4.0 released on 18 February 2015. 
Copy it on a good fast Micro-SD card as per the directions on the Raspberry Pi web site. 
Boot your fresh SD card and install Raspbian.

## raspi-config

When the Pi reboots, various settings are required in raspi-config which runs when the system
starts for the first time. These settings can be done at any time by entering the following at the command line:
```
$ sudo raspi-config
```

* 2 Change user password - it's always a good idea. Make a note of it.
* 5 Enable Camera

The rest of the settings are in the Advanced section:

* A3 Memory Split - Set to 192MB. For full resolution stills, Python picamera requires the GPU to have more RAM than the default
* A4 SSH - Enable SSH if you use SSH to connect to the Pi, or to transfer files from it
* A6 SPI - Enable SPI, and set the kernel module to load by default

Reboot the Pi

## Set up network

Plug in a network cable, or set up the wireless network adapter.
For the latter, the easiest way is to go into LXDE with 'startx' and click Menu->Preferences->WiFi Configuration

## Update and install packages

```
$ sudo apt-get update
$ sudo apt-get upgrade
$ sudo apt-get install python-dev python-setuptools 
```

## Install WiringPi2 and WiringPi2-Python

```
$ git clone git://git.drogon.net/wiringPi
$ cd wiringPi 
$ sudo ./build
$ cd 
$ git clone https://github.com/Gadgetoid/WiringPi2-Python.git
$ cd WiringPi2-Python
$ sudo python setup.py install
$ cd
```

## Install rpiTelecine scripts from Github

```
$ git clone https://github.com/jas8mm/rpiTelecine.git
$ cd rpiTelecine
```

## Install up-to-date OpenCV

Raspbian comes with openCV 2.3 - this is a bit long in the tooth. OpenCV 2.4 has many enhancements and bug fixes.
It's pretty straightforward to download and compile it - but will take a while. The following instructions are based
on the instructions at: http://robertcastle.com/2014/02/installing-opencv-on-a-raspberry-pi/

Dependencies:
```
$ sudo apt-get -y install build-essential cmake cmake-curses-gui pkg-config libpng12-0 libpng12-dev libpng++-dev libpng3 libpnglite-dev zlib1g-dbg zlib1g zlib1g-dev pngtools libtiff4-dev libtiff4 libtiffxx0c2 libtiff-tools libeigen3-dev
$ sudo apt-get -y install libjpeg8 libjpeg8-dev libjpeg8-dbg libjpeg-progs ffmpeg libavcodec-dev libavcodec53 libavformat53 libavformat-dev libgstreamer0.10-0-dbg libgstreamer0.10-0 libgstreamer0.10-dev libxine1-ffmpeg libxine-dev libxine1-bin libunicap2 libunicap2-dev swig libv4l-0 libv4l-dev python-numpy libpython2.6 python-dev python2.6-dev libgtk2.0-dev 
```

Download OpenCV source
```
$ wget --content-disposition http://sourceforge.net/projects/opencvlibrary/files/opencv-unix/2.4.10/opencv-2.4.10.zip/download
```

Unzip and prepare for build
```
$ unzip opencv-2.4.10.zip
$ cd opencv-2.4.10
$ mkdir release
$ cd release
$ ccmake ../
```
Pres 'c', Setup the options - as per the link above, and press 'c' again.
Press 'g' to generate the makefile.

Then 
```
$ make 
sudo make install
```
This takes about 3 hours on the Pi version 2. Much better than the 10 hours on an older single-core Pi.

