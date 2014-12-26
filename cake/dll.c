/*  cake++ - a checkers engine
 *
 *  Copyright (C) 2000-2005 by Martin Fierz
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 *  contact: nospam1@fierz.ch, pch@myzel.net
 */

/*
    version history

    1.22  (24th dec 2014)
    --> do not use endgame database on 64bit target

    1.21  (10th april 2005)
    --> added this file, dll.c (pch)

*/


/* cake CB-api dll interface */


#include <stdio.h>
#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include "structs.h"		/* data structures  */
#include "cakepp.h"		/* function prototypes  */
#include "consts.h"		/* constants  */
#include "movegen.h"		/* makecapturelist ...  */
#include "switches.h"		/* SYS_UNIX  */

#ifdef SYS_WINDOWS
#include <windows.h>
#endif

#ifdef SYS_UNIX
#define WINAPI			// empty on *nix
#endif

/* board values */
#define OCCUPIED 0		// un_occupied dark squares
#define WHITE 1
#define BLACK 2
#define MAN 4
#define KING 8
#define FREE 16			// the light squares, always _free
#define CHANGECOLOR 3

/* getmove return values */
#define DRAW 0
#define WIN 1
#define LOSS 2
#define UNKNOWN 3

/*----------> structure definitions  */

/* coordinate structure for board coordinates */
typedef struct
{
  int x;
  int y;
} coor;

/* all the information you need about a move */
typedef struct
{
  int jumps;			/* what it says */
  int newpiece;			/* what type of piece appears on to */
  int oldpiece;			/* what disappears on from */
  coor from, to;		/* coordinates of the piece - in 8x8 notation! */
  coor path[12];		/* intermediate path coordinates of the moving piece */
  coor del[12];			/* squares whose pieces are deleted after the move */
  int delpiece[12];		/* what is on these squares */
} CBmove;


/*----------> supportive stuff */

int init = 0;
int logging = 2;		/* cake_getmove()  */

int
initdll ()
{
  initcake (logging);
  return 1;
}

/* set bitboard from an 8x8 square  */
static void
boardtobitboard (int b[8][8], struct pos *position)
{
  int i, board[32];

  board[0] = b[0][0];
  board[1] = b[2][0];
  board[2] = b[4][0];
  board[3] = b[6][0];
  board[4] = b[1][1];
  board[5] = b[3][1];
  board[6] = b[5][1];
  board[7] = b[7][1];
  board[8] = b[0][2];
  board[9] = b[2][2];
  board[10] = b[4][2];
  board[11] = b[6][2];
  board[12] = b[1][3];
  board[13] = b[3][3];
  board[14] = b[5][3];
  board[15] = b[7][3];
  board[16] = b[0][4];
  board[17] = b[2][4];
  board[18] = b[4][4];
  board[19] = b[6][4];
  board[20] = b[1][5];
  board[21] = b[3][5];
  board[22] = b[5][5];
  board[23] = b[7][5];
  board[24] = b[0][6];
  board[25] = b[2][6];
  board[26] = b[4][6];
  board[27] = b[6][6];
  board[28] = b[1][7];
  board[29] = b[3][7];
  board[30] = b[5][7];
  board[31] = b[7][7];

  (*position).bm = 0;
  (*position).bk = 0;
  (*position).wm = 0;
  (*position).wk = 0;

  for (i = 0; i < 32; i++)
    {
      switch (board[i])
	{
	case BLACK | MAN:
	  (*position).bm = (*position).bm | (1 << i);
	  break;
	case BLACK | KING:
	  (*position).bk = (*position).bk | (1 << i);
	  break;
	case WHITE | MAN:
	  (*position).wm = (*position).wm | (1 << i);
	  break;
	case WHITE | KING:
	  (*position).wk = (*position).wk | (1 << i);
	  break;
	}
    }
}

/*----------> dll interface */

#ifdef SYS_WINDOWS
BOOL WINAPI
DllEntryPoint (HANDLE hDLL, DWORD dwReason, LPVOID lpReserved)
{
  /* in a dll you used to have LibMain instead of WinMain in
   * windows programs, or main in normal C programs win32
   * replaces LibMain with DllEntryPoint. */

  switch (dwReason)
    {
    case DLL_PROCESS_ATTACH:
      /* dll loaded. put initializations here! */
      if (!init)
	init = initdll ();
      break;
    case DLL_PROCESS_DETACH:
      /* program is unloading dll. put clean up here! */
      break;
    case DLL_THREAD_ATTACH:
      if (!init)
	init = initdll ();
      break;
    case DLL_THREAD_DETACH:
      break;
    default:
      break;
    }
  return TRUE;
}
#endif // SYS_WINDOWS

