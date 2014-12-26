int32 booklookup(struct pos *p, int color);
int   initbook(char fn[1024]);


typedef struct
	{
	int32 black;
	int32 white;
	int32 kings;
	int32 move;
	int color;
	} BOOK_ENTRY;
