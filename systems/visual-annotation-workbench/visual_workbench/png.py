"""Bounded PNG subset: 8-bit gray/RGB/RGBA, non-interlaced; canonical metadata-free output."""
import struct
import zlib
from .runtime import WorkbenchError,MAX_INPUT

SIGNATURE=b'\x89PNG\r\n\x1a\n'
MAX_PIXELS=262144


def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)


def encode(width,height,rgba):
    if type(width) is not int or type(height) is not int or not 1<=width<=1024 or not 1<=height<=1024 or width*height>MAX_PIXELS or type(rgba) is not bytes or len(rgba)!=width*height*4:raise WorkbenchError('PIXELS_INVALID')
    rows=b''.join(b'\0'+rgba[y*width*4:(y+1)*width*4] for y in range(height))
    return SIGNATURE+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows,9))+chunk(b'IEND',b'')


def _paeth(a,b,c):
    p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
    return a if pa<=pb and pa<=pc else b if pb<=pc else c


def decode(raw):
    if type(raw) is not bytes or len(raw)>MAX_INPUT or raw[:8]!=SIGNATURE:raise WorkbenchError('PNG_INVALID')
    offset=8;header=None;compressed=[];ended=False;data_closed=False;chunks=0
    while offset<len(raw):
        if offset+12>len(raw):raise WorkbenchError('PNG_TRUNCATED')
        size=struct.unpack('>I',raw[offset:offset+4])[0];kind=raw[offset+4:offset+8];end=offset+12+size;chunks+=1
        if chunks>128 or end>len(raw) or not all(65<=x<=90 or 97<=x<=122 for x in kind) or kind[2]&32:raise WorkbenchError('PNG_CHUNK_INVALID')
        data=raw[offset+8:offset+8+size];crc=struct.unpack('>I',raw[offset+8+size:end])[0]
        if zlib.crc32(kind+data)&0xffffffff!=crc:raise WorkbenchError('PNG_CRC_INVALID')
        if kind==b'IHDR':
            if header is not None or offset!=8 or size!=13:raise WorkbenchError('PNG_HEADER_INVALID')
            width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',data)
            if not 1<=width<=1024 or not 1<=height<=1024 or width*height>MAX_PIXELS or depth!=8 or color not in (0,2,6) or compression or filtering or interlace:raise WorkbenchError('PNG_SUBSET_UNSUPPORTED')
            header=(width,height,color)
        elif header is None:raise WorkbenchError('PNG_HEADER_INVALID')
        elif kind==b'IDAT':
            if data_closed:raise WorkbenchError('PNG_CHUNK_ORDER')
            compressed.append(data)
        elif kind==b'IEND':
            if size or not compressed or end!=len(raw):raise WorkbenchError('PNG_END_INVALID')
            ended=True;offset=end;break
        elif kind in (b'acTL',b'fcTL',b'fdAT',b'tRNS') or not kind[0]&32:raise WorkbenchError('PNG_SUBSET_UNSUPPORTED')
        elif compressed:data_closed=True
        offset=end
    if not ended or header is None:raise WorkbenchError('PNG_END_INVALID')
    width,height,color=header;channels={0:1,2:3,6:4}[color];stride=width*channels;expected=(stride+1)*height
    try:
        stream=zlib.decompressobj();pixels=stream.decompress(b''.join(compressed),expected+1)
    except zlib.error:raise WorkbenchError('PNG_DECOMPRESSION_INVALID') from None
    if len(pixels)!=expected or not stream.eof or stream.unused_data or stream.unconsumed_tail:raise WorkbenchError('PNG_DECOMPRESSION_LIMIT')
    result=bytearray();previous=bytearray(stride)
    for y in range(height):
        start=y*(stride+1);mode=pixels[start];row=bytearray(pixels[start+1:start+stride+1])
        if mode>4:raise WorkbenchError('PNG_FILTER_UNSUPPORTED')
        for x in range(stride):
            left=row[x-channels] if x>=channels else 0;up=previous[x];upper_left=previous[x-channels] if x>=channels else 0
            predictor=0 if mode==0 else left if mode==1 else up if mode==2 else (left+up)//2 if mode==3 else _paeth(left,up,upper_left)
            row[x]=(row[x]+predictor)&255
        for x in range(width):
            values=row[x*channels:(x+1)*channels]
            result.extend(bytes((values[0],values[0],values[0],255)) if channels==1 else values+b'\xff' if channels==3 else values)
        previous=row
    return width,height,bytes(result)


def normalize(raw):
    width,height,pixels=decode(raw);return width,height,encode(width,height,pixels)


def mask_png(width,height,mask):
    if len(mask)!=width*height:raise WorkbenchError('MASK_INVALID')
    rgba=bytearray()
    for value in mask:rgba.extend((value,value,value,255))
    return encode(width,height,bytes(rgba))


def fictional(width=64,height=48,seed=0):
    pixels=bytes(channel for y in range(height) for x in range(width) for channel in ((x*3+seed)%256,(y*5+seed)%256,((x//8+y//8)%2)*80+40,255))
    return encode(width,height,pixels)
