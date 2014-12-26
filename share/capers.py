# -*- Mode: Python -*-
# vi:si:et:tw=4

"""
Capers - play at draughts

capers provides a visual interface to socalled checkers engines,
that search a given board for the 'best' move.

several drag and drop and point and click controls allow
tuning the behaviour of the program - select game types,
browse played games, etc.

its really more an office application than a game. a game would
let the user enter a small cafe, and with the aid of a waiter,
sit down at some table, join a game, have a chat, get up, and
settle on another table, to play another opponent.

capers tries its best, to give you a pleasant time with Martin
Fierz' strong checkers engines. capers is free software: you are
invited to share and tinker. if in doubt, see accompanying file
COPYING for details on distribution and derivation.

(c) Peter Chiochetti, 2004, 2005


DISCLAIMER:

- a game, for which there is no engine, cannot be played, as capers
  does not know how to take pieces and crown kings.

- unlike earlier versions of capers, this one is made with a
  toolkit. the python bindings make working with gtk quite bearable.
  documentation is, except in parts, very clear and accurate.

- this follows the object oriented design. still, there are just
  procedures. they are organised in classes, to not have to come up
  with clever names for functions and globals, and to more easily
  build on the fine work others have done.

- no care has been taken to make the objects reusable outside of this
  context. they all depend one on the other; though most of the work
  gets done in the "game" class.


DEVEL:

- drive: all but one action are triggerd from the gui, only the engines
  moves are ticking in a gobject timeout loop.

- locking: the Main.game.lock is held, when an engine moves, and when a
  game is created, and while reading a pdn


TODO:

- have engine suggest user moves, possibly in statusline

- when a game is browsed, new moves can be made and will truncate
  the game: instead it was nice to start a variation

- have move_piece called from gobject idle too - about 4 of 5 seconds
  are spent there: the problem is, that when the idle hook returns,
  the canvas isnt done yet...

- intermediate hops mouse input (wait for python-gnomecanvas grab())

- lazy loading of engines, so application starts faster - seems
  no problem here, maybe will be with cake...

- network play: with central server, or p2p  or both?

"""


import os
import sys
import thread
import gobject
import gtk
import gnome.canvas
import math


# =======
# G A M E
# =======

class Position:
	"""known setup positions:
	international, english, (italian, russian,) mafierz

	in store: pseudo constants for the values of a square, a function
	to return a mutable deepcopy of a position, with references to
	pixmaps intact, and a function to print an ascii art board

	- a position is a list of squares: 64 or 100 are allowed
	- a square is a list of five values: num, col, x, y, pixbuf
	"""

	COL_NUM = 0
	COL_VAL = 1
	COL_X = 2
	COL_Y = 3
	COL_PIECE = 4 # pixbuf reference

	# square values
	EMPTY = 0
	WHITE = 1
	BLACK = 2
	CC = 3 # change color
	MAN = 4
	KING = 8
	FREE = 16

	# convenience
	def copy(self, position):
		"""return mutable deepcopy of position:
		simple types by value, objects by reference"""
		temp = []
		for i in xrange(len(position)):
			temp.append([0]*len(position[i]))
			for j in xrange(len(position[i])):
				temp[i][j] = position[i][j]
		return temp

	def ascii(self, position):
		"return ascii art string of <position>"
		i = 0
		r = "\n  "
		squares = "-    wb  WB      "
		if len(position) == 64: c = 8
		if len(position) == 100: c = 10
		assert c
		for s in position:
			i += 1
			r = r + squares[s[1]] + ' '
			if i % c == 0: r = r + "\n  "
		return r

	def fen_setup(self, position, fen):
		"change position to match fen setup, return turn, position"
		turn, bpos, wpos = fen
		fpos = {}
		for num, val in bpos.iteritems():
			fpos[num] = val
		for num, val in wpos.iteritems():
			fpos[num] = val
		for s in position:
			if not s[self.COL_NUM]:
				continue
			s[self.COL_VAL] = self.EMPTY
			try:
				newval = fpos[s[self.COL_NUM]]
				s[self.COL_VAL] = newval
			except KeyError:
				continue
		return turn, position

	# setup positions
	def international(self):
		"return international setup, color to move first"
		pos = []
		cells = 10
		count = 0
		for col in xrange(cells):
			for row in xrange(cells):
				if (row + col) % 2 == 1:
					if count < 39:
						pos.append((count / 2 + 1,
							self.WHITE|self.MAN,
							row, col, 0))
					elif count > 59:
						pos.append((count / 2 + 1,
							self.BLACK|self.MAN,
							row, col, 0))
					else:
						pos.append((count / 2 + 1,
							self.EMPTY,
							row, col, 0))
				else:
					pos.append((0, self.FREE,
						row, col, 0))
				count += 1
		return (self.WHITE, self.copy(pos))

	def english(self):
		"return english setup, color to move first"
		pos = []
		cells = 8
		count = 0
		for col in xrange(cells):
			for row in xrange(cells):
				if (row + col) % 2 == 1:
					if count < 24:
						pos.append((count / 2 + 1,
							self.BLACK|self.MAN,
							cells - row - 1,
							cells - col - 1, 0))
					elif count > 39:
						pos.append((count / 2 + 1,
							self.WHITE|self.MAN,
							cells - row - 1,
							cells - col - 1, 0))
					else:
						pos.append((count / 2 + 1,
							self.EMPTY,
							cells - row - 1,
							cells - col - 1, 0))
				else:
					pos.append((0, self.FREE,
						cells - row - 1,
						cells - col - 1, 0))
				count += 1
		return (self.BLACK, self.copy(pos))

	def italian(self):
		"return italian setup, color to move first"
		Fatal('Italian setup not implemented')

	def russian(self):
		"return russian setup, color to move first"
		Fatal('Russian setup not implemented')

	def mafierz(self):
		"""return mafierz setup (italian rules on russian board),
		color to move first"""
		pos = []
		cells = 8
		count = 0
		for col in xrange(cells):
			for row in xrange(cells):
				if (row + col) % 2 == 0:
					if count < 24:
						pos.append((count / 2 + 1,
							self.BLACK|self.MAN,
							cells - row - 1,
							col, 0))
					elif count > 40:
						pos.append((count / 2 + 1,
							self.WHITE|self.MAN,
							cells - row - 1,
							col, 0))
					else:
						pos.append((count / 2 + 1,
							self.EMPTY,
							cells - row - 1,
							col, 0))
				else:
					pos.append((0, self.FREE,
						cells - row - 1,
						col, 0))
				count += 1
		return (self.WHITE, self.copy(pos))

