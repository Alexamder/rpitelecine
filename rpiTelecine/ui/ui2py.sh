#!/bin/sh
# Compile UI files generated with Qt Designer to Python
pyside-uic telecineui.ui -o telecineui.py
pyside-uic livePreview.ui -o livePreview.py
pyside-uic setupJob.ui -o setupJob.py
