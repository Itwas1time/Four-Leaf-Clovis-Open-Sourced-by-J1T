"""Bounded, lossless source-cell storage for the full PBDB snapshot."""
import json
import zlib
from collections import Counter

MAX_ROW_BYTES = 4 * 1024**2
MAX_BLOCK_BYTES = 8 * 1024**2
MAX_BLOCK_ROWS = 128
MAX_COLUMNS = 512


def encode(values):
    if not isinstance(values, (list, tuple)) or len(values) > MAX_COLUMNS or any(not isinstance(value, str) for value in values):
        raise ValueError('The native fossil cells are invalid.')
    raw = json.dumps(values, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if not 1 <= len(raw) <= MAX_ROW_BYTES:
        raise ValueError('The native fossil row exceeds reviewed bounds.')
    return len(raw), zlib.compress(raw, 6)


def _inflate(blob,size,bound):
    if not isinstance(blob,bytes) or type(size) is not int or not 1<=size<=bound:
        raise ValueError('The stored fossil source row is invalid.')
    decompressor = zlib.decompressobj()
    raw = decompressor.decompress(blob, size + 1)
    if len(raw) != size or not decompressor.eof or decompressor.unused_data or decompressor.unconsumed_tail:
        raise ValueError('The stored fossil source row is incomplete or exceeds its bound.')
    return json.loads(raw)


def _cells(values,headers):
    if (not isinstance(headers,(list,tuple)) or not 1<=len(headers)<=MAX_COLUMNS
            or any(not isinstance(header,str) for header in headers)):
        raise ValueError('The native fossil source columns are invalid.')
    if (not isinstance(values, list) or len(values) != len(headers)
            or any(not isinstance(value, str) for value in values)):
        raise ValueError('The native fossil source cells do not match their columns.')
    source = {}
    for key, value in zip(headers, values, strict=True):
        if key in source and source[key] != value:
            raise ValueError('Repeated fossil source columns disagree.')
        source[key] = value
    counts=Counter(headers)
    fields = [(key + (' [column ' + str(index + 1) + ']' if counts[key] > 1 else ''), value)
              for index, (key, value) in enumerate(zip(headers, values, strict=True))]
    return source, fields


def decode(blob,size,headers):
    return _cells(_inflate(blob,size,MAX_ROW_BYTES),headers)


def decode_block(blob,size,ordinal,rows,headers):
    if type(rows) is not int or not 1<=rows<=MAX_BLOCK_ROWS or type(ordinal) is not int or not 0<=ordinal<rows:
        raise ValueError('The native fossil source block position is invalid.')
    values=_inflate(blob,size,MAX_BLOCK_BYTES)
    if not isinstance(values,list) or len(values)!=rows:
        raise ValueError('The native fossil source block has the wrong row count.')
    return _cells(values[ordinal],headers)
