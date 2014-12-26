#
# cliche - command line interface checkers
# Makefile for gcc
# 1.1 Mit Jan 15 20:21:12 CET 2003
# 1.2 Sam Jun  1 17:00:20 CEST 2013
# 1.3 Don Dez 25 12:28:57 CET 2014
#
VERSION=1.3

# install paths
DESTDIR=/usr/local
BIN_DIR=$(DESTDIR)/bin
LIB_DIR=$(DESTDIR)/lib

# installed files
BIN=cliche
LIB=dama.so simplech.so

# compiler flags
CFLAGS=-g -O3
LDFLAGS=-g
APP_CFLAGS=-rdynamic -DLIB_DIR=\"$(LIB_DIR)\"
APP_LDFLAGS=-ldl
LIB_CFLAGS=-fPIC
LIB_LDFLAGS=-shared -Wl,-soname,$@

# TARGETS
all: $(LIB) $(BIN)

dummy.o: dummy.c
	$(CC) $(CFLAGS) $(LIB_CFLAGS) -o $@ -c $<
dama.o: dama.c
	$(CC) $(CFLAGS) $(LIB_CFLAGS) -o $@ -c $<
simplech.o: simplech.c
	$(CC) $(CFLAGS) $(LIB_CFLAGS) -o $@ -c $<
pdnplay.o: pdnplay.c
	$(CC) $(CFLAGS) $(LIB_CFLAGS) -o $@ -c $<
cliche.o: cliche.c
	$(CC) -Wall $(CFLAGS) $(APP_CFLAGS) -o $@ -c $<

dummy.so: dummy.o
	$(CC) $(LDFLAGS) -o $@ $< $(LIB_LDFLAGS)
dama.so: dama.o
	$(CC) $(LDFLAGS) -o $@ $< $(LIB_LDFLAGS)
simplech.so: simplech.o
	$(CC) $(LDFLAGS) -o $@ $< $(LIB_LDFLAGS)
cliche: cliche.o
	$(CC) $(LDFLAGS) -o $@ $< $(APP_LDFLAGS)

install: all
	install -d $(BIN_DIR) $(LIB_DIR)
	install -s $(BIN) $(BIN_DIR)
	install -s $(LIB) $(LIB_DIR)
clean:
	rm -f *.o *.out *~ tags *.pdn *-stamp
	rm -rf tmp
	which dh_clean && dh_clean
dist: clean
	(cd .. && cp -a cliche cliche-$(VERSION) \
	&& tar cvfz cliche-$(VERSION).tar.gz cliche-$(VERSION) \
	&& rm -rf cliche-$(VERSION) )

# DEBIAN PACKAGE
dpkg: clean
	fakeroot debian/rules binary
dpkg2: clean
	dpkg-buildpackage -rfakeroot -us -uc

# FUN TARGETS
profile: all
	@mkdir -p tmp
	LD_LIBRARY_PATH=/usr/lib/debug \
	LD_PROFILE_OUTPUT=tmp \
	LD_PROFILE=dama.so \
	./cliche dama
	@[ -f ./tmp/dama.so.profile ] \
	&& echo "Profile data in ./tmp." \
	|| echo "No profile data created (Old glibc?)."

memusage: all
	LD_PRELOAD=/lib/libmemusage.so ./cliche 

.PHONY: install clean dist dpkg-all dpkg-bin profile
