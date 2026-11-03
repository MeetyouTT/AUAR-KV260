import gzip,hashlib,json,struct,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
library=Path('/home/root/aura-native-critical-20261024/link-only/5cae51cf9d22e5f7/libaura_native_v2_candidate.so')
raw=library.read_bytes();assert hashlib.sha256(raw).hexdigest()=='c675ba698d45acd8742e52403e6186f43dc56d7d313d0e740896b19412bde656'
assert raw[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',raw,18)[0]==183
header=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
phoff,shoff,phsize,phnum,shsize,shnum=header[5],header[6],header[9],header[10],header[11],header[12]
sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*shsize) for i in range(shnum)]
address=None
for section in sections:
 if section[1]!=11:continue
 strings=sections[section[6]];names=raw[strings[4]:strings[4]+strings[5]]
 for i in range(section[5]//section[9]):
  name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',raw,section[4]+i*section[9])
  if names[name:].split(b'\0',1)[0]==b'aura_native_optional_execute':address=value
assert address is not None
offset=None
for i in range(phnum):
 typ,flags,fileoff,vaddr,paddr,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',raw,phoff+i*phsize)
 if typ==1 and vaddr<=address< vaddr+filesz:offset=fileoff+address-vaddr
assert offset is not None
config=gzip.decompress(Path('/proc/config.gz').read_bytes()).decode().splitlines()
flags=['CONFIG_UPROBES','CONFIG_UPROBE_EVENTS','CONFIG_KPROBE_EVENTS','CONFIG_TRACER_SNAPSHOT','CONFIG_EVENT_TRACING','CONFIG_FTRACE']
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as stream:h=json.load(stream)
print(json.dumps({'scope':'read-only kernel trace capability and pinned ELF file offset',
 'pid':h['pid'],'elf_function_file_offset':offset,'kernel_flags':{k:next((line for line in config if line.startswith(k+'=')),None) for k in flags},
 'uprobe_interface':Path('/sys/kernel/tracing/uprobe_events').exists(),
 'existing_uprobe_definitions':Path('/sys/kernel/tracing/uprobe_events').read_text(),
 'library_is_mapped':str(library) in Path('/proc/'+str(h['pid'])+'/maps').read_text(),
 'thread_ids':[int(p.name) for p in Path('/proc/'+str(h['pid'])+'/task').iterdir()],
 'event_formats':{name:(Path('/sys/kernel/tracing/events/sched')/name/'format').read_text() for name in ['sched_switch','sched_wakeup']}}))