class Game:
	"""glue together gui, engine, board and book

	the game does know very little about the rules, it has to ask the
	engine, if a move was legal, the game only knows the current position,
	it has to ask the book for others

	on entry of a move, board and book will be updated, current game,
	current and last move are tracked here too, its easier than always
	having to ask the book

	on selecting an old game, a new setup position is created and the game
	rewound, in order to update all the pixbuf references to valid ones;
	a game loaded from pdn is just like a game from the treestore

	all communication with board and book shall be through the game
	the game also keeps the lock, while an engine is searching a move

	_grey is the engine used to validate moves by human players;
	_black and _white are either references to engines, or None

	_game_curr, _game_last, _move_curr and _move_last are paths into
	the Book treestore
	"""

	# gametypes
	INTERNL = 20
	ENGLISH = 21
	ITALIAN = 22
	RUSSIAN = 25
	MAFIERZ = 32

	gametype = 0
	_color = 0 # color to move
	_game_curr = _game_last = _move_curr = _move_last = -1
	_position = []
	_black = _white = _grey = False
	engines_loop = 0

	def __init__(self):
		self.lock = thread.allocate_lock()

	# setup
	def new(self):
		"setup from prefs, register with board and book, kickoff engines"
		assert not self.lock.locked()
		self.lock.acquire()
		self.gametype = Main.prefs.getint('game', 'type')
		self._timeout = Main.prefs.getint('game', 'timeout')

		# connect engines
		self._grey = Main.players.gt2engine(self.gametype)
		if not self._grey:
			Fatal('Unsupported gametype: ' + self.gametype)
		black = Main.prefs.get('game', 'black')
		white = Main.prefs.get('game', 'white')
		self._black = Main.players.file2engine(black)
		self._white = Main.players.file2engine(white)
		blackname = whitename = Main.prefs.get('player', 'name')
		if isinstance(self._black, Engine):
			blackname = self._black.name
		if isinstance(self._white, Engine):
			whitename = self._white.name

		# setup position
		flip = False
		if self.gametype == self.INTERNL:
			self._first, self._position = Main.pos.international()
		elif self.gametype == self.ENGLISH:
			self._first, self._position = Main.pos.english()
		elif self.gametype == self.MAFIERZ:
			self._first, self._position = Main.pos.mafierz()
		# flip board, so single human sees it right
		if self._first == Position.WHITE \
			and self._white and not self._black:
			flip = True
		elif self._first == Position.BLACK \
			and self._black and not self._white:
			flip = True
		Main.board.new(self.gametype, self._position, flip)
		self._color = self._first

		# setup book
		name = False
		self._game_curr, = Main.book.new_game(name, self.gametype,
			blackname, whitename, self._position, self._color)
		self._game_last = self._game_curr
		self._move_curr = -1
		self._move_last = self._move_curr

		# go
		self.engines_go()
		self.lock.release()
		if self._color == Position.WHITE:
			Main.feedback.g_push('New game: White to move')
		else:
			Main.feedback.g_push('New game: Black to move')

	def old(self, game):
		"setup from old game <game>, register with prefs, board and book"
		assert not self.lock.locked()
		self.lock.acquire()
		self._game_curr = game

		# setup position
		header = Main.book.goto_game(self._game_curr)
		self.gametype, black, white = \
			header['gametype'], header['black'], header['white']
		if self.gametype == self.INTERNL:
			self._first, self._position = Main.pos.international()
		if self.gametype == self.ENGLISH:
			self._first, self._position = Main.pos.english()
		if self.gametype == self.MAFIERZ:
			self._first, self._position = Main.pos.mafierz()
		# fen setup
		fen = header['fen']
		if fen:
			self._first, self._position \
				= Main.pos.fen_setup(self._position, fen)
		self._color = self._first
		Main.book[self._game_curr][Book.COL_TURN] = self._first

		# set prefs
		Main.prefs.set('game', 'type', self.gametype)
		Main.prefs.set('game', 'black', Main.players.name2file(black))
		Main.prefs.set('game', 'white', Main.players.name2file(white))
		Main.prefs.save()

		# connect engines
		self._grey = Main.players.gt2engine(self.gametype)
		self._black = Main.players.name2engine(black)
		self._white = Main.players.name2engine(white)

		# replay game
		self._move_curr = -1
		self._move_last = self._move_curr
		# flip board, so single human sees it right
		flip = False
		if self._first == Position.WHITE \
			and self._white and not self._black:
			flip = True
		elif self._first == Position.BLACK \
			and self._black and not self._white:
			flip = True
		Main.board.new(self.gametype, self._position, flip)
		movelist = Main.book.old_game(self._position)
		for move in movelist:
			data = self._grey.islegal(move,
				self._color, self._position, None)
			self.do_oldmove(move, data)
		self.lock.release()
		self.goto_begin()

	def pdn(self, last):
		"go to the first game in the book, that has num <last> games"
		assert not self.lock.locked()
		self._timeout = Main.prefs.getint('game', 'timeout')
		self._game_last = last
		self.old(0)

	# editor
	def start_edit(self, empty=False):
		"start new game from current setup or empty board, lock game"
		assert not self.lock.locked()
		self.lock.acquire()
		# setup book
		blackname = whitename = Main.prefs.get('player', 'name')
		if isinstance(self._black, Engine):
			blackname = self._black.name
		if isinstance(self._white, Engine):
			whitename = self._white.name
		name = False
		self._game_curr, = Main.book.new_game(name, self.gametype,
			blackname, whitename, self._position, self._color)
		# setup board
		if empty:
			self.empty()
		else:
			self.clean()
		self._game_last = self._game_curr
		self._move_curr = -1
		self._move_last = self._move_curr
		Main.feedback.g_push('Edit board: click square to set piece')

	def stop_edit(self):
		"create fen of current position, correct book, release game lock"
		bpos = {}
		wpos = {}
		for s in self._position:
			num = s[Position.COL_NUM]
			val = s[Position.COL_VAL]
			if val & Position.BLACK:
				bpos[num] = val
			if val & Position.WHITE:
				wpos[num] = val
		Main.book[self._game_curr][Book.COL_HEAD]['fen'] = \
			self._color, bpos, wpos
		Main.book[self._game_curr][Book.COL_POS] = self._position
		Main.feedback.g_push('Setup registered')
		if self._color == Position.WHITE:
			Main.feedback.g_push('Position set: White to move')
		else:
			Main.feedback.g_push('Position set: Black to move')
		self.lock.release()

	# transport
	def goto_move(self, move):
		"go to move/position <move> in current game"
		if self.lock.locked():
			return
		move = min(self._move_last, move)
		move = max(move, -1)
		if move == self._move_curr:
			return
		self.engines_stop()
		self._move_curr = move
		self._position, self._color = \
			Main.book.get_move(self._move_curr)
		Main.board.setposition(self._position)
		if self._color == Position.WHITE:
			Main.feedback.g_push('Position '
				+ str(move + 1) + ': White to move')
		else:
			Main.feedback.g_push('Position '
				+ str(move + 1) + ': Black to move')

	def goto_begin(self):
		"go to the begin of the game"
		self.goto_move(-1)

	def goto_prev(self):
		"go to the previous position in the game"
		self.goto_move(self._move_curr - 1)

	def goto_next(self):
		"go to the next position in the game"
		self.goto_move(self._move_curr + 1)

	def goto_end(self):
		"go to the last position in the game"
		self.goto_move(self._move_last)

	def goto_game(self, game):
		"go to move/position <game> in current game"
		if self.lock.locked():
			return
		game = min(self._game_last, game)
		game = max(game, 0)
		if game == self._game_curr:
			return
		self.engines_stop()
		self.old(game)

	def goto_game_prev(self):
		"go to the previous game"
		self.goto_game(self._game_curr - 1)

	def goto_game_next(self):
		"go to the next game"
		self.goto_game(self._game_curr + 1)

	def goto_game_move(self, path):
		"""go to move/position <path> in game <path>
		when game changed, only go to begin"""
		if len(path) == 2:
			game, move = path
		else:
			game, = path
			move = -1
		if game != self._game_curr:
			self.goto_game(game)
		elif move != self._move_curr:
			self.goto_move(move)

	# convenience
	def num2val(self, num):
		"return value of square <num>"
		for s in self._position:
			if s[Position.COL_NUM] == num:
				return s[Position.COL_VAL]
		assert "number off board"

	def num2piece(self, num):
		"return piece on square <num>"
		for s in self._position:
			if s[Position.COL_NUM] == num:
				return s[Position.COL_PIECE]
		assert "number off board"

	def num2coor(self, num):
		"translate number to coordinates"
		for s in self._position:
			if s[Position.COL_NUM] == num:
				return (s[Position.COL_X], s[Position.COL_Y])
		assert "number off board"

	def coor2num(self, x, y):
		"translate coordinates to number"
		for s in self._position:
			if s[Position.COL_X] == x  \
				and s[Position.COL_Y] == y:
				return s[Position.COL_NUM]
		assert "coordinates off board"

	# calls to engine
	def engines_stop(self):
		"make engine_getmove always return False"
		if self.engines_loop:
			gobject.source_remove(self.engines_loop)
			self.engines_loop = 0
			Main.feedback.g_push('Engines stop')

	def engines_go(self):
		"let engine_getmove return True"
		if self.engines_loop:
			return
		self.engines_loop = \
			gobject.timeout_add(self._timeout, self.engine_getmove)
		Main.feedback.g_push('Engines go')

	def engine_getmove(self):
		"""ask the engine for a move, called from gobject timeout, so its
		in a loop, where False means break, and True means continue, but
		this will never break what is not broken, only engines_stop does"""
		if not self.engines_loop:
			return False
		if self.lock.locked():
			return True
		if Main.board.busy:
			return True
		if self._color == Position.WHITE \
			and not isinstance(self._white, Engine):
			return True
		if self._color == Position.BLACK \
			and not isinstance(self._black, Engine):
			return True

		maxtime = Main.prefs.getint('engines', 'maxtime')
		data = [self._color, maxtime, self._position]
		if self._color == Position.WHITE:
			self._white.getmove(data)
			return True
		if self._color == Position.BLACK:
			self._black.getmove(data)
			return True
		assert 0

	def engine_islegal(self, list):
		"if game not locked, target is empty and color right, ask engine"
		if self.lock.locked():
			return [False]
		if not list[-1]:
			return [False]
		if self.num2val(list[-1]) ^ Position.EMPTY:
			return [False]
		if self.num2val(list[0]) & self._color:
			return self._grey.islegal(list,
				self._color, self._position, None)
		return [False]

	# book management
	def save_move(self, steps, jumps):
		"register move with book"
		if self._move_curr < self._move_last:
			Main.book.trunc_game(self._move_curr)
		# name = move as string
		if jumps:
			name = 'x'.join([`num` for num in steps])
		else:
			name = '-'.join([`num` for num in steps])
		self._game_curr, self._move_curr = Main.book.new_move(name,
			self._position, self._color, steps)
		self._move_last = self._move_curr

	def save_oldmove(self, steps, jumps):
		"reregister move with book, increments move_curr"
		if jumps:
			name = 'x'.join([`num` for num in steps])
		else:
			name = '-'.join([`num` for num in steps])
		self._game_curr, self._move_curr = Main.book.old_move(
			self._move_curr, name, self._position, self._color, steps)
		self._move_last = self._move_curr

	def set_result(self, code, move):
		"game ended, push message and format result for board/pdn"
		self.engines_stop()
		message = 'Game ends with unknown result'
		if code == Engine.DRAW:
			message = "Game ends in a draw (%s)" % move
			Main.book.set_result('1/2 1/2')
		if code == Engine.WIN:
			if self._color == Position.BLACK:
				message = "Black wins (%s)" % move
			if self._color == Position.WHITE:
				message = "White wins (%s)" % move
		if code == Engine.LOSS:
			if self._color == Position.BLACK:
				message = "Black looses (%s)" % move
			if self._color == Position.WHITE:
				message = "White looses (%s)" % move
		if self._first == self._color:
			if code == Engine.WIN:
				Main.book.set_result('1-0')
			if code == Engine.LOSS:
				Main.book.set_result('0-1')
		if self._first != self._color:
			if code == Engine.WIN:
				Main.book.set_result('0-1')
			if code == Engine.LOSS:
				Main.book.set_result('1-0')
		# wait after engines status pushed
		gobject.timeout_add(self._timeout, Main.feedback.g_push, message)

	# board management
	def empty(self):
		"clear board of all pieces, needed for edit empty"
		for s in self._position:
			s[Position.COL_VAL] = Position.EMPTY
			p = s[Position.COL_PIECE]
			if p:
				p.destroy()
			s[Position.COL_PIECE] = 0

	def clean(self):
		"clear board of all hidden pieces, needed for edit"
		for s in self._position:
			p = s[Position.COL_PIECE]
			v = s[Position.COL_VAL]
			if p and not v:
				p.destroy()
				s[Position.COL_PIECE] = 0

	def do_move_silent(self, a, b):
		"update temp position after move, reducable"
		if a == b: return b
		n = m = -1 # from, to
		# find squares a, b
		for s in self._position:
			if s[Position.COL_NUM] == a:
				n = self._position.index(s)
			elif s[Position.COL_NUM] == b:
				m = self._position.index(s)
		assert n >= 0 and m >=0
		# swap values 1, 4
		self._position[m][Position.COL_VAL], \
			self._position[n][Position.COL_VAL] \
			= self._position[n][Position.COL_VAL], \
				self._position[m][Position.COL_VAL]
		self._position[m][Position.COL_PIECE], \
			self._position[n][Position.COL_PIECE] \
			= self._position[n][Position.COL_PIECE], \
				self._position[m][Position.COL_PIECE]
		return b

	def do_move(self, a, b):
		"update temp position and board after move, reducable"
		Main.board.move_piece(a, b)
		return self.do_move_silent(a, b)

	def take_piece(self, num):
		"take piece on squares num in list, called via map()"
		for s in self._position:
			if s[Position.COL_NUM] != num: continue
			assert s[Position.COL_PIECE]
			s[Position.COL_VAL] = Position.EMPTY
			Main.board.take_piece(num)
			break

	def take_piece_silent(self, num):
		"take piece on squares num in list, called via map()"
		for s in self._position:
			if s[Position.COL_NUM] != num: continue
			assert s[Position.COL_PIECE]
			s[Position.COL_VAL] = Position.EMPTY
			break

	def promote(self, num, value, silent=False):
		"update temp position with piece value"
		for s in self._position:
			if s[Position.COL_NUM] != num: continue
			if not Main.board.edit:
				assert s[Position.COL_PIECE]
			s[Position.COL_VAL] = value
			if not silent:
				s[Position.COL_PIECE] = Main.board.set_piece(num, value)
			break

	def do_enginemove(self, data):
		"""register legal engine move with current position, release game lock
		always return False to remove gobject idle"""
		code, steps, new, old, huffs, lock = data
		if code != Engine.UNKNOWN:
			if len(huffs):
				move = 'x'.join([`num` for num in steps])
			else:
				move = '-'.join([`num` for num in steps])
			self.set_result(code, move)
			lock.release()
			# dont use this move
			return False
		self._position = Main.pos.copy(self._position)
		reduce(self.do_move, steps)
		map(self.take_piece, huffs)
		if new != old:
			self.promote(steps[-1], new)
		self._color ^= Position.CC
		self.save_move(steps, len(huffs))
		lock.release()
		if self._color == Position.WHITE:
			Main.feedback.g_push('White to move')
		else:
			Main.feedback.g_push('Black to move')
		return False

	def do_usermove(self, steps, data):
		"register legal user move with current position, called from board"
		assert data[0] # must be legal
		code, steps, new, old, huffs = data
		self._position = Main.pos.copy(self._position)
		reduce(self.do_move_silent, steps)
		map(self.take_piece, huffs)
		if new != old:
			self.promote(steps[-1], new)
		self._color ^= Position.CC
		self.save_move(steps, len(huffs))
		if self._color == Position.WHITE:
			Main.feedback.g_push('White to move')
		else:
			Main.feedback.g_push('Black to move')
		self.engines_go()

	def do_oldmove(self, steps, data):
		"register legal old move with current position, called from replay"
		if not data[0]: # must be legal
			self.save_oldmove((0, 0), 0)
			return
		code, steps, new, old, huffs = data
		self._position = Main.pos.copy(self._position)
		reduce(self.do_move_silent, steps)
		map(self.take_piece_silent, huffs)
		# make kings
		if new != old:
			self.promote(steps[-1], new, True)
		self._color ^= Position.CC
		self.save_oldmove(steps, len(huffs))


# =======
# B O O K
# =======

import datetime

