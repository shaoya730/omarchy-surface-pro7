from pathlib import Path
import subprocess
import sys
import tempfile

source=Path(sys.argv[1]).read_text()
start=source.index('\trval = video_register_device')
end=source.index('\n\tif (av->debug_link_only',start)
block=source[start:end]
code=r'''
#include <assert.h>
#include <errno.h>
static int video_nr_base=-1, requested, allocated, result, removed;
struct video_device { int num; };
struct video { struct video_device vdev; };
#define VFL_TYPE_VIDEO 0
static int video_register_device_no_warn(struct video_device *v, int type, int nr) {
    requested=nr; v->num=allocated; return result;
}
static void video_unregister_device(struct video_device *v) { removed++; }
static int register_test(struct video *av) {
    int rval;
'''+block+r'''
    return 0;
out_media_entity_cleanup:
    video_unregister_device(&av->vdev);
    return rval;
}
int main(void) {
    struct video av={0};
    allocated=0; assert(register_test(&av)==0 && requested==-1);
    video_nr_base=64; allocated=64;
    assert(register_test(&av)==0 && requested==64);
    allocated=118; assert(register_test(&av)==0);
    allocated=2; removed=0;
    assert(register_test(&av)==-ENFILE && removed==1);
    allocated=0; video_nr_base=-2; removed=0;
    assert(register_test(&av)==-ENFILE && removed==1);
    video_nr_base=256; removed=0;
    assert(register_test(&av)==-ENFILE && removed==1);
    video_nr_base=64;
    result=-ENOMEM; removed=0;
    assert(register_test(&av)==-ENOMEM && removed==1);
}
'''
with tempfile.TemporaryDirectory() as d:
    c=Path(d)/'test.c'; exe=Path(d)/'test'
    c.write_text(code)
    subprocess.run(['cc','-Wall',str(c),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('PASS: upstream allocation, configured range, wrap rejection, registration error')