/* answer to commands sent by CheckerBoard */
int WINAPI
enginecommand (char str[256], char reply[256])
{

  char command[256], param1[256], param2[256];

  if (!init)
    init = initdll ();

  sscanf (str, "%s %s %s", command, param1, param2);

  // check for command keywords 
  if (strcmp (command, "name") == 0)
    {
      sprintf (reply, "Cake %.2f", VERSION);
      return 1;
    }

  if (strcmp (command, "about") == 0)
    {
      sprintf (reply, "Cake - open source checkers program");
      return 1;
    }

  if (strcmp (command, "help") == 0)
    {
      sprintf (reply, "---");
      return 1;
    }

  if (strcmp (command, "set") == 0)
    {
      if (strcmp (param1, "hashsize") == 0)
	{
	  return 0;
	}
      if (strcmp (param1, "book") == 0)
	{
	  return 0;
	}
    }

  if (strcmp (command, "get") == 0)
    {
      if (strcmp (param1, "hashsize") == 0)
	{
	  return 0;
	}
      if (strcmp (param1, "book") == 0)
	{
	  return 0;
	}
      if (strcmp (param1, "protocolversion") == 0)
	{
	  sprintf (reply, "2");
	  return 1;
	}
      if (strcmp (param1, "gametype") == 0)
	{
	  sprintf (reply, "21");
	  return 1;
	}
    }
  return 0;
}

/* islegal tells CheckerBoard if a move the user wants to make
 * is legal or not. to check this, we generate a movelist and
 * compare the moves in the movelist to the move the user
 * wants to make with from&to */

/* turns square number n into a coordinate for checkerboard */
coor
numbertocoor (int n)
{
  coor c;
  switch (n)
    {
    case 4:
      c.x = 0;
      c.y = 0;
      break;
    case 3:
      c.x = 2;
      c.y = 0;
      break;
    case 2:
      c.x = 4;
      c.y = 0;
      break;
    case 1:
      c.x = 6;
      c.y = 0;
      break;
    case 8:
      c.x = 1;
      c.y = 1;
      break;
    case 7:
      c.x = 3;
      c.y = 1;
      break;
    case 6:
      c.x = 5;
      c.y = 1;
      break;
    case 5:
      c.x = 7;
      c.y = 1;
      break;
    case 12:
      c.x = 0;
      c.y = 2;
      break;
    case 11:
      c.x = 2;
      c.y = 2;
      break;
    case 10:
      c.x = 4;
      c.y = 2;
      break;
    case 9:
      c.x = 6;
      c.y = 2;
      break;
    case 16:
      c.x = 1;
      c.y = 3;
      break;
    case 15:
      c.x = 3;
      c.y = 3;
      break;
    case 14:
      c.x = 5;
      c.y = 3;
      break;
    case 13:
      c.x = 7;
      c.y = 3;
      break;
    case 20:
      c.x = 0;
      c.y = 4;
      break;
    case 19:
      c.x = 2;
      c.y = 4;
      break;
    case 18:
      c.x = 4;
      c.y = 4;
      break;
    case 17:
      c.x = 6;
      c.y = 4;
      break;
    case 24:
      c.x = 1;
      c.y = 5;
      break;
    case 23:
      c.x = 3;
      c.y = 5;
      break;
    case 22:
      c.x = 5;
      c.y = 5;
      break;
    case 21:
      c.x = 7;
      c.y = 5;
      break;
    case 28:
      c.x = 0;
      c.y = 6;
      break;
    case 27:
      c.x = 2;
      c.y = 6;
      break;
    case 26:
      c.x = 4;
      c.y = 6;
      break;
    case 25:
      c.x = 6;
      c.y = 6;
      break;
    case 32:
      c.x = 1;
      c.y = 7;
      break;
    case 31:
      c.x = 3;
      c.y = 7;
      break;
    case 30:
      c.x = 5;
      c.y = 7;
      break;
    case 29:
      c.x = 7;
      c.y = 7;
      break;
    }
  return c;
}

/*
char *
binstring (int value)
{
  static char bin[33];
  int i;

  for (i = 0; i < 32; i++)
    {
      if (value & (1 << i))
	bin[i] = '1';
      else
	bin[i] = '0';
    }
  bin[32] = 0x00;

  return (bin);
}
*/

