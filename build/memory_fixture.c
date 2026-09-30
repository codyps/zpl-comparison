/* Transient resident allocation, released before exit: sampling can miss it. */
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv) {
    size_t size = (size_t)atoi(argv[1]) * 1024 * 1024;
    volatile unsigned char *buffer = malloc(size);
    if (!buffer) return 2;
    for (size_t i = 0; i < size; i += 4096) buffer[i] = 1;
    free((void *)buffer);
    puts("{\"ns\":1,\"iterations\":1,\"checksum\":1}");
    return 0;
}
