from pathlib import Path
import re
import subprocess
import sys
import tempfile

source=Path(sys.argv[1]).read_text()
function=source[source.index('static pid_t start_capture('):source.index('\nstatic void stop_capture(')]
harness=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <fcntl.h>
#include <unistd.h>
static void die(const char *m) { exit(3); }
static int fake_pipe(int *p, int f) { p[0]=10;p[1]=11;return 0; }
static int fake_close(int f) { return 0; }
static int fake_dup(int a,int b) { return b; }
static int fake_fork(void) { return 0; }
static int fake_execl(const char *path,const char *arg,...) {
  va_list v;va_start(v,arg);const char *s=arg;
  while(s){puts(s);s=va_arg(v,const char*);}va_end(v);exit(0);
}
#define pipe2 fake_pipe
#define close fake_close
#define dup2 fake_dup
#define fork fake_fork
#define execl fake_execl
'''
with tempfile.TemporaryDirectory() as t:
    p=Path(t)
    (p/'test.c').write_text(harness+function+'\nint main(int argc,char **argv){int fd;start_capture(&fd,atoi(argv[1]));}\n')
    subprocess.run(['cc',str(p/'test.c'),'-o',str(p/'test')],check=True)
    for rear,sensor in [(0,'I2C2.CAMF'),(1,'I2C3.CAMR')]:
        args=subprocess.check_output([str(p/'test'),str(rear)],text=True).splitlines()
        names=[x for x in args if x.startswith('camera-name=')]
        assert len(names)==1 and sensor in names[0],f'Wrong sensor selection: {names}, expected {sensor}'
print('Both real start_capture branches select their exact physical camera.')
