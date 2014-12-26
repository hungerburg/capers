capers
======

Play checkers against the computer and study draughts games from books.

This contains the full source code to both the python GUI and the C engines.
Prebuilt binaries can be found at http://arton.cunst.net/capers/index.html.
To compile yourself, clone the repo and issue "make" from the project directory, then run "./capers".

Directory overview:
- ./ application starter, main Makefile, license, misc stuff
- cake/ the cake engine by Martin Fierz
- cliche/ a commandline host for cb-engines, two more engines by MF
- share/ pixmaps for the board, glade layout, engine runtime dir
- doc/ some documentation, not all
- games/ some example pdn game books
- debian/ for dpkg creation

Capers depends on python and gtk, and pygtk, which glues them together, version 2.4 of pygtk at least; also, it needs gnome canvas to display the board, and python-ctypes, to talk to the engines.
It should work on most linux distributions, provided the dependencies are met; It might also work on Windows, if you manage to collect all the above packages.

Happy hacking!
