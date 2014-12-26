/* structs.h: data structures for cake++ */

/*definitions for platform-independence*/
#define int32 unsigned int
#define int16 unsigned short
#define int8  unsigned char
#define sint32 signed int
#define sint16 signed short
#define sint8  signed char

struct move
	{
   int32 bm;
   int32 bk;
   int32 wm;
   int32 wk;
   int32 info;
   };

struct pos
	{
   int32 bm;
   int32 bk;
   int32 wm;
   int32 wk;
   };

struct hashentry
	{
   int32  lock;
   int32  best;
   sint16 value;
   int16  info;
   };


