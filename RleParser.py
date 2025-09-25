# -*- coding: utf-8 -*-
import os
import logging

class RleParser:
    """
    Простой парсер для структуры portraitXX.bin для извлечения блоков blink, talk, palette и magic.
    Реализовано по правилам, аналогичным sf1_portrait_rules.txt (см. комментарии).
    Блоки blink и talk парсятся динамически, palette - фиксированные 32 байта, magic - 2 байта (если присутствуют).
    """
    def __init__(self, bin_path):
        # Настройка логирования в parser.log
        logging.basicConfig(
            filename='parser.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.bin_path = bin_path
        self.warnings = []  # Хранение предупреждений для отображения в GUI
        with open(bin_path, "rb") as f:
            self.data = f.read()
        self.ln = len(self.data)
        self.blink = b""
        self.talk = b""
        self.palette = b""
        self.magic = b""
        self.graphic_offset = None
        self.logger.info(f"Загружен файл {bin_path}, размер={self.ln} байт")
        self.logger.info(f"Первые 60 байт: {self.data[:60].hex(' ').upper()}")
        self.parse()

    def _skip_block(self, data, pos):
        ln = len(data)
        if pos >= ln or data[pos] != 0x00:
            # Если достигли конца файла, избегаем ошибки индексации
            if pos < ln:
                self.logger.warning(f"Блок на позиции {pos} не начинается с 0x00 (найдено {data[pos]:02X} или конец файла)")
                self.warnings.append(f"⚠️ Блок на позиции {pos} не начинается с 0x00 (найдено {data[pos]:02X})")
            else:
                self.logger.warning(f"Блок на позиции {pos} за пределами длины файла")
                self.warnings.append(f"⚠️ Блок на позиции {pos} за пределами длины файла")
            return pos
        if pos + 1 >= ln:
            self.logger.warning(f"Неполный блок на позиции {pos} (отсутствует байт счёта)")
            self.warnings.append(f"⚠️ Неполный блок на позиции {pos} (отсутствует байт счёта)")
            return pos + 1  # Пропускаем только маркер, если нет счёта
        count = data[pos + 1]
        skip = 2 + count * 4
        if pos + skip > ln:
            self.logger.warning(f"Блок на позиции {pos} превышает длину файла (count={count}, ожидаемая длина={skip}, доступно={ln - pos})")
            self.warnings.append(f"⚠️ Блок на позиции {pos} превышает длину файла (count={count}, ожидаемая длина={skip}, доступно={ln - pos})")
        self.logger.info(f"Пропуск блока на позиции {pos}, count={count}, длина={skip}")
        return min(pos + skip, ln)

    def parse(self):
        data = self.data
        ln = self.ln
        pos = 0
        # Проверка блока blink
        if ln > 0 and data[0] == 0x00:
            blink_start = pos
            pos = self._skip_block(data, pos)
            self.blink = data[blink_start:pos]
            self.logger.info(f"Блок blink распарсен, размер={len(self.blink)}, данные={self.blink.hex(' ').upper()}, pos={pos}")
        else:
            self.logger.warning(f"Файл не начинается с 0x00 — блок blink отсутствует или повреждён")
            self.warnings.append(f"⚠️ Файл не начинается с 0x00 — блок blink отсутствует или повреждён")

        # Проверка блока talk (всегда ожидается после blink)
        if pos < ln and data[pos] == 0x00:
            talk_start = pos
            pos = self._skip_block(data, pos)
            self.talk = data[talk_start:pos]
            self.logger.info(f"Блок talk распарсен, размер={len(self.talk)}, данные={self.talk.hex(' ').upper()}, pos={pos}")
        else:
            if pos < ln:
                self.logger.warning(f"Ожидался блок talk с 0x00 на позиции {pos}, но найдено {data[pos]:02X} — блок talk отсутствует")
                self.warnings.append(f"⚠️ Ожидался блок talk с 0x00 на позиции {pos}, но найдено {data[pos]:02X}")
            else:
                self.logger.warning(f"Достигнут конец файла после blink — блок talk отсутствует")
                self.warnings.append(f"⚠️ Достигнут конец файла после blink — блок talk отсутствует")

        # Палитра (32 байта) ожидается дальше
        if pos + 32 <= ln:
            self.palette = data[pos:pos+32]
            pos += 32
            self.logger.info(f"Палитра распарсена, размер={len(self.palette)}, данные={self.palette.hex(' ').upper()}, pos={pos}")
        else:
            self.logger.warning(f"Недостаточно данных для палитры (доступно {ln - pos} байт вместо 32)")
            self.warnings.append(f"⚠️ Недостаточно данных для палитры (доступно {ln - pos} байт вместо 32)")
            self.palette = data[pos:]
            pos = ln
            self.logger.info(f"Палитра распарсена (неполная), размер={len(self.palette)}, данные={self.palette.hex(' ').upper()}, pos={pos}")
        
        # Логируем данные перед байтами магии
        if pos < ln:
            self.logger.info(f"Данные перед байтами магии на позиции {pos}: {data[pos:min(pos+4, ln)].hex(' ').upper()}")
        
        # Байты магии (08 08) ожидается после палитры - ОСТАВЛЯЕМ ДЛЯ ДЕКОМПРЕССОРА!
        if pos + 2 <= ln:
            self.magic = data[pos:pos+2]
            self.logger.info(f"Чтение байтов магии на позиции {pos}: {self.magic.hex(' ').upper()}")
            if self.magic != b"\x08\x08":
                self.logger.warning(f"Ожидались байты магии 08 08, но найдено {self.magic.hex(' ').upper()} на позиции {pos}")
                self.warnings.append(f"⚠️ Ожидались байты магии 08 08, но найдено {self.magic.hex(' ').upper()} на позиции {pos}")
            else:
                self.logger.info(f"Найдены байты магии: {self.magic.hex().upper()}")
        else:
            self.magic = b""
            self.logger.warning(f"Байты магии не найдены (доступно {ln - pos} байт вместо 2)")
            self.warnings.append(f"⚠️ Байты магии не найдены (доступно {ln - pos} байт вместо 2)")
        
        # Графика начинается с байтов магии (08 08)
        self.graphic_offset = pos  # pos указывает на начало байтов магии
        self.logger.info(f"Смещение графики (включая байты магии): {pos}")

    def get_summary_text(self):
        lines = []
        lines.append(f"Размер: {self.ln} байт")
        lines.append("")
        lines.append("Blink:")
        if self.blink:
            lines.append(f"  Hex: {self.blink[:16].hex(' ').upper()}{' ...' if len(self.blink)>16 else ''}")
        else:
            lines.append("  Отсутствует")
        lines.append("Talk:")
        if self.talk:
            lines.append(f"  Hex: {self.talk[:16].hex(' ').upper()}{' ...' if len(self.talk)>16 else ''}")
        else:
            lines.append("  Отсутствует")
        lines.append(f"Палитра: {len(self.palette)} байт")
        if self.palette:
            # отображаем пары hex палитры
            pairs = [f"{self.palette[i]:02X} {self.palette[i+1]:02X}" for i in range(0, min(len(self.palette), 32), 2)]
            lines.append("  " + ", ".join(pairs))
        lines.append(f"Магия: {len(self.magic)} байт {self.magic.hex(' ').upper() if self.magic else ''}")
        lines.append(f"Смещение графики: {self.graphic_offset}")
        lines.append(f"Размер графики: {max(0, self.ln - (self.graphic_offset or self.ln))} байт")
        return "\n".join(lines)

    def save_rle(self, dest_path=None):
        """
        Сохраняет .bin файл с текущими полями blink/talk/palette.
        Если dest_path = None, перезаписывает оригинальный файл (self.bin_path).
        Этот метод реконструирует файл как:
          [байты blink] + [байты talk] + [палитра (32 байта)] + [остальное (с оригинального graphic_offset)]
        Сохраняет сжатую графику (байты магии + данные) без изменений.
        """
        try:
            if dest_path is None:
                dest_path = self.bin_path

            # Убедимся, что у нас есть оригинальные сырые данные
            original = getattr(self, 'data', None)
            if original is None:
                with open(self.bin_path, "rb") as f:
                    original = f.read()

            # Определяем graphic_offset; если отсутствует, пытаемся найти байты магии, иначе до конца
            graph_off = getattr(self, 'graphic_offset', None)
            if graph_off is None:
                idx = original.find(b'\x08\x08')
                graph_off = idx if idx != -1 else len(original)

            # Подготавливаем байты blink и talk (должны быть bytes)
            blink_bytes = self.blink if isinstance(self.blink, (bytes, bytearray)) else bytes(self.blink or b'')
            talk_bytes  = self.talk  if isinstance(self.talk,  (bytes, bytearray)) else bytes(self.talk or b'')

            # Подготавливаем палитру: ровно 32 байта (паддинг или обрезка)
            palette_bytes = getattr(self, 'palette', b'') or b''
            if len(palette_bytes) < 32:
                palette_bytes = palette_bytes + b'\x00' * (32 - len(palette_bytes))
            else:
                palette_bytes = palette_bytes[:32]

            # Остаток файла (начиная с graphic offset)
            rest = original[graph_off:] if graph_off < len(original) else b''

            new_data = bytearray()
            new_data.extend(blink_bytes)
            new_data.extend(talk_bytes)
            new_data.extend(palette_bytes)
            new_data.extend(rest)

            # Запись в destination
            with open(dest_path, "wb") as out:
                out.write(new_data)

            # Обновляем внутреннее состояние для соответствия новому файлу
            self.data = bytes(new_data)
            self.ln = len(self.data)
            # После перезаписи graphic_offset становится len(blink)+len(talk)+32
            self.graphic_offset = len(blink_bytes) + len(talk_bytes) + 32
            self.logger.info(f"Сохранён RLE .bin в {dest_path}, новый размер={self.ln}, graphic_offset={self.graphic_offset}")

            return dest_path

        except Exception as e:
            self.logger.error(f"Ошибка сохранения RLE файла: {str(e)}")
            raise

    def export_blocks_text(self):
        """Возвращает текстовый отчёт о blink/talk/palette/magic."""
        lines = []
        lines.append(f"Blink: {self.blink.hex(' ').upper() if self.blink else 'none'}")
        lines.append(f"Talk: {self.talk.hex(' ').upper() if self.talk else 'none'}")
        if self.palette:
            pairs = [f"{self.palette[i]:02X} {self.palette[i+1]:02X}" for i in range(0, len(self.palette), 2)]
            lines.append("Палитра (32 байта): " + ", ".join(pairs))
        else:
            lines.append("Палитра: none")
        lines.append(f"Магия: {self.magic.hex(' ').upper() if self.magic else 'none'}")
        return "\n".join(lines)