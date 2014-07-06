# Workflow for a telecine job

This is the basic workflow to convert a film. It's mainly designed for the Pi
to run headless while doing the capture. The setup routine uses a GUI of sorts - 
basically shows a preview of the crop settings, but it is mainly keyboard
controlled.

## Set base exposure

If base whitebalance/shutter speed hasn't been set, or if lighting
has been altered:

1. Without film in gate, put a neutral density filter in front of lamp diffuser
2. Run tc-setwhitebalance.py to set base exposure and white balance

## Set up telecine job

1. Lace the film and pull it through the gate manually. If possible move it to a frame.
2. Run tc-setupjob.py [-b|--brackets] [-s8|--standard8] <jobname>
3. Click in a sprocket hole to set up frame detection
4. Calibrate the transport - press the # key - or do each step individually with u|t|y
5. Use '[' and ']' keys to jump forward or back; or ','/'.' to move one frame forward, back
6. Adjust the crop with arrow keys and PgUp/PgDn
7. Adjust the exposure (+/-) and red/blue gains (rR & bB). Toggle greyscale with g. Toggle clipping with 'c'
8. Use transport keys to move the film to the first frame in the job.
9. Save settings to job ini file with s. To exit without saving use Esc.

The preview can be used to check focus, exposure, etc. It's slow, but just about 
usable over a remote X connection (via ssh).

## Run job

1. Run tc-run.py jobname -s start-frame -e end-frame [-j] [-r] [-b]

'-j' option saves images to jpeg. '-r' runs the transport backwards. '-b' forces bracketing.
Start frame and end frame numbers are inclusive. The tc.run.py runs in the console,
so you can use the screen command to run in the background and headless. 

5 consecutive failures to detect a perforation will stop the job. This is usually at
the end of the reel - or if there's some damage on the film.

All frames will be saved to a sub folder named after the job name. Failed 
perforation detections will be saved as full frames as well as cropped, so they
can be cropped manually if necessary.

## Keys in setup routine

| Keys       | Description                                     |
| ---------- | ----------------------------------------------- |
| s          | Save current settings                           |
| Esc	     | Escape without saving                           |
| c	     | Toggle clipped colours                          |
| g	     | Toggle grayscale                                |
| d	     | Cycle through DRC settings (off,low,med,high)   |
| - +	     | Reduce / increase shutter                      |
| r  R	     | Reduce / increase red gain                     |
| b  B	     | Reduce / increase blue gain                    |
| p	     | Toggle perforation detection                    |
| o	     | Centre frame                                    |
| i	     | Redetect perforation                            |
| #	     | Calibrate Transport (same as u/t/y)             |
| t  y	     | Calibrate transport forward/backward            |
| u	     | Calibrate pixels per motor step                 |
| .  ,	     | Previous / next frame                          |
| <  >	     | Back or forwards 18 frames                      |
| [  ]	     | Fast wind back / forward 18 frames             |
| {  }	     | Fast wind back / forward 180 frames            |
| Arrows     | Move crop                                       |
| PgUp	     | Make crop larger                                |
| PgDn	     | Make crop smaller                               |
| Home	     | Nudge motor forward                             |
| End	     | Nudge motor backward                            |
| 1-4	     | Display reduction (1 full size, 4 quarter size) |