class Book(gtk.TreeStore):
	"""game history - a tree of all the games in the book

	- games grow from the root
	  games store a name, the setup position, etc.
	- moves grow from a game
	  moves contain the move as a string and as a list and
	  the position after the move

	the currently active game is to be remembered between calls to
	several methods, so persistant iters are required

	output game headers are: gametype, black, white, result, date,
	site, round, fen. other headers are not in the output pdn
	the "event" header is in COL_NAME
	"""

	# general
	COL_NAME = 0 # pdn event or move as string
	COL_HEAD = 1 # game headers
	# move
	COL_MOVE = 2 # move as a list
	COL_STREN = 3
	COL_ANNO = 4
	COL_POS = 5
	COL_TURN = 6 # who's next
	
	def __init__(self):
		super(Book, self).__init__(
			str, gobject.TYPE_PYOBJECT,
			gobject.TYPE_PYOBJECT, str, str, gobject.TYPE_PYOBJECT, int,
			int, str, str, str, gobject.TYPE_PYOBJECT,
			gobject.TYPE_PYOBJECT)
		assert self.get_flags() & gtk.TREE_MODEL_ITERS_PERSIST

	def do_clear(self):
		"clear book"
		if hasattr(self, 'game'):
			del self.game
		self.clear()

	def new_game(self, name, gametype, black, white, position, color):
		"add a new game to the book, return path"
		today = datetime.date.today()
		# only if there are moves in the current game
		if not hasattr(self, 'game') or self.iter_n_children(self.game) > 0:
				self.game = self.append(None)
		path = self.get_path(self.game)
		name = "Game " + str(path[0] + 1)
		self.set(self.game, self.COL_NAME, name, self.COL_POS, position,
			self.COL_TURN, color, self.COL_ANNO, '',
			self.COL_HEAD, {'gametype': gametype,
			'black': black, 'white': white, 'result': '*',
			'date': str(today), 'site': '', 'round': '', 'fen': ''})
		Main.bookview.set_cursor(path)
		Main.bookview.scroll_to_cell(path, None, True)
		return path

	def pdn_game(self):
		"add a new empty game to the book"
		self.game = self.append(None)
		self.set(self.game, self.COL_NAME, 'Pdn', self.COL_ANNO, '',
			self.COL_HEAD, {'gametype': Game.ENGLISH,
			'black': 'Black', 'white': 'White', 'result': '*',
			'date': '', 'site': '', 'round': '', 'fen': ''})

	def goto_game(self, num):
		"set game <num> as current, return game header"
		iter = self.iter_nth_child(None, num)
		assert iter
		self.game = iter
		path = self.get_path(self.game)
		Main.bookview.set_cursor(path)
		Main.bookview.scroll_to_cell(path, None, True)
		return (self.get_value(iter, self.COL_HEAD))

	def old_game(self, position):
		"replace position in current old game, return old games' movelist"
		movelist = self.get_movelist()
		self.set_value(self.game, self.COL_POS, position)
		return movelist

	def trunc_game(self, num):
		"delete all moves after <num> from current game"
		assert self.game
		self.get_value(self.game, self.COL_HEAD)['result'] = '*'
		iter = self.iter_nth_child(self.game, num + 1)
		while self.remove(iter): assert iter

	def new_move(self, name, position, color, move):
		"append move to current game, return path"
		assert self.game
		iter = self.append(self.game)
		self.set(iter, self.COL_NAME, name, self.COL_POS, position,
			self.COL_TURN, color, self.COL_MOVE, move, self.COL_ANNO, '')
		path = self.get_path(iter)
		Main.bookview.expand_to_path(path)
		Main.bookview.set_cursor(path)
		Main.bookview.scroll_to_cell(path)
		return path

	def pdn_move(self, name, strength, annotation, move):
		"""append move from pdn to current game, some essential
		parameters are only added later on replay, ie. old_move"""
		assert self.game
		iter = self.append(self.game)
		self.set(iter, self.COL_NAME, name, self.COL_STREN, strength,
			self.COL_ANNO, annotation, self.COL_MOVE, move)

	def old_move(self, num, name, position, color, move):
		"replace position in move <num> in current game, return path"
		assert self.game
		iter = self.iter_nth_child(self.game, num + 1)
		assert iter
		self.set(iter, self.COL_NAME, name, self.COL_POS, position,
			self.COL_TURN, color, self.COL_MOVE, move)
		path = self.get_path(iter)
		return path

	def get_move(self, num):
		"get move <num>, return saved position and turn"
		assert self.game
		if num < 0:
			iter = self.game
		else:
			iter = self.iter_nth_child(self.game, num)
		path = self.get_path(iter)
		Main.bookview.expand_to_path(path)
		Main.bookview.set_cursor(path)
		#Main.bookview.scroll_to_cell(path)
		return (self.get_value(iter, self.COL_POS),
			self.get_value(iter, self.COL_TURN))

	def get_movelist(self):
		"return list of the moves in the current game"
		move = self.iter_children(self.game)
		movelist = []
		while move:
			movelist.append(self.get_value(move, self.COL_MOVE))
			move = self.iter_next(move)
		return movelist

	def set_result(self, result):
		"replace result in current game"
		self.get_value(self.game, self.COL_HEAD).update({'result' : result})

	def fen2str(self, fen):
		"return fen as a string"
		color, bpos, wpos = fen
		if color == Position.BLACK:
			fstr = 'B:B'
		else:
			fstr = 'W:B'
		black = []
		for num, val in bpos.iteritems():
			if val & Position.KING:
				black.append('K%d' % num)
			else:
				black.append(str(num))
		fstr = fstr + ','.join(black)
		fstr = fstr + ':W'
		white = []
		for num, val in wpos.iteritems():
			if val & Position.KING:
				white.append('K%d' % num)
			else:
				white.append(str(num))
		fstr = fstr + ','.join(white)
		return fstr

	def wrap(self, text, width):
		"""
		A word-wrap function that preserves existing line breaks
		and most spaces in the text. Expects that existing line
		breaks are posix newlines (\n).
		http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/148061
		"""
		return reduce(lambda line, word, width=width: '%s%s%s' %
			(line,
				' \n'[(len(line)-line.rfind('\n')-1
				+ len(word.split('\n',1)[0]
					) >= width)],
				word),
				text.split(' ')
			)

	def game2pdn(self):
		"return current game as a pdn string, wrapped email friendly"
		game = self.get_value(self.game, self.COL_NAME)
		header = self.get_value(self.game, self.COL_HEAD)
		gametype, black, white, date, site, round, result, fen = \
			header['gametype'], header['black'], header['white'], \
			header['date'], header['site'], header['round'], \
			header['result'], header['fen']

		pdn = """[Event "%s"]\n""" % game
		if date:
			pdn = pdn + """[Date "%s"]\n""" % date
		if black != 'Black':
			pdn = pdn + """[Black "%s"]\n""" % black
		if white != 'White':
			pdn = pdn + """[White "%s"]\n""" % white
		if site:
			pdn = pdn + """[Site "%s"]\n""" % site
		if round:
			pdn = pdn + """[Round "%s"]\n""" % round
		if gametype != Game.ENGLISH:
			pdn = pdn + """[Gametype "%s"]\n""" % gametype
		pdn = pdn + """[Result "%s"]\n""" % result
		if fen:
			fstr = self.fen2str(fen)
			pdn = pdn + """[FEN "%s"]\n""" % fstr
		anno = self.get_value(self.game, self.COL_ANNO)
		if anno:
			pdn = pdn + """{%s}\n""" % self.wrap(anno, 72)

		move = self.iter_children(self.game)
		movelist = []
		count = 2
		while move:
			if count % 2 == 0:
				movelist.append(str(count / 2) + '.')
			count += 1
			name = self.get_value(move, self.COL_NAME)
			stren = self.get_value(move, self.COL_STREN)
			anno = self.get_value(move, self.COL_ANNO)
			if stren:
				name = name + stren
			if anno:
				name = name + ' {' + anno + '}'
			movelist.append(name)
			move = self.iter_next(move)
		movelist = ' '.join(movelist)
		pdn = pdn + self.wrap(movelist, 72)
		pdn = pdn + ' %s\n' % (result)
		return game, pdn

import shlex

class Pdn(shlex.shlex):
	"""load games from pdn file

	as the parser is quite small, its put here too. the globals game and
	move are counts that match paths into the books treestore. 

	this gets a filename, parses the games in the file and writes them to
	the book, then points the game at the first loaded game; moves are not
	checked for validity here
	"""

	def __init__(self, stream, filename):
		"init lexer in posix mode, prepare parser"
		# not a new style class
		#super(Pdn, self).__init__()
		shlex.shlex.__init__(self, stream, filename, True)
		self.wordchars = self.wordchars + """.-/'<>*!?"""
		self.quotes = '"'
		self.pdn_state = 'none'
		self.pdn_trace = False
		self.game = -1
		self.move = -1
		self.name = filename

	def parse_fen(self, fen):
		"parse fen string: setup position, return turn, bpos, wpos"
		def num_val(square, color):
			"return number and value of square"
			if square.isdigit():
				return [int(square), color|Position.MAN]
			if square[0].lower() == 'k':
				return [int(square[1:]), color|Position.KING]
			print self.error_leader(), 'invalid square in fen: "%s"' %square
			return (0, 0)
		turn, pos1, pos2 = fen.split(':')
		if turn.lower() == 'b':
			turn = Position.BLACK
		else:
			turn = Position.WHITE
		if pos1[0].lower() == 'b':
			black = pos1[1:].split(',')
			white = pos2[1:].split(',')
		else:
			black = pos2[1:].split(',')
			white = pos1[1:].split(',')
		try:
			black = dict([num_val(x, Position.BLACK) for x in black])
			white = dict([num_val(x, Position.WHITE) for x in white])
		except ValueError:
			print self.error_leader(), 'invalid fen: "%s"' %fen
			return [0, 0, 0]
		return turn, black, white

	def parse_header(self):
		"parse headers: key, value; save to book, increment game counter"
		if not self.pdn_state == 'headers':
			# got new game
			self.pdn_state = 'headers'
			self.game += 1
			self.move = -1
			# create empty game in book
			Main.book.pdn_game()
			Main.feedback.g_push('Loading game: %3i' % self.game)
			# parsing may take some time
			while gtk.events_pending():
				gtk.main_iteration(False)
		key = self.get_token()
		value = self.get_token()
		header = Main.book[self.game][Book.COL_HEAD]
		if self.pdn_trace:
			print """H:%s,:	[%s "%s"]""" % (self.game, key, value)
		if key.lower() == 'event':
			Main.book[self.game][Book.COL_NAME] = value
		elif key.lower() == 'gametype':
			Main.book[self.game][Book.COL_HEAD]['gametype'] = int(value)
		elif key.lower() == 'fen':
			Main.book[self.game][Book.COL_HEAD]['fen'] = self.parse_fen(value)
		else:
			Main.book[self.game][Book.COL_HEAD][key.lower()] = value
		# discard rest of line
		for token in iter(self.get_token, None):
			if token == ']':
				return
			print self.error_leader(), 'stray text in header: "%s"' %token

	def parse_annotation(self):
		"parse annotation, return it"
		annotation = self.get_token()
		# drop empty annotations
		if annotation == '}': return ''
		for token in iter(self.get_token, None):
			if token == '}':
				if self.pdn_trace:
					print "A:%s,%s:	{%s}" % (self.game, self.move, annotation)
				return annotation
			annotation = ' '.join((annotation, token))

	def move_split(self, move):
		"split a move, return list of integers"
		if move.count('-'):
			steps = move.split('-')
			try:
				return [int(x) for x in steps] 
			except ValueError:
				print self.error_leader(), 'stray text in movelist: "%s"' %move
				return [0, 0]
		elif move.count('x'):
			steps = move.split('x')
			try:
				return [int(x) for x in steps] 
			except ValueError:
				print self.error_leader(), 'stray text in movelist: "%s"' %move
				return [0, 0]
		else:
			return [False]

	def parse_move(self):
		"parse single move: hops, strength, annotation; return them"
		steps = []
		move = strength = annotation = ''
		for token in iter(self.get_token, None):
			# move
			if not steps and token[0] in '1234567890':
				# strength
				if token[-1] in '*!?':
					strength = token[-1]
					steps = self.move_split(token[:-1])
				else:
					steps = self.move_split(token)
				# eat move numbers
				if len(steps) < 2:
					steps = []
					move = strength = annotation = ''
					continue
				self.move += 1
				move = token
				continue
			#annotation
			if token == '{':
				annotation = self.parse_annotation()
				continue
			# push back the rest
			self.push_token(token)
			break
		if self.pdn_trace:
			print "M:%s,%s:	%s" %(self.game, self.move, steps)
		return (move, steps, strength, annotation)

	def parse_moves(self):
		"parse movelist: moves, result; save them to book"
		def set_result(result):
			"set result in book"
			if self.game < 0: return
			Main.book[self.game][Book.COL_HEAD]['result'] = result
			self.pdn_state = 'none'
		result = ''
		for token in iter(self.get_token, None):
			# result: unknown
			if token ==  '*':
				self.pdn_state = 'none'
				continue
			# result: first wins
			elif token ==  '1-0':
				set_result(token)
				continue
			# result: second wins
			elif token ==  '0-1':
				set_result(token)
				continue
			# result: draw
			elif token ==  '1/2-1/2':
				set_result(token)
				continue
			# shift move
			elif token[0] in '1234567890':
				if self.game < 0:
					continue
				self.push_token(token)
				data = self.parse_move()
				move, steps, strength, annotation = data
				if move and len(steps) > 1:
					Main.book.pdn_move(move, strength, annotation, steps)
				continue
			if token == '[':
				self.push_token(token)
				break
			# warn about others
			print self.error_leader(), 'stray text in movelist: "%s"' %token
			break

	def parse(self):
		"parse book: headers, annotation, movelist; hold game.lock"
		Main.game.lock.acquire()
		Main.book.do_clear()
		Main.bookview.connect_model(False)
		for token in iter(self.get_token, None):
			# header
			if token == '[':
				self.parse_header()
				continue
			# annotation
			elif token == '{':
				if self.game < 0: continue
				annotation = self.parse_annotation()
				Main.book[self.game][Book.COL_ANNO] = annotation
				continue
			# shift movelist
			elif token[0] in '1234567890*':
				if not self.pdn_state == 'moves':
					self.pdn_state = 'moves'
				self.push_token(token)
				self.parse_moves()
				continue
			# warn about others
			print self.error_leader(), 'stray text: "%s"' %token
		Main.bookview.connect_model(True)
		Main.game.lock.release()
		Main.feedback.g_push('read %d games from %s'
			%(self.game + 1, self.name))
		if self.game < 0:
			Main.game.new()
			Main.feedback.g_push('No games found')
			return False
		Main.game.pdn(self.game)
		return True

