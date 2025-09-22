# -*- coding: utf-8 -*-
import io
from PIL import Image

class BitReader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0
        self.barrel = 0
        self.length = 0

    def _fill(self):
        if self.offset >= len(self.data):
            return False
        hi = self.data[self.offset]
        lo = self.data[self.offset+1] if (self.offset+1)<len(self.data) else 0
        self.offset += 2 if (self.offset+1)<len(self.data) else 1
        self.barrel = (hi << 8) | lo
        self.length = 16
        return True

    def get_bit(self):
        if self.length == 0:
            if not self._fill():
                return None
        bit = 1 if (self.barrel & 0x8000) else 0
        self.barrel = (self.barrel << 1) & 0xFFFFFFFF
        self.length -= 1
        return bit

    def get_bits(self, n):
        if n == 0: return 0
        val = 0
        for _ in range(n):
            b = self.get_bit()
            if b is None: return None
            val = (val << 1) | b
        return val

def read_palette_from_header(data):
    pal_bytes = data[4:36]
    pal = []
    for i in range(0, 32, 2):
        first = pal_bytes[i]
        second = pal_bytes[i+1]
        b_n = first & 0x0F
        g_n = (second >> 4) & 0x0F
        r_n = second & 0x0F
        r = int(round(r_n * 255 / 15))
        g = int(round(g_n * 255 / 15))
        b = int(round(b_n * 255 / 15))
        pal.append((r,g,b,255))
    return pal

def decompress_from_my_compressor(data_stream: io.BytesIO, output_png_path: str):
    """
    Распаковывает BIN, созданный SF1PortraitCompressor, в PNG 64x64.
    Возвращает: путь к сохранённому PNG файлу.
    """
    data = data_stream.read()
    palette = read_palette_from_header(data)
    stream = data[38:]
    br = BitReader(stream)

    W, H, SIZE = 64, 64, 64*64
    indexed = [0]*SIZE
    pos, last = 0, 0

    # Пропустить init биты
    br.get_bit(); br.get_bit()

    while pos < SIZE:
        pix = br.get_bits(4)
        if pix is None: break
        pix &= 0xF
        indexed[pos] = pix
        last = pix

        nxt = br.get_bit()
        if nxt is None: break

        if nxt == 1:
            # Обработка copy_down_left/offset
            b0 = br.get_bit()
            if b0 == 0:
                b1 = br.get_bit()
                offset = 1 if b1==1 else 2
                if offset==2: br.get_bit(); br.get_bit()
                target = pos + W - offset
                if 0 <= target < SIZE:
                    indexed[target] = last
            br.get_bit(); br.get_bit()  # два нуля
            br.get_bit()  # контрольный бит
            # Распаковка repeat run
            t3=0
            while True:
                b=br.get_bit()
                if b==1: break
                t3+=1
            t=2; t2=2
            for _ in range(t3):
                t+=t2; t2*=2
            rem=0
            for _ in range(t3+1):
                rem=(rem<<1)|br.get_bit()
            repeat=(t-2)+rem
            for k in range(1,repeat):
                idx=pos+k
                if idx<SIZE: indexed[idx]=last
            pos+=repeat
            continue
        else:
            # Repeat run / advance
            t3=0
            while True:
                b=br.get_bit()
                if b==1: break
                t3+=1
            t=2; t2=2
            for _ in range(t3):
                t+=t2; t2*=2
            rem=0
            for _ in range(t3+1):
                rem=(rem<<1)|br.get_bit()
            repeat=(t-2)+rem
            for k in range(1,repeat):
                idx=pos+k
                if idx<SIZE: indexed[idx]=last
            pos+=repeat
            continue

    img = Image.new('RGBA',(W,H))
    px = img.load()
    for i,v in enumerate(indexed):
        x=i%W; y=i//W
        if v==0: px[x,y]=(0,0,0,0)
        else:
            r,g,b,a=palette[v&0xF]
            px[x,y]=(r,g,b,255)
    img.save(output_png_path)
    return output_png_path