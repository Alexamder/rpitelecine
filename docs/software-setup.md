# Setting up the rpiTelecine software

These are the steps required to get the Python scripts working with my 
telecine hardware. I am currently using a Raspberry Pi B version 2 - as the telecine 
processing really benefits from additional memory and the extra processor cores.
These instructions were tested using NOOBS 1.4.0 released on 18 February 2015.
A main prerequisite is the Python-picamera library, which is installed by default with
the current version of Raspbian. Other prerequisites are WiringPi2, WiringPi2-Python and OpenCV.

## Download and install NOOBS

Get the latest version from http://www.raspberrypi.org/downloads/
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
Python-dev and python-setuptools are used to install wiringPi2; OpenCV is used in the rpiTelecine scripts 
to provide a rudimentary GUI and image saving capability, and Scipy is used for some simple image analysis.

```
$ sudo apt-get update
$ sudo apt-get upgrade
$ sudo apt-get install python-dev python-setuptools 
$ sudo apt-get install libopencv-dev python-opencv python-scipy
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