import pango

class CellRendererWrap(gtk.GenericCellRenderer):
	"""a cell renderer, that wraps long text

	the first on_get_size will not be given a cell_area, probably,
	because the treeview widget is not yet realized. as no width can
	be set for the wordwrap, pango will not wrap at all and the cell
	will be as wide as the longest single line in the model.

	one way around this is to set an initial width. this has a severe
	drawback: a cell will never shrink below its initial width and its
	initial height will neither shrink nor grow. so if the set width is
	smaller than the actual width, when the cell is realized, there will
	be a blank padding on the bottom. if the set width is larger than
	the actual width, some of the text will be cut off.

	another way might be to pack the cell into the column after view and
	column have been realized. still, the first calls will not sport a
	cell_area.

	this always sets the marked up text
	"""
	__gproperties__ = {
		'text': (gobject.TYPE_STRING, 'markup', 'markup displayed by the cell',
					 '', gobject.PARAM_READWRITE),
		'markup': (gobject.TYPE_STRING, 'markup', 'markup displayed by the cell',
					 '', gobject.PARAM_READWRITE),
	}

	def __init__(self):
		gobject.GObject.__init__(self)
		#self.set_property('mode', gtk.CELL_RENDERER_MODE_EDITABLE)
		self.set_property('xalign', 0.0)
		self.set_property('yalign', 0.5)
		self.set_property('xpad', 2)
		self.set_property('ypad', 2)
		self.markup = self.text = ''

	def do_get_property(self, property):
		if property.name == 'text' or property.name == 'markup':
			return self.markup
		else:
			raise TypeError('No property named %s' % (property.name,))

	def do_set_property(self, property, value):
		if property.name == 'text' or property.name == 'markup':
			self.markup = value
		else:
			raise TypeError('No property named %s' % (property.name,))
		
	def _render(self, widget, cell_area, xpad):
		"call pango to render the text"
		layout = widget.create_pango_layout(self.text)
		layout.set_markup(self.markup)
		layout.set_wrap(pango.WRAP_WORD)

		if cell_area:
			width = cell_area.width
		else:
			width = self.get_property('width')
		width -= 2 * xpad

		layout.set_width(width * pango.SCALE)
		return layout

	def _get_size(self, widget, cell_area, layout=False):
		"only call to pango, if there is no layout"
		xpad = self.get_property('xpad')
		ypad = self.get_property('ypad')
		xalign = self.get_property('xalign')
		yalign = self.get_property('yalign')

		if not layout:
			layout = self._render(widget, cell_area, xpad)
		width, height = layout.get_pixel_size()
		calc_width = 2 * xpad + width
		calc_height = 2 * ypad + height

		if cell_area:
			x_offset = xalign * (cell_area.width - calc_width)
			x_offset = max(x_offset, 0)
			y_offset = yalign * (cell_area.height - calc_height)
			y_offset = max(y_offset, 0)		   
		else:
			x_offset = 0
			y_offset = 0
		return int(x_offset), int(y_offset), calc_width, calc_height

	def on_get_size(self, widget, cell_area):
		"tell the treeview the cell's size"
		return self._get_size(widget, cell_area)

	def on_render(self, window, widget, background_area,
		cell_area, expose_area, flags):
		"paint the cell"
		xpad = self.get_property('xpad')
		ypad = self.get_property('ypad')

		layout = self._render(widget, cell_area, xpad)
		x_offset, y_offset, width, height = self._get_size(widget, cell_area, layout)
		width -= 2*xpad
		height -= 2*ypad
		widget.style.paint_layout(window,
			gtk.STATE_NORMAL, True,
			cell_area, widget, "text",
			cell_area.x + x_offset + xpad,
			cell_area.y + y_offset + ypad,
			layout)
gobject.type_register(CellRendererWrap) # make widget available to bookview

class BookView(gtk.TreeView):
	"""display of book: games and moves

	the book view displays data from several columns of the book model
	in a single column, collection is done via a celldata function
	to speed up loading of games, the model is disconnected then

	it might have been preferable to show the black and white move on
	the same line, but that seems quite hard and doesnt mix well with
	annotations
	"""

	_book = None # for disconnect/reconnect

	def __init__(self):
		"never called, libglade doesnt"
		gobject.GObject.__init__(self)
		#assert 0 # obviously, now its called

	def edit_game(self, model, path):
		"edit game headers and dialog"
		game = model.get_iter(path)
		event, header, annotation = model.get(game,
			Book.COL_NAME, Book.COL_HEAD, Book.COL_ANNO)
		editor = Main.gui['Edit game...']
		ege = Main.gui['EG event']
		egd = Main.gui['EG date']
		egb = Main.gui['EG black']
		egw = Main.gui['EG white']
		egs = Main.gui['EG site']
		egn = Main.gui['EG round']
		egr = Main.gui['EG result']
		ega = Main.gui['EG annotation'].get_buffer()
		ege.set_text(event)
		egd.set_text(header['date'])
		egb.set_text(header['black'])
		egw.set_text(header['white'])
		egs.set_text(header['site'])
		egn.set_text(header['round'])
		egr.set_text(header['result'])
		ega.set_text(annotation)
		if editor.run() == gtk.RESPONSE_OK:
			model.set(game,
				Book.COL_NAME, ege.get_text(),
				Book.COL_ANNO, ega.get_text(ega.get_start_iter(),
					ega.get_end_iter()))
			header['date'] = egd.get_text()
			header['black'] = egb.get_text()
			header['white'] = egw.get_text()
			header['site'] = egs.get_text()
			header['round'] = egn.get_text()
			header['result'] = egr.get_text()
			header['date'] = egd.get_text()
			Main.feedback.g_push('Game headers set')
		else:
			Main.feedback.g_push('Edit game cancelled')
		editor.hide()

	def edit_move(self, model, path):
		"edit move info and dialog"
		move = model.get_iter(path)
		stren, annotation = model.get(move,
			Book.COL_STREN, Book.COL_ANNO)
		editor = Main.gui['Edit move...']
		emsn = Main.gui['EM strength']
		emso = Main.gui['EM strong']
		emsa = Main.gui['EM star']
		emsw = Main.gui['EM weak']
		ema = Main.gui['EM annotation'].get_buffer()
		if stren == '!': emso.set_active(1)
		elif stren == '*': emsa.set_active(1)
		elif stren == '?': emsw.set_active(1)
		else: emsn.set_active(1)
		ema.set_text(annotation)
		if editor.run() == gtk.RESPONSE_OK:
			if emso.state: stren = '!'
			elif emsa.state: stren = '*'
			elif emsw.state: stren = '?'
			else: stren = ''
			model.set(move, Book.COL_STREN, stren)
			model.set(move, Book.COL_ANNO,
				ema.get_text(ema.get_start_iter(), ema.get_end_iter()))
			Main.feedback.g_push('Move info set')
		else:
			Main.feedback.g_push('Edit move cancelled')
		editor.hide()

	def on_activate_row(self, treeview, path, column):
		"on double click on row edit game or move"
		if Main.board.busy or Main.board.edit: return False
		if len(path) == 1:
			Main.feedback.g_push('Edit game headers')
			self.edit_game(treeview.get_model(), path)
		else:
			Main.feedback.g_push('Edit move info')
			self.edit_move(treeview.get_model(), path)
		return True
		
	def on_change_selection(self, selection):
		"on selction change goto selected game or move"
		if Main.game.lock.locked(): return False
		if Main.board.busy or Main.board.edit: return False
		model, iter = selection.get_selected()
		if not iter: return False
		Main.game.goto_game_move(model.get_path(iter))
		return True
		
	def open(self, book):
		"connect to the model, install callbacks"
		self._book = book
		self.set_model(book)
		column = gtk.TreeViewColumn('Book')
		column.set_fixed_width(210)
		self.append_column(column)
		
		cell = CellRendererWrap()
		column.pack_start(cell, False)
		w = column.get_fixed_width()
		cell.set_property('width', w - 20)
		column.set_cell_data_func(cell, self.do_markup)
		self.connect('row-activated', self.on_activate_row)
		selection = self.get_selection()
		selection.connect('changed', self.on_change_selection)

	def do_markup (self, column, cell, model, iter):
		"add annotation and headers to cells markup"
		name = model.get_value(iter, model.COL_NAME)
		name = name.replace('&', '&amp;')
		if model.get_value(iter, model.COL_TURN) == Position.WHITE:
			norm = '<span foreground="#C0000C">%s</span>'
			bold = '<b>%s</b>'
		else:
			norm = '%s'
			bold = '<b>%s</b>'
		header = model.get_value(iter, model.COL_HEAD)
		if header:
			black, white, result = \
				header['black'], header['white'], header['result']
			markup = bold % name + '\nBlack: %s' % black \
				+ '\nWhite: %s' % white + '\nResult: %s' % result
		else:
			markup = norm % name
		stren = model.get_value(iter, model.COL_STREN)
		if stren:
			markup = markup + stren
		anno = model.get_value(iter, model.COL_ANNO)
		if anno:
			anno = anno.replace('&', '&amp;')
			markup = markup +  '\n' + anno
		cell.set_property('markup', markup)

	def connect_model(self, toggle=True):
		"toggle/connect from book"
		if toggle == False:
			self.set_model(None)
		else:
			self.set_model(self._book)
