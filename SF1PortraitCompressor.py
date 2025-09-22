# -*- coding: utf-8 -*-
import io
from PIL import Image

class SF1PortraitCompressor:
    def __init__(self, png_path=None, image=None):
        self.png_path = png_path
        self.image = image
        self.barrel = 0
        self.length = 0
        self.output = bytearray()
        self.pos = 0
        self.pos2 = 0
        self.last = 0
        self.width = 64
        self.size = 64 * 64
        self.value_map = {0: 0, 1: 2, 2: 4, 3: 6, 4: 8, 5: 10, 6: 12, 7: 14}  # SF2PaletteManager VALUE_ARRAY

    def put_bit(self, bit):
        self.barrel = (self.barrel << 1) | (1 if bit else 0)
        self.length += 1
        if self.length == 16:
            self.output.extend(self.barrel.to_bytes(2, 'big'))
            self.length = 0
            self.barrel = 0

    def put_bits(self, value, bits):
        if value < 0 or value >= (1 << bits):
            raise ValueError(f"Value {value} is out of range for {bits} bits")
        for i in range(bits - 1, -1, -1):
            self.put_bit((value >> i) & 1)

    def put_pixel(self, pixel):
        self.put_bits(pixel, 4)
        self.last = pixel

    def repeat_last(self, repeat):
        t = 2
        t2 = 2
        t3 = 0
        while repeat >= t * 2 - 2:
            t += t2
            t2 *= 2
            t3 += 1
        for _ in range(t3):
            self.put_bit(0)
        self.put_bit(1)
        repeat -= (t - 2)
        t2 = 1 << t3
        for i in range(t3 + 1):
            self.put_bit(1 if (t2 & repeat) else 0)
            t2 >>= 1

    def copy_down_left(self, offset):
        if offset == 1:
            self.put_bit(0)
            self.put_bit(1)
        elif offset == 2:
            self.put_bit(0)
            self.put_bit(0)
            self.put_bit(1)
            self.put_bit(0)
        self.pos2 += self.width
        self.pos2 -= offset

    def search(self, found):
        if self.pos2 + self.width - 1 < self.size:
            if self.indexed_pixels[self.pos2 + self.width - 1] == self.last and \
               (self.pos2 + self.width - 2 >= self.size or self.indexed_pixels[self.pos2 + self.width - 2] != self.last):
                if not found:
                    self.put_bit(1)
                self.copy_down_left(1)
                return True
        return False

    def flush_bits(self):
        if self.length > 0:
            if self.length > 16:
                self.length = 0
                self.barrel = 0
            self.barrel <<= (16 - self.length)
            self.output.extend(self.barrel.to_bytes(2, 'big'))
            self.length = 0
            self.barrel = 0

    def compress(self, output_path):
        try:
            if self.image is None:
                if self.png_path is None:
                    raise ValueError("Either png_path or image must be provided")
                img = Image.open(self.png_path).convert('RGBA')
            else:
                img = self.image.convert('RGBA')
            width, height = img.size
            if width != 64 or height != 64:
                raise ValueError("Ошибка: Размер изображения должен быть ровно 64x64 пикселей")
            pixels = list(img.getdata())
            colors = set(pixel[:3] for pixel in pixels if pixel[3] != 0)
            if len(colors) > 15:
                raise ValueError("Ошибка: Максимум 16 цветов в палитре (включая прозрачный)")

            # Palette conversion (based on SF2PaletteManager PaletteEncoder.java)
            palette = [(0, 0, 0, 0)]  # Первый цвет — прозрачный
            color_map = {palette[0]: 0}
            for r, g, b, a in pixels:
                if a == 0:
                    continue
                # Конверсия в 3-3-2 (R,G: 0-7, B: 0-7 mapped to VALUE_ARRAY)
                r_3bit = self.value_map.get((r >> 5) & 0x07, 0)
                g_3bit = self.value_map.get((g >> 5) & 0x07, 0)
                b_3bit = self.value_map.get((b >> 5) & 0x07, 0)  # Используем 3 бита для B
                color_key = (r_3bit, g_3bit, b_3bit, 255)
                if color_key not in color_map and len(palette) < 16:
                    palette.append((r, g, b, 255))  # Сохраняем оригинальные RGB
                    color_map[color_key] = len(palette) - 1
            while len(palette) < 16:
                palette.append((0, 0, 0, 0))

            # Формируем данные палитры (SF2 format: first byte = B, second byte = (G << 4) | R)
            palette_data = bytearray()
            for i, (r, g, b, _) in enumerate(palette):
                r_3bit = self.value_map.get((r >> 5) & 0x07, 0)
                g_3bit = self.value_map.get((g >> 5) & 0x07, 0)
                b_3bit = self.value_map.get((b >> 5) & 0x07, 0)
                first = b_3bit & 0x0F
                second = ((g_3bit << 4) & 0xF0) | (r_3bit & 0x0F)
                palette_data.extend([first, second])

            # Map pixels to palette indices
            self.indexed_pixels = bytearray()
            for r, g, b, a in pixels:
                if a == 0:
                    self.indexed_pixels.append(0)  # Прозрачные пиксели всегда индекс 0
                else:
                    r_3bit = self.value_map.get((r >> 5) & 0x07, 0)
                    g_3bit = self.value_map.get((g >> 5) & 0x07, 0)
                    b_3bit = self.value_map.get((b >> 5) & 0x07, 0)
                    color_key = (r_3bit, g_3bit, b_3bit, 255)
                    self.indexed_pixels.append(color_map.get(color_key, 0))

            # Build .bin structure
            self.output = bytearray()
            self.output.extend(b"\x00\x00")  # BLINK block (empty)
            self.output.extend(b"\x00\x00")  # TALK block (empty)
            self.output.extend(palette_data)  # Palette (32 bytes)
            self.output.extend(b"\x08\x08")  # Magic bytes

            # Compress graphics с исправлением прозрачности
            self.put_bit(1)
            self.put_bit(1)
            iteration_count = 0
            max_iterations = self.size * 2
            while self.pos < self.size:
                iteration_count += 1
                if iteration_count > max_iterations:
                    raise RuntimeError(f"Infinite loop detected at pos {self.pos}, iteration {iteration_count}")
                
                current_pixel = self.indexed_pixels[self.pos]
                
                # Если пиксель прозрачный (0), кодируем его отдельно и не ищем копии
                if current_pixel == 0:
                    self.put_pixel(0)
                    self.last = 0
                    self.pos += 1
                    self.pos2 = self.pos
                    # Проверяем, есть ли ещё прозрачные пиксели для повторения
                    if self.pos < self.size and self.indexed_pixels[self.pos] == 0:
                        self.pos2 = self.pos
                        repeat = 1
                        while self.pos2 < self.size and self.indexed_pixels[self.pos2] == 0:
                            self.pos2 += 1
                            repeat += 1
                        self.pos = self.pos2
                        self.put_bit(0)
                        self.repeat_last(repeat)
                    else:
                        self.put_bit(0)
                        self.put_bit(1)
                        self.put_bit(1)
                    continue

                # Для непрозрачных пикселей — оригинальная логика
                self.put_pixel(current_pixel)
                self.last = current_pixel
                self.pos2 = self.pos
                found = 0
                t = False
                while found == 0:
                    t = self.search(found)
                    if t:
                        found = 1
                    else:
                        break
                if found:
                    self.put_bit(0)
                    self.put_bit(0)

                if self.pos + 1 < self.size and self.indexed_pixels[self.pos + 1] == self.last:
                    self.pos2 = self.pos + 1
                    repeat = 1
                    while self.pos2 < self.size and self.indexed_pixels[self.pos2] == self.last:
                        self.pos2 += 1
                        repeat += 1
                    self.pos = self.pos2
                    self.put_bit(0)
                    self.repeat_last(repeat)
                else:
                    self.put_bit(0)
                    self.put_bit(1)
                    self.put_bit(1)
                    self.pos += 1
                    self.pos2 = self.pos

            self.flush_bits()

            # Save
            with open(output_path, "wb") as f:
                f.write(self.output)

        except Exception as e:
            print(f"Compression error: {str(e)}")
            raise

if __name__ == "__main__":
    compressor = SF1PortraitCompressor(png_path="input.png")
    try:
        compressor.compress("output.bin")
        print("Успех: Файл output.bin создан")
    except ValueError as e:
        print(f"Ошибка: {e}")
    except Exception as e:
        print(f"Ошибка: {str(e)}")