#!/usr/bin/env python3
# Copyright 2024-present the vsag project
# SPDX-License-Identifier: Apache-2.0
"""Whole-vector updates must work even when coordinate zero is unchanged."""
import csv
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from edge_restoration_probe import build_control, run


def records(path, rows):
    path.write_bytes(b''.join(struct.pack('<I',len(r))+struct.pack('<'+'f'*len(r),*r) for r in rows))


def main():
    route,slot=map(lambda p:str(Path(p).resolve()),sys.argv[1:3])
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);source=root/'initial';replacement=root/'replacement.fvecs'
        vectors=[[0.,0.,0.],[0.,1.,0.],[0.,4.,0.]];links=[[1,2],[0,2],[0,1]]
        payload=16+3*(16+3*4)+8*sum(map(len,links))
        data=b'VSAGLT01'+struct.pack('<7Q',2,3,3,payload,2,2,3)+struct.pack('<3q',0,1,2)
        data+=struct.pack('<9f',*(x for row in vectors for x in row))
        data+=b''.join(struct.pack('<Q',len(r))+struct.pack('<'+'Q'*len(r),*r) for r in links)
        source.write_bytes(data)
        records(root/'queries.fvecs',[[0.,0.,0.]])
        (root/'groundtruth.ivecs').write_bytes(struct.pack('<ii',1,0))
        (root/'changed-groundtruth.ivecs').write_bytes(struct.pack('<ii',1,1))
        records(replacement,[[0.,2.,1.]])
        output=root/'native.csv'
        command=[route,'--replacement-update',str(source),str(root),str(output),'1','trace']
        done=subprocess.run(command,capture_output=True,text=True);assert done.returncode==0,done.stderr
        neighbors=list(csv.DictReader(Path(str(output)+'.neighbors.csv').open()))
        assert [(r['phase'],r['id'],float.fromhex(r['distance'])) for r in neighbors]==[('initial','0',0.),('changed','1',1.)]
        assert next(csv.DictReader(output.open()))['roundtrip']=='1'
        edges=root/'edges.u32';edges.write_bytes(b''.join(struct.pack('<III',2,*r) for r in links))
        fd,receipt=build_control(source,edges,1,1,replacement)
        try:
            changed=os.pread(fd,len(data),0)
            assert changed[:88]==data[:88] and changed[100:]==data[100:]
            assert struct.unpack_from('<3f',changed,88)==(0.,2.,1.)
            assert receipt['replacement_vectors_sha256']
        finally:os.close(fd)
        (root/'groundtruth.ivecs').write_bytes(struct.pack('<ii',1,1))
        run(source,edges,root,root/'control.csv',1,1,slot,replacement)
        states=list(csv.DictReader((root/'control.csv').open()));assert all(r['hits']=='1' for r in states)
        for i,rows in enumerate([[[0.,0.,0.]], [[-0.,0.,0.]], [[0.,float('nan'),1.]], [[0.,float('inf'),1.]], [[0.,2.]], [[0.,2.,1.],[0.,3.,1.]]]):
            records(replacement,rows)
            cmd=command.copy();cmd[4]=str(root/('bad-'+str(i)+'.csv'))
            assert subprocess.run(cmd,capture_output=True).returncode!=0
            try:
                fd,_=build_control(source,edges,1,1,replacement);os.close(fd);raise AssertionError('invalid replacement accepted')
            except ValueError:pass
        records(replacement,[[0.,2.,1.]])
        replacement.write_bytes(replacement.read_bytes()[:-1])
        cmd=command.copy();cmd[4]=str(root/'truncated.csv');assert subprocess.run(cmd,capture_output=True).returncode!=0
        replacement.unlink();cmd[4]=str(root/'missing.csv');assert subprocess.run(cmd,capture_output=True).returncode!=0
        assert source.read_bytes()==data
    print('Replacement update fixtures passed')


if __name__=='__main__':main()
