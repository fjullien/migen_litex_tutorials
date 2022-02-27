#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <math.h>

#include <SDL2/SDL.h>

#include <sys/socket.h>
#include <arpa/inet.h>

struct sockaddr_in server, cliaddr;
int sock;

#define WINDOW_SIZE_X   320
#define WINDOW_SIZE_Y   240
#define LED_SIZE        15
#define RING_RADIUS     80.0

void fill_circle(SDL_Surface *surface, int cx, int cy, int radius, Uint32 pixel)
{
    static const int BPP = 4;

    double r = (double)radius;

    for (double dy = 1; dy <= r; dy += 1.0)
    {
        // This loop is unrolled a bit, only iterating through half of the
        // height of the circle.  The result is used to draw a scan line and
        // its mirror image below it.

        // The following formula has been simplified from our original.  We
        // are using half of the width of the circle because we are provided
        // with a center and we need left/right coordinates.

        double dx = floor(sqrt((2.0 * r * dy) - (dy * dy)));
        int x = cx - dx;

        // Grab a pointer to the left-most pixel for each half of the circle
        Uint8 *target_pixel_a = (Uint8 *)surface->pixels + ((int)(cy + r - dy)) * surface->pitch + x * BPP;
        Uint8 *target_pixel_b = (Uint8 *)surface->pixels + ((int)(cy - r + dy)) * surface->pitch + x * BPP;

        for (; x <= cx + dx; x++)
        {
            *(Uint32 *)target_pixel_a = pixel;
            *(Uint32 *)target_pixel_b = pixel;
            target_pixel_a += BPP;
            target_pixel_b += BPP;
        }
    }
}

void redraw_ring(SDL_Surface *windowSurface, unsigned int *data, int x, int y, int led_size, float radius)
{
    int i = 0;
    for (float theta = 0; theta < (3.14159 * 2); theta += (2 * 3.14159 / 12)) {
        int new_x = (int)((float)x + (radius * cos ( theta )));
        int new_y = (int)((float)y - (radius * sin ( theta )));

        if (i < 12)
            fill_circle(windowSurface, new_x, new_y, led_size, data[i] == 0 ? 0x00404040 : data[i]);
        i++;
    }
}

int main(int argc, char *argv[])
{
    //Main loop flag
    bool b_Quit = false;
    //Event handler 
    SDL_Event ev;
    //SDL window
    SDL_Window *window = NULL;

    SDL_Surface *windowSurface;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        printf("Error while creating socket\n");
        return -1;
    }

	server.sin_addr.s_addr = htonl(INADDR_ANY);//inet_addr("127.0.0.1");
	server.sin_family = AF_INET;
	server.sin_port = htons( 8888 );

    struct timeval read_timeout;
    read_timeout.tv_sec = 0;
    read_timeout.tv_usec = 10;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &read_timeout, sizeof(read_timeout));

    if ( bind( sock, (struct sockaddr *)&server, sizeof(server)) )
    {
        printf( "bind() error\n" );
        return -1;
    }

    if (SDL_Init(SDL_INIT_VIDEO) < 0)
    {
        printf("Video Initialisation Error: %s\n", SDL_GetError());
    }
    else
    {
        window = SDL_CreateWindow("LED Ring", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, WINDOW_SIZE_X, WINDOW_SIZE_Y, SDL_WINDOW_SHOWN);
        if (window == NULL)
        {
            printf("Window Creation Error: %s\n", SDL_GetError());
        }
        else
        {
            windowSurface = SDL_GetWindowSurface(window);

            unsigned int data[12] = {
                0x00404040,
                0x00404040,
                0x00404040,
                0x00404040,
                0x00404040,
                0x00404040,
                0x00404040,
                0x00404040,
                0x00404040,
                0x00404040,
                0x00404040,
                0x00404040,
            };

            redraw_ring(windowSurface, data, WINDOW_SIZE_X / 2, WINDOW_SIZE_Y / 2, LED_SIZE, RING_RADIUS);

            //Main loop
            while (!b_Quit)
            {
                   int len = sizeof(cliaddr);
                    int ret = recvfrom(sock, data, sizeof(data), 0, ( struct sockaddr *)&cliaddr, (socklen_t*)&len);
                    if( ret > 0 )
                    {
                        redraw_ring(windowSurface, data, WINDOW_SIZE_X / 2, WINDOW_SIZE_Y / 2, LED_SIZE, RING_RADIUS);
                    }

                //Event Loop
                while (SDL_PollEvent(&ev) != 0)
                {
 
                    //Quit Event
                    if (ev.type == SDL_QUIT)
                    {
                        b_Quit = true;
                    }
                }

                SDL_UpdateWindowSurface(window);
            }

        }
    }

    SDL_DestroyWindow(window);
    SDL_Quit();

    return 0;
}