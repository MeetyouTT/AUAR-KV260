"""Source-only bounded TCP release wait for the already frozen minor tools."""
import ast
import hashlib


ORIGINAL_OWNERLESS_SHA = '034d1ef96fff72f8e1c4792bfd0830d512f9334027ad43d15fcf7cea5c5132cf'

WAIT_HELPERS = r'''
def _ownerless_process_snapshot(u):
 need(u['MainPID']=='0' and u['ActiveState'] in ('failed','inactive') and not u.get('Job'),'ownerless_failed_or_inactive_unit_required')
 for item in Path('/proc').iterdir():
  if not item.name.isdigit():continue
  try:raw=(item/'cmdline').read_bytes()
  except FileNotFoundError:continue
  need(len(raw)<=1048576,'bounded_proc_command_required')
  args=raw.split(b'\0')
  need(not any(a.endswith((b'/board_avatar_pan.py',b'/board_avatar_gtk.py')) for a in args),'another_gtk_owner_exists')
  need(str(Path(EXACT_TARGET)/'startup/launcher.py').encode() not in args,'another_supervisor_exists')

def _control_port_has_listener(port=8783):
 need(type(port) is int and 1<=port<=65535,'valid_control_port_required')
 for name in ('tcp','tcp6'):
  try:
   with (Path('/proc/net')/name).open('rb') as stream:raw=stream.read(2097153)
  except FileNotFoundError:
   if name=='tcp6':continue
   raise
  need(len(raw)<=2097152,'bounded_tcp_metadata_required')
  for line in raw.decode('ascii').splitlines()[1:]:
   fields=line.split()
   need(len(fields)>=4,'valid_tcp_metadata_required')
   address,separator,hex_port=fields[1].rpartition(':')
   need(separator==':' and len(address) in (8,32) and re.fullmatch('[0-9A-Fa-f]+',address)
        and re.fullmatch('[0-9A-Fa-f]{4}',hex_port)
        and re.fullmatch('[0-9A-Fa-f]{2}',fields[3]),'valid_tcp_endpoint_metadata_required')
   if int(hex_port,16)==port and fields[3].upper()=='0A':return True
 return False

def ownerless(u):
 import errno,socket
 _ownerless_process_snapshot(u)
 deadline=time.monotonic()+70.0
 while True:
  boot();_ownerless_process_snapshot(c.show())
  need(not _control_port_has_listener(),'control_port_has_active_listener')
  try:
   with socket.socket() as sock:
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    sock.bind(('127.0.0.1',8783))
    boot();_ownerless_process_snapshot(c.show())
   return
  except OSError as exc:
   if exc.errno!=errno.EADDRINUSE:raise
   need(not _control_port_has_listener(),'control_port_has_active_listener')
   remaining=deadline-time.monotonic()
   need(remaining>0,'control_port_release_timeout')
   time.sleep(min(0.25,remaining))
'''


def patch_ownerless(source):
    tree=ast.parse(source)
    functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='ownerless']
    if len(functions)!=1:
        raise ValueError('one_frozen_ownerless_function_required')
    function=functions[0]
    original=ast.get_source_segment(source,function)
    if hashlib.sha256(original.encode()).hexdigest()!=ORIGINAL_OWNERLESS_SHA:
        raise ValueError('ownerless_baseline_changed')
    names={node.name for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
    if names & {'_ownerless_process_snapshot','_control_port_has_listener'}:
        raise ValueError('port_wait_helper_name_collision')
    lines=source.splitlines(keepends=True)
    lines[function.lineno-1:function.end_lineno]=[WAIT_HELPERS+'\n']
    result=''.join(lines)
    ast.parse(result,feature_version=(3,9))
    return result