gobject.type_register(BookView) # make widget available to libglade


# ===========
# E N G I N E
# ===========

from ctypes import cdll, c_int, c_double, c_char_p, c_buffer, Structure
from ctypes import sizeof, byref

class CBcoor(Structure):
	"cb api coordinates structure"
	_fields_ = [("x", c_int), ("y", c_int)]

class CBmove(Structure):
	"cb api move structure"
	_fields_ = [("jumps", c_int),
		("newpiece", c_int),
		("oldpiece", c_int),
		("mfrom", CBcoor),
		("mto", CBcoor),
		("path", CBcoor * 12),
		("mdel", CBcoor * 12),
		("delpiece", c_int * 12)]

class Engine (gobject.GObject):
	"""interface to the checkers engine dll

	on init this class loads an engine. it also translates between
	the different data types of the C-api and the python game

	unlike "enginecommand()" and "islegal()", which return in an
	instant, the "getmove()" function needs to be in a thread: when
	its done, it will install game.do_enginemove as an idle task
	in gtk.
	
	getmove will change the game.lock, so feedback can know, when
	the engine stopped. gtk seems to cycle thread locks, so not
	deleting it, should not leak.

	there is only ever one engine active at a time, as the CBapi
	does not support thinking on the opponents time. so its ok to
	lock the game, not the engine thread.

	engines have to conform to the CheckerBoard API by Martin Fierz.
	engines are written eg. in C, and can be loaded and removed at
	runtime
	"""

	# game result codes
	DRAW = 0
	WIN = 1
	LOSS = 2
	UNKNOWN = 3

	def __init__(self, enginefile):
		"load a dll, set globals: name, gametype, about, help"
		gobject.GObject.__init__(self)
		try:
			self.engine = cdll.LoadLibrary(enginefile)
		except OSError:
			Fatal('Invalid engine, please remove:\n\n'
				+ enginefile)

		self.name = self.about = self.help = ''
		res = self.enginecommand('name')
		if res[0]:
			self.name = res[1]
		res = self.enginecommand('about')
		if res[0]:
			self.about = res[1]
		res = self.enginecommand('help')
		if res[0]:
			self.help = res[1]

	def get(self, key):
		"shorthand enginecommand get: gametype..."
		res = self.enginecommand('get ' + key)
		if res[0]:
			return res[1]
		return False

	def cbcoor2num(self, cbcoor):
		"convert CBapi coordinate structure to board number"
		x = cbcoor.x
		y = cbcoor.y
		if Main.game.gametype == Main.game.ENGLISH:
			y = 8 - y - 1
		elif Main.game.gametype == Main.game.MAFIERZ:
			x = 8 - x - 1
		return Main.game.coor2num(x, y)

	def pos2cbboard(self, position, board):
		"""copy position to CBapi board
		in CBapi, origin is SW, in capers origin is NW"""
		cells = 8
		if Main.game.gametype == Main.game.INTERNL: cells = 10

		if Main.game.gametype == Main.game.ENGLISH:
			for s in position:
				v, x, y = s[Position.COL_VAL], \
					s[Position.COL_X], s[Position.COL_Y]
				if v:
					board[x][cells-y-1] = v
		elif Main.game.gametype == Main.game.MAFIERZ:
			for s in position:
				v, x, y = s[Position.COL_VAL], \
					s[Position.COL_X], s[Position.COL_Y]
				if v:
					board[cells-x-1][y] = v
		else:
			assert 0 # gametype not supported
		if 0: # print board
			squares = "-    wb  WB      "
			for x in range(cells):
				print ' '.join([squares[num] for num in board[x]])
			print

	# int enginecommand(char str[256], char reply[256]);
	def enginecommand(self, command):
		"mostly 'get gametype' and 'name'"
		res = 0
		buf = c_buffer(256) # create_string_buffer

		argtypes = [c_char_p, c_char_p]
		res = self.engine.enginecommand(command, buf)
		return res, buf.value

	# int islegal(int b[8][8], int color, int from, int to,
	#             struct CBmove *move);
	def islegal(self, list, color, position, cbmove):
		"check move in list, return False if illegal, else return list"
		cells = 8
		if len(position) == 100: cells = 10

		board = ((c_int * cells) * cells)()
		color = c_int(color)
		mfrom = c_int(list[0])
		mto = c_int(list[-1])
		cbmove = CBmove()

		self.pos2cbboard(position, board)

		# call engine
		argtypes = [(c_int * cells) * cells, c_int, c_int, c_int, CBmove]
		res = self.engine.islegal(board, color, mfrom, mto, byref(cbmove))

		steps = [self.cbcoor2num(cbmove.mfrom)]
		for i in range(1, cbmove.jumps):
			steps.append(self.cbcoor2num(cbmove.path[i]))
		steps.append(self.cbcoor2num(cbmove.mto))

		# collapse duplicate fields in movelist
		s = steps[-1]
		for i in range(len(steps)-2, -1, -1):
			if steps[i] == s: del steps[i]
			else: s = steps[i]

		huffs = []
		for i in range(cbmove.jumps):
			huffs.append(self.cbcoor2num(cbmove.mdel[i]))
		return [res, steps, cbmove.newpiece, cbmove.oldpiece, huffs]

	def showbuf(self, lock, buf):
		"engine feedback, in timeout, stop when lock lost/released"
		if not lock.locked():
			return False
		if lock != Main.game.lock:
			return False
		Main.feedback.e_push(buf.value)
		return lock.locked()

	def playnow(self, lock, playnow):
		"engine break, in timeout, stop when break or lock lost/released"
		if not Main.game.engines_loop:
			playnow.value = 1
			return False
		if lock != Main.game.lock:
			return False
		return lock.locked()

	# int getmove(int b[8][8],int color, double maxtime, char str[255],
	#             int *playnow, int info, int unused, struct CBmove *move);
	def getmove(self, data):
		"wraps the threaded call to the engine, always return False"
		assert not Main.game.lock.locked()
		Main.game.lock = thread.allocate_lock()
		Main.game.lock.acquire()
		assert thread.start_new_thread(
			self.getmove_thread, ((Main.game.lock, data)))

	def getmove_thread(self, lock, data):
		"start searching a move; in a thread"
		color, maxtime, position = data
		cells = 8
		if len(position) == 100: cells = 10

		board = ((c_int * cells) * cells)()
		self.pos2cbboard(position, board)
		color = c_int(color)
		maxtime = c_double(maxtime)
		buf = c_buffer(1024) # create_string_buffer
		playnow = c_int(0)
		info = c_int(0)
		moreinfo = c_int(0)
		cbmove = CBmove()

		# let main thread handle feedback, break
		gobject.timeout_add(200, self.showbuf, lock, buf)
		gobject.timeout_add(100, self.playnow, lock, playnow)

		argtypes = [(c_int * cells) * cells, c_double, c_char_p,
			c_int, c_int, c_int, CBmove]
		res = self.engine.getmove(board, color, maxtime, buf,
			byref(playnow), info, moreinfo, byref(cbmove))

		steps = [self.cbcoor2num(cbmove.mfrom)]
		for i in range(1, cbmove.jumps):
			steps.append(self.cbcoor2num(cbmove.path[i]))
		steps.append(self.cbcoor2num(cbmove.mto))

		# collapse duplicate fields in movelist
		s = steps[-1]
		for i in range(len(steps)-2, -1, -1):
			if steps[i] == s: del steps[i]
			else: s = steps[i]

		huffs = []
		for i in range(cbmove.jumps):
			huffs.append(self.cbcoor2num(cbmove.mdel[i]))

		# let main thread handle the move
		gobject.idle_add(Main.game.do_enginemove,
			(res, steps, cbmove.newpiece, cbmove.oldpiece, huffs, lock))
gobject.type_register(Engine) # make widget available to Player ListStore

# =========
# B O A R D
# =========

