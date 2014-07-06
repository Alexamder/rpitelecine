# RPi Telecine construction

## Chassis

The chassis is constructed mainly from [Makerbeam](http://www.makerbeam.eu/) 
10mm extruded aluminium, and associated accessories. The Nema 17 stepper 
motors use the Makerbeam metal bracket, and the servo motors use the lasercut
acrylic servo mount. Arms for the pinch rollers are attached using the
bearing mounts, and the PCB slots between two 10cm beams. The Raspberry Pi in a
Pibow case is attached to the front beam with long steel M3 screws in place
of the standard nylon ones. A long camera ribbon cable goes from the Pi to the
camera.

## 3d printed parts

Various parts in the telecine were 3d printed. A fair amount of precision is required for the 
film handling. It's important that the film path is pretty level - from film-spool to motor 
to gate to motor to take-up spool. 
[Shapeways](http://www.shapeways.com/) and [3dPrintUK](http://www.3dprint-uk.co.uk/)
were used. Shapeways offer a variety of materials and colours, and 3dPrintUK are slightly 
faster and cheaper for larger items - but only in white nylon.

Parts were designed in [Freecad](http://freecadweb.org/), and STL files were sent to
the 3d printing service. Freecad allows designs to be made based on cross-sectional
drawings, and results have been very good.

* Film Gate
* Pi camera mount
* Film roller on stepper motor
* Pinch roller
* Film Idler rollers
* Spool tables
* Light box
* Makerbeam end-stop (protects rubber band)

The film rollers and pinch rollers were printed in Shapeways' frosted detail plastic,
as this gives a good smooth surface for gripping the film edges. First version in 
white standard nylon slipped more. The pinch rollers use bearing races so they can rotate
freely. The film rollers fit steppers with a 5mm D shaped shaft. A little bit of electrical 
tape was used on the shaft to make a tight fit.

Pinch rollers are mounted on swinging arms, and use rubber bands made from an old bicycle 
inner tube to hold the roller in tension with the motor mounted (capstan) roller.
The arms can be released in order to remove the film.

The light box serves to mix the colours of the white and turquoise LEDs, and to diffuse the
light to create a flat area of illumination behind the gate.
The gate and camera mount fit into the slots on the Makerbeam - allowing adustment while
keeping alignment straight.

## Hacked servos

The film spool tables are attached directly to the splines of the servos. The servos
are standard inexpensive TowerPro MG995s (or copies), but modded for continuous
rotation by pulling out a metal pin that stops the gears rotating 360 degrees, and 
removing the feedback potentiometer. The control PCB was also removed, and two wires
soldered directly to the motor - effectively turning the servo into a compact
simple geared motor. There are various instructions dotted around the net for this
process.

The advantage of using servos is the simplicity of attaching the spool table - it just
uses a single m3 screw, and holds extremely securely. However any DC motor would be suitable.
Film spools are not fixed on the tables - they are designed to rotate freely so film can
be pulled off the reel, and the take-up spool rotates with a little bit of friction, rotating
enough to take up the slack. The motors are designed just to rotate in one direction - in order 
to pull the film onto the spool. 

## Camera and Lens

The camera is screwed onto a 3d printed bracket which fits into the slot in a short piece of Makerbeam.
It can be fixed securely, but allows for adjustment and focusing the image. 
To focus closer the Raspberry Pi camera's lens needs to be carefully unscrewed almost
as far as it can. This is not enough to get an 8mm frame large enough in the frame, so an additional
lens is required. 

The first version of the camera mount allowed fixing of a simple
(and inexpensive) smartphone close-up/macro lens. These can be got for cheap from Ebay.
Results using this lens was just about acceptable - the centre of the frame was
pretty sharp, but got softer away from the centre with a fair amount of colour fringing. My 
first examples on Youtube use this lens. Not bad for a lens that costs less than a fiver.

Much better is its replacement - a coated Steinheil triplet, available for a reasonable price from
[Surplus Shed](http://www.surplusshed.com/pages/item/pl1033.html) in the USA. This lens is much sharper
with little chromatic abberation and has less distortion than the smartphone lens. 
It was suggested for macro use by rkinch [in this thread on the Pi forums](http://www.raspberrypi.org/forums/viewtopic.php?f=43&t=43985&start=52).
The camera mount design was adjusted for this lens.


