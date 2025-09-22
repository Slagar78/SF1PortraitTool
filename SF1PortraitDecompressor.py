# -*- coding: utf-8 -*-
import io

class SF1PortraitDecompressor:
    """
    Переписанный декомпрессор на основе Pixel.h (sf1edit)

    Небольшое изменение: get_data принимает опциональный параметр offset.
    Если offset передан (целое число), файл будет смещён на него перед чтением
    ширины/высоты, чтобы поведение совпадало с PixelDecompressor.get_data(offset).
    """
    def __init__(self, f: io.BytesIO):
        self.file = f
        self.barrel = 0
        self.length = 0
        self.pos = -1
        self.pos2 = 0
        self.count = 0
        self.data = None
        self.width = 0
        self.height = 0
        self.size = 0
        self.last = 0

    def get_bit(self):
        if self.length == 0:
            hi = self.file.read(1)
            if not hi:
                return False
            lo = self.file.read(1)
            if not lo:
                return False
            self.barrel = (hi[0] << 8) | lo[0]
            self.length = 16
        bit = (self.barrel & 0x8000) != 0
        self.barrel = (self.barrel << 1) & 0xFFFF
        self.length -= 1
        return bit

    def get_bits(self, n):
        c = 0
        for _ in range(n):
            if self.length == 0:
                hi = self.file.read(1)
                if not hi:
                    return c
                lo = self.file.read(1)
                if not lo:
                    return c
                self.barrel = (hi[0] << 8) | lo[0]
                self.length = 16
            c = (c << 1) | (1 if (self.barrel & 0x8000) else 0)
            self.barrel = (self.barrel << 1) & 0xFFFF
            self.length -= 1
        return c

    def copy_down_bit_right(self):
        self.pos2 += self.width
        if self.get_bit():
            self.pos2 += 1
        if self.pos2 < self.size:
            self.data[self.pos2] = self.last

    def copy_down_right(self, off):
        self.pos2 += self.width
        self.pos2 += off
        if self.pos2 < self.size:
            self.data[self.pos2] = self.last

    def copy_down_left(self, off):
        self.pos2 += self.width
        self.pos2 -= off
        if self.pos2 < self.size:
            self.data[self.pos2] = self.last

    def get_data(self, offset: int = None):
        """
        Распаковывает портрет из текущего self.file.
        Если offset указан (int), сначала делает self.file.seek(offset).
        Возвращает: (список_hex_нибблов, количество непрозрачных пикселей).
        """
        # Сброс состояния декодера
        self.length = 0
        self.pos = -1
        self.pos2 = 0
        self.barrel = 0

        # Если задан offset — переходим на него
        if offset is not None:
            # допустимое поведение: если offset не int — будет исключение у caller
            self.file.seek(offset)

        # читаем ширину/высоту (первые два байта потока)
        width_data = self.file.read(1)
        if not width_data:
            raise ValueError("Недостаточно данных для чтения ширины")
        self.width = width_data[0] * 8

        height_data = self.file.read(1)
        if not height_data:
            raise ValueError("Недостаточно данных для чтения высоты")
        self.height = height_data[0] * 8

        self.size = self.width * self.height
        # Инициализируем буфер прозрачностью 0xFF (как в оригинале)
        self.data = bytearray([0xFF] * self.size)

        # Основной цикл декомпрессии (повторяет логику Pixel.h)
        while self.pos < self.size or self.pos == -1 or self.pos == 0xFFFFFFFF:
            restart = False
            self.count = -1
            shift = 2

            # do { ... } while (!bit);
            while True:
                if self.length == 0:
                    hi = self.file.read(1)
                    if not hi:
                        # досрочный выход — возвращаем накопленные данные
                        return [f"{x:X}" for x in self.data[:self.size]], \
                               sum(1 for x in self.data if x != 0xFF)
                    lo = self.file.read(1)
                    if not lo:
                        return [f"{x:X}" for x in self.data[:self.size]], \
                               sum(1 for x in self.data if x != 0xFF)
                    self.barrel = (hi[0] << 8) | lo[0]
                    self.length = 16
                bit = (self.barrel & 0x8000) != 0
                self.barrel = (self.barrel << 1) & 0xFFFF
                self.length -= 1
                self.count += 1
                if bit:
                    break

            shift <<= self.count
            self.pos += shift - 2

            self.count += 1
            if self.count:
                self.pos += self.get_bits(self.count)

            if self.pos >= self.size:
                break

            c = self.get_bits(4) & 0xF
            self.data[self.pos] = c
            self.last = c

            if self.get_bit():
                self.pos2 = self.pos
                while not restart:
                    if self.get_bit():
                        self.copy_down_bit_right()
                    elif self.get_bit():
                        self.copy_down_left(1)
                    elif self.get_bit():
                        if self.get_bit():
                            self.copy_down_right(2)
                        else:
                            self.copy_down_left(2)
                    else:
                        restart = True

        # считаем непрозрачные пиксели
        non_trans = sum(1 for x in self.data[:self.size] if x != 0xFF)
        return [f"{x:X}" for x in self.data[:self.size]], non_trans