class CheckerBoard(gnome.canvas.Canvas):
	"""present the game visually

	- the user may drag pieces (event handler)
	- the game may move, take, crown pieces (public method)

	the board does not know the rules, as soon as a piece is dropped,
	the board will ask the game if the move was legal, and if it
	wasnt, will put the piece back to the start, otherwise, it will
	pass the result of the query on to the game

	board coordinates start in the top-left corner (NORTHWEST), the
	other classes send and get calibrated coordinates (0-[79])

	the board also does not know the numbering scheme and where the
	double corner lies. this information is included in the position
	passed when a new board is setup

	the board resizes itself to match the setup, and flips, if asked
	
	self.busy is true, while a piece is moved by user or engine
	"""

	# private globals
	_grid_width = 0
	_board_width = 0
	_temp_move = []
	_gametype = 0
	_flipped = False # True when upsidedown
	_x1 = _y1 = 0 # drag start point
	busy = False # True while move_piece
	edit = False # True while editing

	def __init_(self):
		"never called, should libglade do that?"
		assert 0

	def new(self, gametype, setup, flip):
		"create board backdrop, pieces, numbers from setup"
		self._gametype = gametype
		self._flipped = False

		# grid_width is derived from loaded pixmap
		scenefile = Main.prefs.get('look', 'scene')
		pb = gtk.gdk.pixbuf_new_from_file(scenefile)
		gw = pb.get_height()
		self._grid_width = gw

		# board_width is derived from passed setup
		assert(len(setup) in (64, 100))
		if (len(setup) == 64):
			bw = gw * 8
		elif (len(setup) == 100):
			bw = gw * 10
		self._board_width = bw
		if self.get_size() != (bw, bw):
			self.set_size_request(bw, bw)
			self.set_scroll_region(0, 0, bw, bw)

		# delete previous canvas items
		if dir(self).count('background'):
			self.background.destroy()
			del self.background
		if dir(self).count('numbers'):
			self.numbers.destroy()
			del self.numbers
		if dir(self).count('pieces'):
			self.pieces.destroy()
			del self.pieces

		# all new, scene pixmap might have changed
		self.background = self.root().add(gnome.canvas.CanvasPixbuf)
		self.numbers = self.root().add(gnome.canvas.CanvasGroup)
		self.pieces = self.root().add(gnome.canvas.CanvasGroup)
		bg = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, bw, bw)
		bm = pb.subpixbuf(gw*2, 0, gw, gw)
		wm = pb.subpixbuf(gw*3, 0, gw, gw)
		bk = pb.subpixbuf(gw*4, 0, gw, gw)
		wk = pb.subpixbuf(gw*5, 0, gw, gw)
		# map squares e=0, f=16
		# map pieces  w=5, b=6, W=9, B=10
		#          0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
		squares = [1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0]
		figures = [0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0]
		pixbufs = [0, 0, 0, 0, 0,wm,bm, 0, 0,wk,bk, 0, 0, 0, 0, 0, 0]
		self.pixbufs = pixbufs
		i = 0
		for s in setup:
			n, v, x, y = s[Position.COL_NUM], s[Position.COL_VAL], \
				s[Position.COL_X], s[Position.COL_Y]
			# background
			pb.copy_area(squares[v] * gw,
				0, gw, gw, bg, x * gw, y * gw)
			# numbers
			if squares[v]:
				m = self.numbers.add(gnome.canvas.CanvasText,
					anchor=gtk.ANCHOR_SOUTH_EAST)
				m.set(text=n, x=x * gw + gw, y=y * gw + gw)
			# pieces
			if figures[v]:
				p = self.pieces.add(gnome.canvas.CanvasPixbuf)
				p.set(pixbuf=pixbufs[v], x=x * gw, y=y * gw)
				p.connect('event', self.on_piece_event)
				setup[i][Position.COL_PIECE] = p
			i += 1
		self.connect('event', self.on_board_event)
		self.background.set(pixbuf=bg)
		del pb, bg, squares, figures, m, p
		self.flip(flip)

	def flip(self, flip='flip'):
		"quickly rotate board"
		if flip == self._flipped:
			return self._flipped
		# if called from action
		if flip == 'flip':
			self._flipped = not self._flipped
		else:
			self._flipped = flip
		gw = self._grid_width
		bw = self._board_width

		for n in self.numbers.item_list:
			a, b, x, y = n.get_bounds()
			x, y = n.i2w(x, y)
			n.set(x=bw-x+gw, y=bw-y+gw)
		for p in self.pieces.item_list:
			a, b, x, y = p.get_bounds()
			x, y = p.i2w(x, y)
			p.set(x=bw-x, y=bw-y)

	def setposition(self, setup):
		"quickly switch to setup position, only same game"
		figures = [0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0]
		gw = self._grid_width
		bw = self._board_width
		for s in setup:
			n, v, x, y, p = s[Position.COL_NUM], s[Position.COL_VAL], \
				s[Position.COL_X], s[Position.COL_Y], s[Position.COL_PIECE]
			if figures[v]:
				if self._flipped:
					x, y = p.w2i(bw - x * gw - gw, bw - y * gw - gw)
				else:
					x, y = p.w2i(x * gw, y * gw)
				p.set(pixbuf=self.pixbufs[v], x=x, y=y)
				p.show()
			elif p:
				p.hide()
		#self.update_now()

	def on_board_event(self, num, event):
		"handle events on board, ie. menu and edit mode"
		if event.type != gtk.gdk.BUTTON_PRESS: return False
		if self.busy: return False

		# context menu
		if event.button == 3:
			menu = Main.gui['Menu']
			menu.popup(None,None,None,event.button,event.time)
			return True

		if not self.edit: return False
		
		gw = self._grid_width
		bw = self._board_width
		cells = bw / gw

		x = math.floor(event.x / gw)
		y = math.floor(event.y / gw)
		num = Main.game.coor2num(x, y)
		if not num: return False

		# promotion cycle: empty, bm, bk, wm, wk, empty
		value = Main.game.num2val(num)
		if not value:
			value = Position.BLACK | Position.MAN
		elif value == Position.WHITE | Position.KING:
			value = 0
		elif value & Position.MAN:
			value ^= Position.MAN
			value |= Position.KING
		elif value & Position.KING:
			value ^= Position.KING
			value |= Position.MAN
			value ^= Position.CC
		Main.game.promote(num, value)
		return True

	def on_piece_event(self, piece, event):
		"handle events on pieces, ie. dragndrop"
		if self.edit: return True
		if Main.game.lock.locked(): return True

		gw = self._grid_width
		bw = self._board_width
		cells = bw / gw

		# drag
		if event.type == gtk.gdk.BUTTON_PRESS:
			if self.busy: return False
			x = math.floor(event.x / gw)
			y = math.floor(event.y / gw)
			if self._flipped:
				num = Main.game.coor2num(cells - x - 1, cells - y - 1)
			else:
				num = Main.game.coor2num(x, y)
			assert num
			# intermediate square
			if self._x1:
				self._temp_move.append(num)
				return True
			# starting square
			self._x1 = self._x = event.x
			self._y1 = self._y = event.y
			"""
			################
			# TODO item.grab
			################
			"""
			piece.raise_to_top()
			self._temp_move = [num]
			self.busy = True
			return True
		# piece dropped
		if self._x1 == 0:
			self.busy = False
			return True
		# drop
		if event.type == gtk.gdk.BUTTON_RELEASE:
			x = math.floor(event.x / gw)
			y = math.floor(event.y / gw)
			if self._flipped:
				num = Main.game.coor2num(cells - x - 1, cells - y - 1)
			else:
				num = Main.game.coor2num(x, y)
			# ending square
			self._temp_move.append(num)
			legal = Main.game.engine_islegal(self._temp_move)
			# not legal, return to start
			if not legal[0]:
				u = self._x1 - self._x
				v = self._y1 - self._y
				piece.move(u, v)
				self._x1 = self._y1 = 0
				self._temp_move = []
				self.busy = False
				return True
			# legal, snap piece to grid
			x *= gw
			y *= gw
			x, y = piece.w2i(x, y)
			piece.set(x=x, y=y)
			self._x1 = self._y1 = 0
			Main.game.do_usermove(self._temp_move, legal)
			self.busy = False
			return True
		# ignore other events
		if event.type != gtk.gdk.MOTION_NOTIFY:
			return True
		# off board, return to start
		if event.x < 0 or event.y < 0 or event.x > bw or event.y > bw:
			u = self._x1 - self._x
			v = self._y1 - self._y
			piece.move(u, v)
			self._x1 = self._y1 = 0
			self.busy = False
			return False
		u = event.x - self._x
		v = event.y - self._y
		piece.move(u, v)
		self._x = event.x
		self._y = event.y
		return True

	def take_piece(self, num):
		"hide piece on square <num>"
		piece = Main.game.num2piece(num)
		assert piece
		piece.hide()
		self.update_now()

	def set_piece(self, num, value):
		"make piece on square <num> of <value>, return new piece"
		piece = Main.game.num2piece(num)
		if not self.edit:
			assert piece
		if not value:
			piece.destroy()
			return 0
		elif not piece:
			piece = self.pieces.add(gnome.canvas.CanvasPixbuf)
			x, y = Main.game.num2coor(num)
			gw = self._grid_width
			piece.set(pixbuf=self.pixbufs[value], x=x * gw, y=y * gw)
			piece.connect('event', self.on_piece_event)
		else:
			piece.set(pixbuf=self.pixbufs[value])
		return piece

	def move_piece(self, a, b,):
		"animate move, set board to 'busy'"
		def step(x, y):
			"diagonal path"
			u = v = 1
			if x < 0: u = -1
			if y < 0: v = -1
			for i in xrange(max(abs(x),abs(y))):
				if i > abs(x): u = 0
				if i > abs(y): v = 0
				yield((u, v))
		piece = Main.game.num2piece(a)
		assert piece
		self.busy = True
		piece.raise_to_top()
		gw = self._grid_width
		bw = self._board_width
		x1, y1 = Main.game.num2coor(a)
		x2, y2 = Main.game.num2coor(b)
		if self._flipped:
			x1, y1 = bw - x1, bw - y1
			x2, y2 = bw - x2, bw - y2
		for u, v in step((x2 - x1) * gw, (y2 - y1) * gw):
			piece.move(u, v)
			self.update_now()
		self.busy = False

	def move_piece2(self, a, b):
		"animate move in gtk.idle, set board to 'busy'"
		def step(x, y):
			"diagonal path"
			u = v = 1
			if x < 0: u = -1
			if y < 0: v = -1
			for i in xrange(max(abs(x),abs(y))):
				if i > abs(x): u = 0
				if i > abs(y): v = 0
				piece.move(u, v)
				yield True
			self.busy = False
			yield False
		def wait(x, y):
			if self.busy:
				yield True
			self.busy = True
			gobject.idle_add(step(x, y).next)
			yield False
		piece = Main.game.num2piece(a)
		assert piece
		piece.raise_to_top()
		gw = self._grid_width
		x1, y1 = Main.game.num2coor(a)
		x2, y2 = Main.game.num2coor(b)
		gobject.idle_add(wait((x2 - x1) * gw, (y2 - y1) * gw).next)
gobject.type_register(CheckerBoard) # make widget available to libglade


# =============
# P L A Y E R S
# =============

import glob

class Players(gtk.ListStore):
	"""list the possible opponents in a game

	human is always first, then comes the list of available engines
	human gets a gametype of 0, to be distinguishable from engines

	subclasses liststore, to be suitable as a model for the engines
	popup in the "New..." dialogue
	"""

	COL_FILE = 0
	COL_NAME = 1
	COL_GAMETYPE = 2
	COL_GAMENAME = 3
	COL_ABOUT = 4
	COL_HELP = 5
	COL_ENGINE = 6

	def __init__(self):
		"human is first, then load engines, ask them for gametype etc."
		super(Players, self).__init__(str, str, int, str, str, str, Engine)

		# human player, aka user
		name = Main.prefs.get('player', 'name')
		self.append(['human', name, 0, 'any', 'Human', 'None', None])

		# engines
		libdir = Main.prefs.get('paths', 'engines')
		if os.name == 'nt':
			search = os.path.join(libdir, '*.dll')
		else:
			search = os.path.join(libdir, '*.so')
		engines = glob.glob(search)

		for fn in engines:
			engine = Engine(fn)
			try:
				name, about, help = engine.name, \
					engine.about, engine.help
				gametype = int(engine.get('gametype'))
			except:
				del engine
				continue
			if gametype == Main.game.INTERNL:
				gamename = 'International'
			elif gametype == Main.game.ENGLISH:
				gamename = 'English'
			elif gametype == Main.game.ITALIAN:
				gamename = 'Italian'
			elif gametype == Main.game.RUSSIAN:
				gamename = 'Russian'
			elif gametype == Main.game.MAFIERZ:
				gamename = 'Italian1'
			assert gamename
			self.append([fn, name, gametype, gamename,
				about, help, engine])

	# convenience
	def gt2engine(self, gametype):
		"return an engine for a gametype, the first one found"
		iter = self.get_iter_first()
		while iter:
			if self.get_value(iter, self.COL_GAMETYPE) == gametype:
				return self.get_value(iter, self.COL_ENGINE)
			iter = self.iter_next(iter)
		assert 0

	def file2engine(self, filename):
		"return an engine for a filename"
		iter = self.get_iter_first()
		while iter:
			if self.get_value(iter, self.COL_FILE) == filename:
				return self.get_value(iter, self.COL_ENGINE)
			iter = self.iter_next(iter)
		assert 0

	def file2name(self, file):
		"return the name of the engine corresponding to <file>"
		iter = self.get_iter_first()
		while iter:
			if self.get_value(iter, self.COL_FILE) == file:
				return self.get_value(iter, self.COL_NAME)
			iter = self.iter_next(iter)
		assert 0

	def name2engine(self, name):
		"return the name of the engine corresponding to <file> or None"
		iter = self.get_iter_first()
		while iter:
			if self.get_value(iter, self.COL_NAME) == name:
				return self.get_value(iter, self.COL_ENGINE)
			iter = self.iter_next(iter)
		return None

	def name2file(self, name):
		"return the name of the engine corresponding to <file> or human"
		iter = self.get_iter_first()
		while iter:
			if self.get_value(iter, self.COL_NAME) == name:
				return self.get_value(iter, self.COL_FILE)
			iter = self.iter_next(iter)
		return 'human'


# =====
# G U I
# =====

