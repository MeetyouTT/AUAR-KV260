"""Read only new USB error records, without clearing any logs."""
import errno,json,os,time
fd=os.open('/dev/kmsg',os.O_RDONLY|os.O_NONBLOCK);count=overruns=0
try:
 os.lseek(fd,0,os.SEEK_END);end=time.monotonic()+2
 while time.monotonic()<end:
  try:
   value=os.read(fd,8192)
   count+=int(b"HC couldn't access mem fast enough" in value)
  except BlockingIOError:time.sleep(.02)
  except OSError as exc:
   if exc.errno==errno.EPIPE:overruns+=1
   else:raise
finally:os.close(fd)
print(json.dumps({'new_usb_buffer_errors_in_2s':count,'reader_overruns':overruns,'log_cleared':False,'services_restarted':False,'register_writes':0}))
