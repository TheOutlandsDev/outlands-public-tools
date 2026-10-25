"""Create fictional raw image fixtures only. Never install or boot these images. MIT."""
from pathlib import Path
import json
import struct
import sys
import uuid
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser,TextError,canonical_directory,cli_error,local_path,require

def header(sector,current,backup,first,last,table_lba,table):
    data=bytearray(sector);data[:8]=b'EFI PART'
    struct.pack_into('<IIIIQQQQ',data,8,0x10000,92,0,0,current,backup,first,last)
    data[56:72]=uuid.UUID('11111111-2222-4333-8444-555555555555').bytes_le
    struct.pack_into('<QIII',data,72,table_lba,128,128,zlib.crc32(table))
    struct.pack_into('<I',data,16,zlib.crc32(data[:92]));return data

def build_image(sector=512,partitions=None):
    require(sector in {512,4096},'SECTOR_SIZE_UNSUPPORTED')
    sectors=256;table_sectors=(16384+sector-1)//sector;first=2+table_sectors;last=sectors-2-table_sectors
    if partitions is None:partitions=[(first+2,first+9,'demo_alpha'),(first+12,first+20,'demo_beta')]
    table=bytearray(16384)
    for index,(start,end,name) in enumerate(partitions):
        require(index<128 and len(name.encode('utf-16-le'))<=72,'EXAMPLE_PARTITION_LIMIT')
        offset=index*128;table[offset:offset+16]=uuid.UUID('00000000-0000-4000-8000-000000000001').bytes_le
        table[offset+16:offset+32]=uuid.UUID(int=index+16).bytes_le
        struct.pack_into('<QQQ',table,offset+32,start,end,0)
        encoded=name.encode('utf-16-le');table[offset+56:offset+56+len(encoded)]=encoded
    data=bytearray(sectors*sector);data[510:512]=b'\x55\xaa';data[450]=0xee
    struct.pack_into('<II',data,454,1,sectors-1)
    data[sector:2*sector]=header(sector,1,sectors-1,first,last,2,table)
    data[2*sector:2*sector+len(table)]=table
    backup_table_lba=sectors-1-table_sectors
    data[backup_table_lba*sector:backup_table_lba*sector+len(table)]=table
    data[-sector:]=header(sector,sectors-1,1,first,last,backup_table_lba,table)
    return data

def refresh_checksums(data,sector):
    for lba in (1,len(data)//sector-1):
        offset=lba*sector; table_lba,count,size=struct.unpack_from('<QII',data,offset+72)
        table=data[table_lba*sector:table_lba*sector+count*size]
        struct.pack_into('<I',data,offset+88,zlib.crc32(table));struct.pack_into('<I',data,offset+16,0)
        header_size=struct.unpack_from('<I',data,offset+12)[0]
        struct.pack_into('<I',data,offset+16,zlib.crc32(data[offset:offset+header_size]))

def main(argv=None):
    parser=Parser(description=__doc__);parser.add_argument('--output',required=True)
    try:
        args=parser.parse_args(argv);output=local_path(args.output);parent=canonical_directory(output.parent);output=parent/output.name
        require(not output.exists() and not output.is_symlink(),'OUTPUT_EXISTS');output.mkdir(mode=0o700,exist_ok=False)
        bad_crc=build_image();bad_crc[512+16]^=1
        overlap=build_image(partitions=[(36,50,'demo_overlap_a'),(45,60,'demo_overlap_b')])
        values={'clean-512.img':build_image(),'clean-4096.img':build_image(4096),'review-crc.img':bad_crc,'review-overlap.img':overlap}
        for name,data in values.items():
            with (output/name).open('xb') as stream:stream.write(data)
        print(json.dumps({'status':'FICTIONAL_EXAMPLES_CREATED','files':len(values)},sort_keys=True));return 0
    except (TextError,OSError,ValueError) as error:return cli_error(error)

if __name__=='__main__':raise SystemExit(main())
