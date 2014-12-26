#!/usr/bin/env python

"""Capers - play at draughts

This is just a small launcher, the classes themselves are imported
from the capers module.

"""

GLOBAL_SHARE_PATH='/opt/capers'

import pygtk
pygtk.require('2.0')
import gtk.glade

import sys
sys.path.insert(0, GLOBAL_SHARE_PATH)
sys.path.insert(0, 'share')
import capers

import profile
profile.run('capers.Main()')
#profile.run('capers.Main()', 'profile.out')
