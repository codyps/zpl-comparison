/* Launch from a small, freshly exec'd process so Python's pre-exec RSS is
 * excluded from the adapter's wait4 high-water mark. stdout/stderr pass through. */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc < 3) return 2;
    pid_t child = fork();
    if (child < 0) { perror("fork"); return 2; }
    if (child == 0) {
        execvp(argv[2], argv + 2);
        perror("execvp");
        _exit(127);
    }
    int status;
    struct rusage usage;
    while (wait4(child, &status, 0, &usage) < 0) {
        if (errno != EINTR) { perror("wait4"); return 2; }
    }
    FILE *out = fopen(argv[1], "w");
    if (!out) { perror("memory evidence"); return 2; }
#ifdef __APPLE__
    long long bytes = usage.ru_maxrss;
#else
    long long bytes = (long long)usage.ru_maxrss * 1024;
#endif
    fprintf(out, "{\"peak_rss_bytes\":%lld}\n", bytes);
    if (fclose(out)) return 2;
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}