class NewDialog(gtk.Dialog):
	"""Start new game with options

	Options are: gametype, black and white players
	The selection of players depends on the gametype, as engines are
	specifically adapted to one; only the human player can play all
	the different types, the exclude filter takes that into account.
	the unique filter's types list is preset with 0, as to not show
	the humans "any" gametype
	"""

	_gametype = 0
	_gametypes = [0]

	def gt_exclude(self, model, iter):
		"exclude entries by global gametype"
		gt = model.get_value(iter, Main.players.COL_GAMETYPE)
		if gt == 0:
			return True
		if gt == self._gametype:
			return True
		return False

	def gt_unique(self, model, iter):
		"only one entry per gametype"
		gt = model.get_value(iter, Main.players.COL_GAMETYPE)
		if gt in self._gametypes:
			return False
		self._gametypes.append(gt)
		return True

	def on_gt_change(self, gbox, xfil):
		"change filter for players"
		iter = gbox.get_active_iter()
		model = gbox.get_model()
		self._gametype = model.get_value(iter, Main.players.COL_GAMETYPE)
		xfil.refilter()
		bbox = Main.gui['NewBlackBox']
		iter = xfil.get_iter_first()
		bbox.set_active_iter(iter)
		wbox = Main.gui['NewWhiteBox']
		iter = xfil.get_iter_first()
		wbox.set_active_iter(iter)

	def reset(self):
		"change filter for players to prefs, called from gui"
		if not self._gametype:
			self.prepare()
		self._gametype = Main.prefs.getint('game', 'type')

		# gametypes
		gbox = Main.gui['NewGametypeBox']
		iter = self.ufil.get_iter_first()
		while iter:
			if self.ufil.get_value(iter, Main.players.COL_GAMETYPE) \
				== self._gametype:
				gbox.set_active_iter(iter)
				break
			iter = self.ufil.iter_next(iter)
		else:
			assert 0

		# players
		bbox = Main.gui['NewBlackBox']
		wbox = Main.gui['NewWhiteBox']
		iter = self.xfil.get_iter_first()
		bbox.set_active_iter(iter)
		wbox.set_active_iter(iter)
		black = Main.prefs.get('game', 'black')
		white = Main.prefs.get('game', 'white')
		while iter:
			file = self.xfil.get_value(iter, Main.players.COL_FILE)
			if file == black:
				bbox.set_active_iter(iter)
			if file == white:
				wbox.set_active_iter(iter)
			iter = self.xfil.iter_next(iter)

	def save(self):
		"write current selection to prefs"
		bbox = Main.gui['NewBlackBox']
		wbox = Main.gui['NewWhiteBox']
		model = bbox.get_model()
		iter = bbox.get_active_iter()
		assert iter
		black = self.xfil.get_value(iter, Main.players.COL_FILE)
		iter = wbox.get_active_iter()
		assert iter
		white = self.xfil.get_value(iter, Main.players.COL_FILE)
		Main.prefs.set('game', 'type', self._gametype)
		Main.prefs.set('game', 'black', black)
		Main.prefs.set('game', 'white', white)
		Main.prefs.save()

	def prepare(self):
		self._gametype = Main.prefs.getint('game', 'type')
		black = Main.prefs.get('game', 'black')
		white = Main.prefs.get('game', 'white')

		# exclusive gametype filter
		self.xfil = Main.players.filter_new()
		self.xfil.set_visible_func(self.gt_exclude)

		# unique gametypes filter
		self.ufil = Main.players.filter_new()
		self.ufil.set_visible_func(self.gt_unique)

		# gametypes
		gbox = Main.gui['NewGametypeBox']
		cell = gtk.CellRendererText()
		gbox.pack_start(cell, True)
		gbox.add_attribute(cell, 'text', Main.players.COL_GAMENAME)
		gbox.set_model(self.ufil)
		gbox.connect('changed', self.on_gt_change, self.xfil)

		# players
		bbox = Main.gui['NewBlackBox']
		cell = gtk.CellRendererText()
		bbox.pack_start(cell, True)
		bbox.add_attribute(cell, 'text', Main.players.COL_NAME)
		bbox.set_model(self.xfil)

		wbox = Main.gui['NewWhiteBox']
		cell = gtk.CellRendererText()
		wbox.pack_start(cell, True)
		wbox.add_attribute(cell, 'text', Main.players.COL_NAME)
		wbox.set_model(self.xfil)

		self.reset()
gobject.type_register(NewDialog) # make widget available to libglade

class Feedback(gtk.Statusbar):
	"""the statusbar displays mostly what the engine thinks it does"""

	def prepare(self):
		"setup statusbar contexts: engine, game"
		self.e_con = self.get_context_id('Engine')
		self.g_con = self.get_context_id('Game')

	def e_push(self, message):
		"write a message to the engine context, pop old one"
		self.pop(self.e_con)
		self.push(self.e_con, message)
		return False

	def g_push(self, message):
		"write a message to the game context, pop old one"
		self.pop(self.g_con)
		self.push(self.g_con, message)
		return False
gobject.type_register(Feedback) # make widget available to libglade
		

class GladeGui:
	"""interface with the libglade runtime

	the layout of the application window is described in a file
	that libglade loads at runtime. signal handlers are installed
	in this class' dictionary. widgets are made available as
	attributes of this class

	display of pieces and numbers can be toggled
	"""

	types = dict(GnomeCanvas=CheckerBoard,
		GtkTreeView=BookView,
		GtkDialog=NewDialog,
		GtkStatusbar=Feedback)

	def __getitem__(self, key):
		"Make widgets available as attributes of this class"
		return self.tree.get_widget(key)

	def __init__(self, gladefile):
		"""Load the interface descripton and connect the signals
		setup up actions and accelerators, create clipboard"""
		self.tree = gtk.glade.XML(gladefile, typedict=self.types)
		self.tree.signal_autoconnect(GladeGui.__dict__)
		self.editempty = False

		# clipboard
		self.clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)

		# menu
		menu = self['Menu']
	
		# action definitions
		accelgroup = gtk.AccelGroup()
		self['Capers'].add_accel_group(accelgroup)
		actiongroup = gtk.ActionGroup('Capers')
		self.actiongroup = actiongroup

		action = gtk.Action('flip', 'F_lip board', 'Flip board', None)
		action.connect('activate', self.flip_cb)
		actiongroup.add_action_with_accel(action, '<control>l')
		action.set_accel_group(accelgroup)
		action.connect_accelerator()
		menu.append(action.create_menu_item())

		action = gtk.ToggleAction('edit', '_Edit board', 'Edit board', None)
		action.connect('activate', self.edit_cb)
		actiongroup.add_action_with_accel(action, '<control>e')
		action.set_accel_group(accelgroup)
		action.connect_accelerator()
		menu.append(action.create_menu_item())

		action = gtk.Action('editempty', '_Edit empty board', \
			'Edit empty board', None)
		action.connect('activate', self.editempty_cb)
		actiongroup.add_action_with_accel(action, '<control><shift>e')
		action.set_accel_group(accelgroup)
		action.connect_accelerator()
		menu.append(action.create_menu_item())
		
		sep = gtk.SeparatorMenuItem()
		sep.show()
		menu.append(sep)

		action = gtk.Action('copy', '_Copy game', \
			'Copy game', gtk.STOCK_COPY)
		action.connect('activate', self.copy_cb)
		actiongroup.add_action_with_accel(action, None)
		action.set_accel_group(accelgroup)
		action.connect_accelerator()
		menu.append(action.create_menu_item())

		action = gtk.Action('paste', '_Paste game', \
			'Paste game', gtk.STOCK_PASTE)
		action.connect('activate', self.paste_cb)
		actiongroup.add_action_with_accel(action, None)
		action.set_accel_group(accelgroup)
		action.connect_accelerator()
		menu.append(action.create_menu_item())

		action = gtk.Action('open', '_Open book', 'Open book', gtk.STOCK_OPEN)
		action.connect('activate', self.open_cb)
		actiongroup.add_action_with_accel(action, None)
		action.connect_proxy(self['Open book'])
		action.set_accel_group(accelgroup)
		action.connect_accelerator()
		menu.append(action.create_menu_item())

		action = gtk.Action('save', '_Save game', 'Save game', gtk.STOCK_SAVE)
		action.connect('activate', self.save_cb)
		actiongroup.add_action_with_accel(action, None)
		action.connect_proxy(self['Save game'])
		action.set_accel_group(accelgroup)
		action.connect_accelerator()
		menu.append(action.create_menu_item())
		
		sep = gtk.SeparatorMenuItem()
		sep.show()
		menu.append(sep)

		action = gtk.Action('new', '_New game', 'New game', gtk.STOCK_NEW)
		action.connect('activate', self.new_cb)
		actiongroup.add_action_with_accel(action, None)
		action.connect_proxy(self['New game'])
		action.set_accel_group(accelgroup)
		action.connect_accelerator()
		menu.append(action.create_menu_item())

		action = gtk.Action('nwo', '_New game with options',
			'New game with options', gtk.STOCK_PROPERTIES)
		action.connect('activate', self.nwo_cb)
		actiongroup.add_action_with_accel(action, '<control><shift>n')
		action.connect_proxy(self['New game with options'])
		action.set_accel_group(accelgroup)
		action.connect_accelerator()
		menu.append(action.create_menu_item())

		action = gtk.Action('quit', '_Quit', 'Quit program', gtk.STOCK_QUIT)
		action.connect('activate', self.on_wm_quit)
		actiongroup.add_action_with_accel(action, None)
		action.set_accel_group(accelgroup)
		action.connect_accelerator()
		menu.append(action.create_menu_item())

	# action callbacks
	def quit_cb(self, *args):
		gtk.main_quit()

	def new_cb(self, *args):
		"new same game"
		if not Main.game.lock.locked():
			Main.game.new()

	def nwo_cb(self, *args):
		"new game with options"
		if Main.game.lock.locked():
			Main.feedback.g_push('Function locked!')
			return
		Main.feedback.g_push('Select options for new game...')
		nwo = Main.gui['New...']
		nwo.reset()
		nwo.connect("close", lambda w: nwo.hide()) # esc key
		if nwo.run() == gtk.RESPONSE_OK:
			nwo.save()
			Main.game.new()
		else:
			Main.feedback.g_push('New game cancelled')
		nwo.hide()

	def open_cb(self, *args):
		"load book from pdn file"
		if Main.game.lock.locked():
			return
		Main.feedback.g_push('Select book to open...')
		fc = gtk.FileChooserDialog(title='Open...',
			action=gtk.FILE_CHOOSER_ACTION_OPEN,
			buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
			gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		fc.set_default_response(gtk.RESPONSE_OK)
		filter = gtk.FileFilter()
		filter.set_name("Checkers Books")
		filter.add_pattern("*.pdn")
		filter.add_mime_type("text/*")
		fc.add_filter(filter)
		filter = gtk.FileFilter()
		filter.set_name("All Files")
		filter.add_pattern("*")
		fc.add_filter(filter)
		opendir = Main.prefs.get('paths', 'opengame')
		fc.set_current_folder(opendir)
		if fc.run() == gtk.RESPONSE_OK:
			fn = fc.get_filename()
			try:
				f = open(fn, 'r')
			except:
				Main.feedback.g_push('Could not open file')
				fc.destroy()
				return
			pdn = Pdn(f, fn)
			pdn.parse()
			f.close()
			# save path
			opendir = os.path.dirname(fn)
			Main.prefs.set('paths', 'opengame', opendir)
			Main.prefs.save()
		else:
			Main.feedback.g_push('Open book cancelled')
		fc.destroy()

	def save_cb(self, *args):
		"save current game as pdn"
		if Main.game.lock.locked():
			return
		Main.feedback.g_push('Select file for saving...')
		fc = gtk.FileChooserDialog(title='Save as...',
			action=gtk.FILE_CHOOSER_ACTION_SAVE,
			buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
			gtk.STOCK_SAVE, gtk.RESPONSE_OK))
		fc.set_default_response(gtk.RESPONSE_OK)
		filter = gtk.FileFilter()
		filter.set_name("Checkers Books")
		filter.add_pattern("*.pdn")
		filter.add_mime_type("text/*")
		fc.add_filter(filter)
		filter = gtk.FileFilter()
		filter.set_name("All Files")
		filter.add_pattern("*")
		fc.add_filter(filter)
		filename, text = Main.book.game2pdn()
		filename = filename + '.pdn'
		fc.set_current_name(filename)
		savedir = Main.prefs.get('paths', 'savegame')
		fc.set_current_folder(savedir)
		if fc.run() == gtk.RESPONSE_OK:
			fn = fc.get_filename()
			f = open(fn, 'w')
			f.write(text)
			f.close
			# save path
			savedir = os.path.dirname(fn)
			Main.prefs.set('paths', 'savegame', savedir)
			Main.prefs.save()
			Main.feedback.g_push('Game saved: ' + fn)
		else:
			Main.feedback.g_push('Save game cancelled')
		fc.destroy()

	def copy_cb(self, *args):
		"copy game"
		if Main.game.lock.locked():
			return
		Main.feedback.g_push('Copy current game to clipboard')
		filename, text = Main.book.game2pdn()
		self.clipboard.set_text(text)
		Main.feedback.g_push('Copied current game to clipboard')

	def paste_cb(self, *args):
		"paste game"
		if Main.game.lock.locked():
			return
		Main.feedback.g_push('Paste book from clipboard')
		text = self.clipboard.wait_for_text()
		if not text or text == '':
			Main.feedback.g_push('Clipboard empty')
			return
		pdn = Pdn(text, 'clipboard')
		pdn.parse()

	def edit_cb(self, *args):
		"edit board toggle"
		action = self.actiongroup.get_action('edit')
		if Main.board.edit:
			Main.game.stop_edit()
			Main.board.edit = False
			action.set_active(False)
		else:
			Main.game.start_edit(self.editempty)
			Main.board.edit = True
			action.set_active(True)
		assert action.get_active() == Main.board.edit
		self.editempty = False

	def editempty_cb(self, *args):
		"edit empty board toggle, set global, then call edit board"
		action = self.actiongroup.get_action('edit')
		self.editempty = True
		if Main.board.edit:
			action.set_active(False)
		else:
			action.set_active(True)

	def flip_cb(self, *args):
		"flip board"
		if Main.game.lock.locked():
			return
		Main.board.flip()
	
	# glade handlers
	def on_wm_quit(widget, event):
		Main.gui.quit_cb()

	def on_button_begin(widget):
		Main.game.goto_begin()
	def on_button_prev(widget):
		Main.game.goto_prev()
	def on_button_next(widget):
		Main.game.goto_next()
	def on_button_end(widget):
		Main.game.goto_end()
	def on_button_game_prev(widget):
		Main.game.goto_game_prev()
	def on_button_game_next(widget):
		Main.game.goto_game_next()

	def on_button_go(widget):
		Main.game.engines_go()
	def on_button_stop(widget):
		Main.game.engines_stop()