/* fill CBmove struct */
void
movetocbmove (struct pos p, struct move move, CBmove * cbmove, int color,
	      int from, int to)
{
  int jumps = 0;
  static int square[32] = { 4, 3, 2, 1, 8, 7, 6, 5,
    12, 11, 10, 9, 16, 15, 14, 13,
    20, 19, 18, 17, 24, 23, 22, 21,
    28, 27, 26, 25, 32, 31, 30, 29
  };				/* maps bits to checkers notation */
  int i, j, del;

  // from/to?
  cbmove->from = numbertocoor (from);
  cbmove->to = numbertocoor (to);

  // oldpiece?
  if ((color == BLACK && (p.bm & move.bm))
      || (color == WHITE && (p.wm & move.wm)))
    cbmove->oldpiece = (color | MAN);
  else
    cbmove->oldpiece = (color | KING);

  // newpiece?
  if ((color == BLACK && ((p.bm ^ move.bm) & move.bm))
      || (color == WHITE && ((p.wm ^ move.wm) & move.wm)))
    cbmove->newpiece = (color | MAN);
  else
    cbmove->newpiece = (color | KING);

  // jumps?
  if (color == BLACK && move.wk | move.wm)
    jumps = 1;
  if (color == WHITE && move.bk | move.bm)
    jumps = 1;

  if (!jumps)
    {
      cbmove->jumps = 0;
      cbmove->path[0] = numbertocoor (to);
      return;
    }

  // deleted pieces?
  j = 0;
  if (color == BLACK)
    {
      del = move.wm | move.wk;
      for (i = 0; i < 32; i++)
	{
	  if (del & (1 << i))
	    {
	      cbmove->del[j] = numbertocoor (square[i]);
	      if (move.wm & (1 << i))
		cbmove->delpiece[j] = (color | MAN);
	      else
		cbmove->delpiece[j] = (color | KING);
	      j++;
	    }
	}
    }
  else
    {
      del = move.bm | move.bk;
      for (i = 0; i < 32; i++)
	{
	  if (del & (1 << i))
	    {
	      cbmove->del[j] = numbertocoor (square[i]);
	      if (move.bm & (1 << i))
		cbmove->delpiece[j] = (color | MAN);
	      else
		cbmove->delpiece[j] = (color | KING);
	      j++;
	    }
	}
    }
  cbmove->jumps = j;
  for (i = 0; i < j; i++)
    cbmove->path[i] = numbertocoor (to);
}

int WINAPI
islegal (int b[8][8], int color, int from, int to, CBmove * move)
{
  struct move movelist[MAXMOVES];
  int i, n, Lfrom, Lto, found = 0;
  char c, Lstr[256];
  extern struct pos p;		/* global for movelist generation */

  if (!init)
    init = initdll ();

  boardtobitboard (b, &p);

  /* get a movelist  */
  n = makecapturelist (movelist, color, 0);
  if (!n)
    n = makemovelist (movelist, color, 0, 0);

  /* for all moves: convert move to notation and compare  */
  for (i = 0; i < n; i++)
    {
      movetonotation (p, movelist[i], Lstr, color);
      /* Lstr contains something like "11-15" or "15x24"  */
      sscanf (Lstr, "%2i%c%2i", &Lfrom, &c, &Lto);
      if (Lto < 0)
	Lto = -Lto;
      if ((Lfrom == from) && (Lto == to))
	{
	  found = 1;
	  break;
	}
    }
  /* set CBmove to movelist[i], update position */
  if (found)
    movetocbmove (p, movelist[i], move, color, from, to);
  return found;
}


/*
 * cake_getmove is the entry point to cake++
 * - give a pointer to a position and you get the new
 *   position in this structure after cake++ has calculated.
 * - color is BLACK or WHITE and is the side to move.
 * - how is 0 for time-based search and 1 for depth-based
 *   search and 2 for node-based search
 * - maxtime and depthtosearch and maxnodes are used for these
 *   two search modes.
 * - cake++ prints information in str
 * - if playnow is set to a value != 0 cake++ aborts the
 *   search.
 * - if (logging&1) cake++ will write information into
 *   "log.txt"
 *   if(logging&2) cake++ will also print the information to
 *   stdout.
 * - if reset!=0 cake++ will reset hashtables and repetition
 *   checklist
 * int cake_getmove(struct pos *position, int color,
 *                  int how, double maxtime,
 *                  int depthtosearch, int32 maxnodes,
 *                  char str[255], int *playnow,
 *                  int log, int reset)
 *
 * this is not the same as the CB-api call!
 */

int WINAPI
getmove (int b[8][8], int color, double maxtime, char str[255], int *playnow,
	 int info, int unused, CBmove * move)
{
  int value;
  struct pos pp;
  struct pos p;		/* global for movelist generation */
  char c, Lstr[256];
  int Lfrom, Lto;
  struct move m;

  if (!init)
    init = initdll ();

  boardtobitboard (b, &pp);
  value = cake_getmove (&pp, color, 0, maxtime, 9, 10000,
			str, playnow, logging, 0);

  boardtobitboard (b, &p);
  m.bm = pp.bm ^ p.bm;
  m.bk = pp.bk ^ p.bk;
  m.wm = pp.wm ^ p.wm;
  m.wk = pp.wk ^ p.wk;
  movetonotation (p, m, Lstr, color);
  sscanf (Lstr, "%2i%c%2i", &Lfrom, &c, &Lto);
  movetocbmove (p, m, move, color, Lfrom, Lto);

  if (value >= 4999)
    return WIN;
  if (value <= -4999)
    return LOSS;
  return UNKNOWN;
}
