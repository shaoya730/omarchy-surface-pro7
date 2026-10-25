from pathlib import Path
import subprocess as sp
import sys
import tempfile

source=Path(sys.argv[1]).read_text()
start=source.find('\t\tif (vep.base.port < 32 &&')
block=''
if start>=0:
    end=source.index('\n\n',start)
    block=source[start:end].replace('continue;','return 1;')
code=r'''
#include <assert.h>
#include <stdint.h>
static uint32_t disabled_csi2_ports;
#define BIT(n) (1UL << (n))
#define dev_info(...) ((void)0)
static int skip(unsigned int port) {
    struct { struct { unsigned int port; } base; } vep = { { port } };
'''+block+r'''
    return 0;
}
int main(void) {
    for (unsigned int i=0;i<32;i++) assert(skip(i)==0);
    disabled_csi2_ports=64;
    assert(skip(6)==1);
    assert(skip(3)==0 && skip(7)==0);
    assert(skip(32)==0 && skip(UINT32_MAX)==0);
}
'''
with tempfile.TemporaryDirectory() as temp:
    p=Path(temp)
    (p/'test.c').write_text(code)
    sp.run(['cc','-fsanitize=undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    sp.run([str(p/'test')],check=True)
print('PASS: default discovery, explicit IR exclusion, RGB preserved, safe bit bounds')