# =========
# P R E F S
# =========

import ConfigParser

class Prefs(ConfigParser.RawConfigParser):
	"""read, manage and save settings

	- the player has a name
	- the game has a gametype, a black and a white player
	  players may be "human" or the path to an engine
	- the look has a scene and a glade file

	this is just the last game played, no checking is done, if
	engine and gametype match; prefs are synced from "New..."

	preferences are saved in a file "prefs" in
	$XDG_CONFIG_HOME/capers or in
	$HOME/.config/capers or in $PWD
	"""

	def pmkdir(self, newdir):
		"works like <mkdir -p>"
		if os.path.isdir(newdir):
			return
		else:
			head, tail = os.path.split(newdir)
			if head and not os.path.isdir(head):
				self.pmkdir(head)
			if tail:
				os.mkdir(newdir)

	def find(self):
		"find or invent the preferences file, return filename"
		prefsdir = os.getenv('XDG_CONFIG_HOME')
		if not prefsdir:
			prefsdir = os.getenv('HOME')
			if prefsdir:
				prefsdir = os.path.join(prefsdir, '.config')
				prefsdir = os.path.join(prefsdir, 'capers')
			else:
				prefsdir = os.getcwd()
		self.pmkdir(prefsdir)
		return os.path.join(prefsdir, 'prefs')

	def save(self):
		"save preferences to default location"
		assert self.prefsfile
		file = open(self.prefsfile, 'w')
		self.write(file)
		file.close

	def __init__(self):
		"load settings, make defaults"
		# not a new style class
		#super(Prefs, self).__init__()
		ConfigParser.RawConfigParser.__init__(self)

		self.prefsfile = self.find()
		self.read(self.prefsfile)
		# installed dir
		cwd = sys.path[0].rstrip("/bin")

		# player
		username = False
		try:
			username = self.get('player', 'name')
		except ConfigParser.NoSectionError:
			self.add_section('player')
		except ConfigParser.NoOptionError:
			pass
		if not username:
			username = os.getenv('LOGNAME')
			if not username:
				username = os.getenv('USERNAME')
			if not username:
				username = 'Player'
			self.set('player', 'name', username)

		# paths
		libdir = False
		try:
			libdir = self.get('paths', 'engines')
		except ConfigParser.NoSectionError:
			self.add_section('paths')
		except ConfigParser.NoOptionError:
			pass
		if not libdir or not os.path.isdir(libdir):
			libdir = os.path.join(cwd, 'lib')
			#self.pmkdir(libdir)
			self.set('paths', 'engines', libdir)
		opendir = False
		try:
			opendir = self.get('paths', 'opengame')
		except ConfigParser.NoSectionError:
			self.add_section('paths')
		except ConfigParser.NoOptionError:
			pass
		if not opendir or not os.path.isdir(opendir):
			opendir = os.path.join(cwd, 'games')
			self.set('paths', 'opengame', opendir)

		savedir = False
		try:
			savedir = self.get('paths', 'savegame')
		except ConfigParser.NoSectionError:
			self.add_section('paths')
		except ConfigParser.NoOptionError:
			pass
		if not savedir or not os.path.isdir(savedir):
			savedir = os.getenv('XDG_DATA_HOME')
			if savedir and os.path.isdir(savedir):
				savedir = os.path.join(savedir, 'capers')
				self.pmkdir(savedir)
			else:
				savedir = os.getenv('HOME')
		assert(savedir)
		self.set('paths', 'savegame', savedir)

		# engines
		enginefile = False
		try:
			enginefile = self.get('engines', 'default')
		except ConfigParser.NoSectionError:
			self.add_section('engines')
		except ConfigParser.NoOptionError:
			pass
		if not enginefile or not os.path.isfile(enginefile):
			enginefile = os.path.join(libdir, 'simplech')
			if os.name == 'nt':
				enginefile = enginefile + '.dll'
			else:
				enginefile = enginefile + '.so'
			if not os.access(enginefile, os.F_OK | os.R_OK):
				Fatal('Default checkers engine not found:\n\n'
				+ enginefile)
			self.set('engines', 'default', enginefile)

		maxtime = 2
		try:
			maxtime = self.getint('engines', 'maxtime')
		except ConfigParser.NoSectionError:
			self.add_section('engines')
			self.set('engines', 'maxtime', 2)
		except ConfigParser.NoOptionError:
			self.set('engines', 'maxtime', 2)
		if maxtime < 1:
			self.set('engines', 'maxtime', 1)

		# game
		gametype = False
		try:
			gametype = self.getint('game', 'type')
		except ConfigParser.NoSectionError:
			self.add_section('game')
		except ConfigParser.NoOptionError:
			pass
		if not gametype or gametype not in (Main.game.INTERNL,
			Main.game.ENGLISH, Main.game.ITALIAN,
			Main.game.RUSSIAN, Main.game.MAFIERZ):
			gametype = Main.game.ENGLISH
			self.set('game', 'type', gametype)

		black = False
		try:
			black = self.get('game', 'black')
		except ConfigParser.NoSectionError:
			self.add_section('game')
			self.set('game', 'black', 'human')
		except ConfigParser.NoOptionError:
			self.set('game', 'black', 'human')
		black = self.get('game', 'black')
		if black != 'human' and not os.access(black, os.F_OK | os.R_OK):
			self.set('game', 'black', 'human')

		white = False
		try:
			white = self.get('game', 'white')
		except ConfigParser.NoSectionError:
			self.add_section('game')
			self.set('game', 'white', self.get('engines', 'default'))
		except ConfigParser.NoOptionError:
			self.set('game', 'white', self.get('engines', 'default'))
		white = self.get('game', 'white')
		if white != 'human' and not os.access(white, os.F_OK | os.R_OK):
			self.set('game', 'white', 'human')

		timeout = 500
		try:
			timeout = self.getint('game', 'timeout')
		except ConfigParser.NoSectionError:
			self.add_section('game')
			self.set('game', 'timeout', 500)
		except ConfigParser.NoOptionError:
			self.set('game', 'timeout', 500)
		if timeout < 100:
			self.set('game', 'timeout', 100)

		# look
		scenefile = False
		try:
			scenefile = self.get('look', 'scene')
		except ConfigParser.NoSectionError:
			self.add_section('look')
		except ConfigParser.NoOptionError:
			pass
		if not scenefile or not os.path.isfile(scenefile):
			scenefile = os.path.join(cwd, 'share', 'scene.xpm')
			if not os.access(scenefile, os.F_OK | os.R_OK):
				Fatal('Scene pixmap not found:\n\n'
				+ scenefile)
			self.set('look', 'scene', scenefile)

		gladefile = False
		try:
			gladefile = self.get('look', 'glade')
		except ConfigParser.NoSectionError:
			self.add_section('look')
		except ConfigParser.NoOptionError:
			pass
		if not gladefile or not os.path.isfile(gladefile):
			gladefile = os.path.join(cwd, 'share', 'capers.glade')
			if not os.access(gladefile, os.F_OK | os.R_OK):
				Fatal('User interface description not found:\n\n'
				+ gladefile)
			self.set('look', 'glade', gladefile)

		self.save()


# =======
# M A I N
# =======

class Fatal(gtk.Window):
	"the program cannot continue, display dialog telling the reason"
	def __init__(self, text):
		gobject.GObject.__init__(self)
		message = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
			gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, text)
		response = message.run()
		message.destroy()
		sys.exit(1)

class Main:
	"""create instances of the classes, map these to Main namespace

	Position(), Game(), Book(), Prefs(), Players(), GladeGui(),
	Feedback(), BookView(), CheckerBoard()

	is this a singleton?
	"""
	def __init__(self):
		try:
			gobject.threads_init()
		except:
			Fatal('No threads in pygtk')
		Main.pos = Position()
		Main.game = Game()
		Main.book = Book()
		Main.prefs = Prefs()
		Main.players = Players()
		Main.gui = GladeGui(Main.prefs.get('look', 'glade'))
		Main.feedback = Main.gui['Feedback']
		Main.feedback.prepare()
		Main.bookview = Main.gui['Book']
		Main.bookview.open(Main.book)
		Main.board = Main.gui['Board']
		if len(sys.argv) > 1:
			fn = sys.argv[-1]
			try:
				f = open(fn, 'r')
			except:
				Fatal('No such file: %s' % fn)
			pdn = Pdn(f, fn)
			pdn.parse()
			f.close()
			del pdn
		else:
			Main.game.new()
		gtk.main()
