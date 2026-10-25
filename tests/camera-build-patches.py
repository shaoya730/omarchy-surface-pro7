from pathlib import Path
import hashlib
import os
import subprocess as sp
import sys
import tempfile

adapter=Path(sys.argv[1]).resolve()
checkout=Path(sys.argv[2]).resolve()
script=(adapter/'camera/build.sh').read_text()
block=script[script.index('for camera_patch in '):script.index('sensor_dir=')]
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp)
    for name in ['ipu-isys-video.c','ipu-isys.c']:
        relative='linux-6.19.8/drivers/media/pci/intel/'+name
        p=root/relative
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(sp.check_output(['git','-C',str(checkout),'show','HEAD:'+relative]))
    snapshots=[]
    for _ in range(2):
        env=dict(os.environ,source_dir=str(root),script_dir=str(adapter/'camera'))
        sp.run(['bash','-euc',block],env=env,check=True)
        snapshots.append({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.c')})
    assert snapshots[0]==snapshots[1], 'A repeated build changed already patched source'
print('PASS: both camera patches apply once and remain identical on a repeat build')
