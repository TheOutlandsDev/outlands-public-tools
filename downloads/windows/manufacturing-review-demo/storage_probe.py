"""Qualification-only native volume classification; never emit private paths."""
import ctypes,json,re,sys
from ctypes import wintypes as w
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,w.LPVOID,w.DWORD,w.DWORD,w.HANDLE];k.CreateFileW.restype=w.HANDLE
k.GetFinalPathNameByHandleW.argtypes=[w.HANDLE,w.LPWSTR,w.DWORD,w.DWORD];k.GetFinalPathNameByHandleW.restype=w.DWORD
k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
value=[]
for label,path in zip(('overlay','scratch'),sys.argv[1:]):
 h=k.CreateFileW('\\\\?\\'+path,0x80,3,None,3,0x02200000,None)
 if h==ctypes.c_void_p(-1).value:value.append(dict(storage=label,opened=False,error=ctypes.get_last_error()));continue
 try:
  buf=ctypes.create_unicode_buffer(32768);n=k.GetFinalPathNameByHandleW(h,buf,len(buf),2)
  family='local-nt-volume' if re.match(r'\\Device\\HarddiskVolume[0-9]+(?:\\|$)',buf.value,re.I) else 'virtual-nt-volume' if buf.value.startswith('\\Device\\VhdHardDisk') else 'mapped-nt-volume' if 'ContainerMapped' in buf.value else 'other'
  value.append(dict(storage=label,opened=True,normalized_nt_name_returned=bool(n),family=family,error=ctypes.get_last_error() if not n else 0))
 finally:k.CloseHandle(h)
print(json.dumps(value))
