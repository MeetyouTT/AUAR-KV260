"""Decode only non-sensitive Xilinx carrier FRU fields from registered EEPROM."""
import json
from pathlib import Path

assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
dev = Path('/sys/bus/i2c/devices/1-0051')
assert dev.exists() and (dev/'name').read_text().strip() == '24c64'
assert (dev/'driver').resolve().name == 'at24'
ep = dev/'eeprom'
out = {'device':'1-0051','driver':'at24','serial_or_mac_emitted':False,'hardware_writes':0,'bus_scan':False}
with ep.open('rb') as f:
    hdr = f.read(8)
    if len(hdr) != 8:
        out['status'] = 'short_common_header'
    elif sum(hdr) % 256:
        out.update(status='invalid_common_header_checksum', header_version=hdr[0]&0x0f)
    elif not hdr[3]:
        out.update(status='no_board_area', header_version=hdr[0]&0x0f)
    else:
        off = hdr[3]*8
        f.seek(off)
        area_head = f.read(6)
        if len(area_head) != 6 or area_head[1] < 1:
            out.update(status='invalid_board_area_header', board_offset=off)
        else:
            area_len = area_head[1]*8
            f.seek(off)
            area = f.read(area_len)
            checksum_ok = len(area)==area_len and sum(area)%256==0
            structure_ok = len(area)==area_len and checksum_ok and (area_head[0]&0x0f)==1
            fields=[]
            i=6
            while structure_ok and i < len(area)-1:
                tl=area[i]; i+=1
                typ=tl>>6; n=tl&0x3f
                if typ==3 and n==1 and (area[i]<0x20 or area[i]==0x7f):
                    break
                if i+n>len(area)-1:
                    structure_ok=False
                    break
                raw=area[i:i+n];i+=n
                fields.append((typ,raw))
            names=['manufacturer','product_name','serial_number','part_number','file_id','revision']
            parsed={}
            for name,(typ,raw) in zip(names,fields):
                if name=='serial_number':
                    continue
                if typ==3:
                    val=raw.decode('ascii','replace').strip()
                    parsed[name]=''.join(c for c in val if c.isprintable())
                elif typ==0:
                    parsed[name]='binary:'+raw.hex()
                else:
                    parsed[name]='type_%d_length_%d'%(typ,len(raw))
            out.update(status='ok' if structure_ok else 'invalid_board_area',header_version=hdr[0]&0x0f,
                       board_offset=off,board_area_bytes=area_len,common_checksum_ok=True,
                       board_checksum_ok=bool(checksum_ok),board_structure_ok=bool(structure_ok),
                       board_area_version=area_head[0]&0x0f,fields=parsed)
print(json.dumps(out,ensure_ascii=False),flush=True)
