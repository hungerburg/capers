# cake - a checkers engine
# Copyright (C) 2000,2005 by Martin Fierz

# Makefile for use with gcc
# and install target
# init: Peter Chiochetti Sat Jun 24 13:47:15 MEST 2000
# book: -"- Mit Feb 23 14:42:43 CET 2005

VERSION=1.22

### system configuration
# this defaults to little endian (intel) hardware if you are
# on a big endian machine (eg. ppc, sparc), uncomment XDEFS

### install directories for binary and database

DESTDIR = /usr/local
BIN_DIR = $(DESTDIR)/bin
DB___DIR = $(DESTDIR)/lib
MAN_DIR = $(DESTDIR)/man/man6

### compiler, debug, optimization, byteorder

CC = gcc
DEFS = -DDBINI=\"$(DB___DIR)/db.ini\" -DXBOOK=\"$(DB___DIR)/xbook.bin\" \
	-DSYS_UNIX -DVERSION=$(VERSION)
#XDEFS = -DBIGEND

#CFLAGS = -g -Wall $(DEFS) $(XDEFS)
CFLAGS = -O3 $(DEFS) $(XDEFS)

LIB_CFLAGS=-fPIC
LIB_LDFLAGS=-shared -Wl,-soname,$@

### install program

MAKEDIR = /usr/bin/install -d
INSTALL = /usr/bin/install -c -s
INSTALLDATA = /usr/bin/install -c -m 644

#### end of configuration


OBJECTS = cakepp.o db.o movegen.o book.o dll.o

all: cake.so

.c.o:
	$(CC) $(CFLAGS) $(LIB_CFLAGS) -o $@ -c $<

cake.so: $(OBJECTS)
	$(CC) $(LDFLAGS) $(LIB_LDFLAGS) -o $@ $^

clean:
	rm -f *.o *~ *core *.BAK *.txt sys.db.ini tags

tags: *.c
	vim-ctags *

install: all
	@sed -e "s:db:$(DB___DIR)/db:g" db.ini >sys.db.ini
	$(INSTALL) cake $(BIN_DIR)/cake
	$(MAKEDIR) $(DB___DIR)
	$(INSTALLDATA) sys.db.ini $(DB___DIR)/db.ini
	$(INSTALLDATA) db4 $(DB___DIR)/db4
	$(INSTALLDATA) db4.idx $(DB___DIR)/db4.idx
	$(INSTALLDATA) xbook.bin $(DB___DIR)/xbook.bin
	$(MAKEDIR) $(MAN_DIR)

### dist package

DISTFILES = Makefile README COPYING db.ini db4 db4.idx \
	dll.c cakepp.c cakepp.h consts.h db.c db.h \
	movegen.c movegen.h structs.h switches.h \
	book.c book.h xbook.bin cake.so \
	cake.dev cake.dll

dist: clean all
	strip cake.so
	@sh -c 'cd ..; \
	tar cvfz cake-$(VERSION).tar.gz \
	`for i in $(DISTFILES); do echo cake-$(VERSION)/$$i; done`'
