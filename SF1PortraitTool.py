# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import io
import os
from datetime import datetime
from SF1PortraitParser import SF1PortraitParser
from SF1PortraitDecompressor import SF1PortraitDecompressor
from SF1PortraitCompressor import SF1PortraitCompressor
from Lingua import LANGS
from RLEDecompressor import BitReader, read_palette_from_header, decompress_from_my_compressor
from RleParser import RleParser
from AnimationEditor import AnimationEditor

class PortraitViewerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("SF1 Portrait Tool")
        self.frame = tk.Frame(self.master)
        self.frame.pack(fill='both', expand=True)

        self.current_lang = 'ru'
        self.scale = 4  # initial zoom factor
        self.last_image = None
        self.last_log_text = ''
        self.last_file_path = ''
        self.last_parser = None
        self.last_palette = None  # Для хранения палитры PNG
        self.last_pixels = None   # Для хранения пиксельных данных PNG

        # Language selector с флагами
        lang_frame = tk.Frame(self.frame)
        lang_frame.pack(fill='x', pady=(0,5))
        tk.Label(lang_frame, text=LANGS[self.current_lang]['language']).pack(side=tk.LEFT)
        self.lang_var = tk.StringVar(value=self.get_lang_display(self.current_lang))
        lang_displays = [self.get_lang_display(lang) for lang in LANGS.keys()]
        lang_menu = ttk.Combobox(lang_frame, textvariable=self.lang_var, values=lang_displays, width=10)
        lang_menu.pack(side=tk.LEFT, padx=(5,0))
        lang_menu.bind('<<ComboboxSelected>>', self.change_language)

        # Buttons
        button_frame = tk.Frame(self.frame)
        button_frame.pack(fill='x', pady=5)
        self.btn_open = tk.Button(button_frame, text=LANGS[self.current_lang]['open_file'], command=self.open_file)
        self.btn_open.pack(side=tk.LEFT, padx=2)
        self.btn_open_portrait = tk.Button(button_frame, text=LANGS[self.current_lang]['open_portrait'], command=self.open_portrait)
        self.btn_open_portrait.pack(side=tk.LEFT, padx=2, pady=5)
        self.btn_open_png = tk.Button(button_frame, text=LANGS[self.current_lang]['open_png_file'], command=self.open_png)
        self.btn_open_png.pack(side=tk.LEFT, padx=2)
        self.btn_save_png = tk.Button(button_frame, text=LANGS[self.current_lang]['save_png'], command=self.save_image)
        self.btn_save_png.pack(side=tk.LEFT, padx=2)
        self.btn_save_log = tk.Button(button_frame, text=LANGS[self.current_lang]['save_log'], command=self.save_log)
        self.btn_save_log.pack(side=tk.LEFT, padx=2)
        self.btn_save_palette = tk.Button(button_frame, text=LANGS[self.current_lang]['palette'], command=self.save_palette)
        self.btn_save_palette.pack(side=tk.LEFT, padx=2)
        self.btn_save_bin = tk.Button(button_frame, text=LANGS[self.current_lang]['save_bin'], command=self.save_bin)
        self.btn_save_bin.pack(side=tk.LEFT, padx=2)
        self.btn_zoom_in = tk.Button(button_frame, text=LANGS[self.current_lang]['scale_up'], command=self.zoom_in)
        self.btn_zoom_in.pack(side=tk.LEFT, padx=2)
        self.btn_zoom_out = tk.Button(button_frame, text=LANGS[self.current_lang]['scale_down'], command=self.zoom_out)
        self.btn_zoom_out.pack(side=tk.LEFT, padx=2)
        self.btn_edit_anim = tk.Button(button_frame, text=LANGS[self.current_lang]['edit_animations'], command=self.edit_animations)
        self.btn_edit_anim.pack(side=tk.LEFT, padx=2)

        self.canvas = tk.Canvas(self.frame, width=64*self.scale, height=64*self.scale, bg='white')
        self.canvas.pack(pady=5)

        self.text = tk.Text(self.frame, wrap='word', height=15)
        self.text.pack(fill='both', expand=True, pady=5)

        self.status = tk.Label(self.frame, text='', anchor='w')
        self.status.pack(fill='x')

    def get_lang_display(self, lang):
        """Добавить флаг к коду языка"""
        flags = {
            'ru': '🇷🇺',
            'en': '🇬🇧',
            'it': '🇮🇹',
            'fr': '🇫🇷',
            'es': '🇪🇸',
            'ja': '🇯🇵',
            'pt': '🇵🇹',
            'el': '🇬🇷'
        }
        return f"{lang} {flags.get(lang, '')}"

    def change_language(self, event=None):
        selected = self.lang_var.get().split(' ')[0]
        self.current_lang = selected
        self.update_button_texts()

    def update_button_texts(self):
        self.btn_open.config(text=LANGS[self.current_lang]['open_file'])
        self.btn_open_portrait.config(text=LANGS[self.current_lang]['open_portrait'])
        self.btn_open_png.config(text=LANGS[self.current_lang]['open_png_file'])
        self.btn_save_png.config(text=LANGS[self.current_lang]['save_png'])
        self.btn_save_log.config(text=LANGS[self.current_lang]['save_log'])
        self.btn_save_palette.config(text=LANGS[self.current_lang]['palette'])
        self.btn_save_bin.config(text=LANGS[self.current_lang]['save_bin'])
        self.btn_zoom_in.config(text=LANGS[self.current_lang]['scale_up'])
        self.btn_zoom_out.config(text=LANGS[self.current_lang]['scale_down'])
        self.btn_edit_anim.config(text=LANGS[self.current_lang]['edit_animations'])

    def zoom_in(self):
        self.scale = min(10, self.scale + 1)
        self.redraw_image()

    def zoom_out(self):
        self.scale = max(1, self.scale - 1)
        self.redraw_image()

    def redraw_image(self):
        if self.last_image:
            display = self.last_image.resize((64*self.scale, 64*self.scale), Image.Resampling.NEAREST)
            self.photo = ImageTk.PhotoImage(display)
            self.canvas.config(width=64*self.scale, height=64*self.scale)
            self.canvas.delete('all')
            self.canvas.create_image((64*self.scale)//2, (64*self.scale)//2, image=self.photo, anchor='center')
            self.canvas.image = self.photo

    def build_image_sf1_linear(self, nibbles, palette):
        flat = [int(x, 16) if x != '' else 0 for x in nibbles[:64*64]]
        img = Image.new('RGBA', (64, 64))
        pixels = []
        for idx in range(64*64):
            if idx < len(flat):
                ci = flat[idx]
                if ci < len(palette):
                    pixels.append(palette[ci])
                else:
                    pixels.append((0,0,0,0))
            else:
                pixels.append((0,0,0,0))
        img.putdata(pixels)
        return img, len(flat)

    def open_file(self):
        file_path = filedialog.askopenfilename(title=LANGS[self.current_lang]['open_file'],
                                               filetypes=[('Binary files','*.bin'),('All files','*.*')])
        if file_path:
            try:
                self.last_file_path = file_path
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                parser = SF1PortraitParser(file_path)
                self.last_parser = parser
                graphic_offset = parser.graphic_offset if parser.graphic_offset is not None else 0
                
                if graphic_offset >= len(data):
                    raise ValueError(f"Графический offset ({graphic_offset}) больше размера файла ({len(data)})")
                
                file_stream = io.BytesIO(data)
                
                decompressor = SF1PortraitDecompressor(file_stream)
                nibbles, non_trans = decompressor.get_data(graphic_offset)
                
                palette_data = parser.palette if hasattr(parser, 'palette') else b''
                
                def decode_palette_genesis(palette_data):
                    pal = []
                    for i in range(16):
                        if i*2+1 >= len(palette_data):
                            pal.append((0,0,0,255))
                            continue
                        low = palette_data[i*2]
                        high = palette_data[i*2+1]
                        word = (low << 8) | high
                        r = ((word >> 0) & 0x0E) >> 1
                        g = ((word >> 4) & 0x0E) >> 1
                        b = ((word >> 8) & 0x0E) >> 1
                        scale = 255 // 7
                        r = r * scale
                        g = g * scale
                        b = b * scale
                        alpha = 0 if i == 0 else 255
                        pal.append((r,g,b,alpha))
                    return pal

                palette = decode_palette_genesis(palette_data)
                self.last_palette = palette
                img, _ = self.build_image_sf1_linear(nibbles, palette)
                self.last_image = img
                self.last_pixels = nibbles

                parser_summary = parser.get_summary_text() if hasattr(parser, 'get_summary_text') else ''
                self.last_log_text = parser_summary
                self.text.delete(1.0, tk.END)
                self.text.insert(tk.END, self.last_log_text)
                self.redraw_image()
                self.status.config(text=f"✅ Открыт портрет: {os.path.basename(file_path)} | {non_trans} пикселей")
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Полная ошибка: {error_details}")
                messagebox.showerror("Ошибка", f"Ошибка при загрузке файла:\n{str(e)}\n\nПроверь консоль для подробностей.")
                self.status.config(text=f"❌ Ошибка: {str(e)}")

    def open_portrait(self):
        file_path = filedialog.askopenfilename(title=LANGS[self.current_lang]['open_portrait'],
                                               filetypes=[('Binary files', '*.bin'), ('All files', '*.*')])
        if file_path:
            try:
                self.last_file_path = file_path
                with open(file_path, 'rb') as f:
                    data = f.read()

                parser = RleParser(file_path)
                self.last_parser = parser
                self.last_log_text = parser.get_summary_text()
                
                if len(parser.palette) != 32:
                    raise ValueError("Неполные или отсутствующие данные палитры в файле.")

                def decode_palette_genesis(palette_data):
                    pal = []
                    for i in range(0, 32, 2):
                        first = palette_data[i]
                        second = palette_data[i+1]
                        b_n = first & 0x0F
                        g_n = (second >> 4) & 0x0F
                        r_n = second & 0x0F
                        r = int(round(r_n * 255 / 15))  # Изменено на /15 без mapping
                        g = int(round(g_n * 255 / 15))
                        b = int(round(b_n * 255 / 15))
                        alpha = 0 if i == 0 else 255
                        pal.append((r, g, b, alpha))
                    return pal

                self.last_palette = decode_palette_genesis(parser.palette)

                graphic_data_offset = parser.graphic_offset
                if graphic_data_offset is None or graphic_data_offset >= len(data):
                    raise ValueError("Не удалось определить смещение графических данных.")

                file_stream = io.BytesIO(data)
                
                temp_png_path = "temp_decompressed.png"
                decompress_from_my_compressor(file_stream, temp_png_path)
                
                img = Image.open(temp_png_path).convert('RGBA')
                self.last_image = img
                
                pixels = list(img.getdata())
                color_map = {(r, g, b, a): i for i, (r, g, b, a) in enumerate(self.last_palette)}
                self.last_pixels = []
                for r, g, b, a in pixels:
                    if a == 0:
                        self.last_pixels.append('0')
                    else:
                        color_key = (r, g, b, a)
                        idx = color_map.get(color_key, 0)
                        self.last_pixels.append(f"{idx:X}")
                
                non_trans = sum(1 for px in pixels if px[3] != 0)
                
                self.text.delete(1.0, tk.END)
                self.text.insert(tk.END, self.last_log_text)
                self.redraw_image()
                self.status.config(text=f"✅ Открыт портрет (RLE): {os.path.basename(file_path)} | {non_trans} пикселей")
                
                os.remove(temp_png_path)
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Полная ошибка: {error_details}")
                messagebox.showerror("Ошибка", f"Ошибка при загрузке портрета (RLE7):\n{str(e)}\n\nПроверь консоль для подробностей.")
                self.status.config(text=f"❌ Ошибка: {str(e)}")

    def open_png(self):
        file_path = filedialog.askopenfilename(
            title=LANGS[self.current_lang]['open_png_file'],
            filetypes=[('PNG files', '*.png'), ('All files', '*.*')]
        )
        if file_path:
            try:
                img = Image.open(file_path).convert('RGBA')
                width, height = img.size
                if width != 64 or height != 64:
                    raise ValueError("Размер изображения должен быть 64x64 пикселей")
                
                pixels = list(img.getdata())
                colors = set(pixel[:3] for pixel in pixels if pixel[3] != 0)
                if len(colors) > 15:
                    raise ValueError("Максимум 16 цветов в палитре (включая прозрачный)")

                palette = [(0, 0, 0, 0)]
                color_map = {(0, 0, 0, 0): 0}
                for r, g, b, a in pixels:
                    if a == 0:
                        continue
                    color = (r // 36, g // 36, b // 36)
                    if color not in color_map and len(palette) < 16:
                        palette.append((r, g, b, 255))
                        color_map[color] = len(palette) - 1
                
                while len(palette) < 16:
                    palette.append((0, 0, 0, 0))

                indexed_pixels = []
                for r, g, b, a in pixels:
                    if a == 0:
                        indexed_pixels.append('0')
                    else:
                        color = (r // 36, g // 36, b // 36)
                        indexed_pixels.append(f"{color_map.get(color, 0):X}")

                self.last_image = img
                self.last_palette = palette
                self.last_pixels = indexed_pixels
                self.last_file_path = file_path
                self.last_parser = None

                total_pixels = 64*64
                non_trans_calc = sum(1 for px in pixels if px[3] != 0)
                palette_info = ', '.join([f"{i:02X} ({r},{g},{b},{a})" for i, (r, g, b, a) in enumerate(palette) if i < len(colors) + 1])
                self.last_log_text = f"Файл: {os.path.basename(file_path)}\nNon-transparent: {non_trans_calc} из {total_pixels}\n\nПалитра:\n{palette_info}\n"
                self.text.delete(1.0, tk.END)
                self.text.insert(tk.END, self.last_log_text)

                self.redraw_image()
                self.status.config(text=f"✅ Открыт PNG: {os.path.basename(file_path)} | {non_trans_calc} пикселей")

            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Полная ошибка: {error_details}")
                messagebox.showerror("Ошибка", f"Ошибка при загрузке PNG:\n{str(e)}\n\nПроверь консоль для подробностей.")
                self.status.config(text=f"❌ Ошибка: {str(e)}")

    def save_image(self):
        if not self.last_image:
            messagebox.showwarning("Предупреждение", "Сначала откройте портрет")
            return
        file_path = filedialog.asksaveasfilename(
            title=LANGS[self.current_lang]['save_png'],
            defaultextension='.png',
            filetypes=[('PNG files', '*.png'), ('All files', '*.*')]
        )
        if file_path:
            try:
                self.last_image.save(file_path)
                self.status.config(text=f"💾 Сохранено PNG: {os.path.basename(file_path)}")
                messagebox.showinfo("Успех", f"Сохранено PNG:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка сохранения PNG", str(e))

    def save_log(self):
        if not self.last_log_text:
            messagebox.showwarning("Предупреждение", "Сначала откройте портрет")
            return
        file_path = filedialog.asksaveasfilename(
            title=LANGS[self.current_lang]['save_log'],
            defaultextension='.txt',
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.last_log_text)
                self.status.config(text=f"📝 Сохранён лог: {os.path.basename(file_path)}")
                messagebox.showinfo("Успех", f"Сохранён лог:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка сохранения лога", str(e))

    def save_palette(self):
        if not self.last_palette:
            messagebox.showwarning("Предупреждение", "Сначала откройте портрет")
            return
        file_path = filedialog.asksaveasfilename(
            title=LANGS[self.current_lang]['palette'],
            defaultextension='.txt',
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for i, color in enumerate(self.last_palette):
                        f.write(f"Color {i:02X}: {color}\n")
                
                self.status.config(text=f"💾 Сохранена палитра: {os.path.basename(file_path)}")
                messagebox.showinfo("Успех", f"Сохранена палитра:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка сохранения палитры", str(e))

    def save_bin(self):
        """Сохранить текущее изображение как сжатый .bin файл"""
        if self.last_image:
            try:
                compressor = SF1PortraitCompressor(image=self.last_image)
                output_path = filedialog.asksaveasfilename(
                    title=LANGS[self.current_lang]['save_bin'],
                    defaultextension='.bin',
                    filetypes=[('Binary files', '*.bin'), ('All files', '*.*')]
                )
                if output_path:
                    compressor.compress(output_path)
                    self.status.config(text=f"💾 Сохранён BIN: {os.path.basename(output_path)}")
                    messagebox.showinfo("Успех", f"Сохранён BIN:\n{output_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при сжатии файла:\n{str(e)}")
        else:
            file_path = filedialog.askopenfilename(
                title=LANGS[self.current_lang]['open_png'],
                filetypes=[('PNG files', '*.png'), ('All files', '*.*')]
            )
            if file_path:
                try:
                    compressor = SF1PortraitCompressor(png_path=file_path)
                    output_path = filedialog.asksaveasfilename(
                        title=LANGS[self.current_lang]['save_bin'],
                        defaultextension='.bin',
                        filetypes=[('Binary files', '*.bin'), ('All files', '*.*')]
                    )
                    if output_path:
                        compressor.compress(output_path)
                        self.status.config(text=f"💾 Сохранён BIN: {os.path.basename(output_path)}")
                        messagebox.showinfo("Успех", f"Сохранён BIN:\n{output_path}")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Ошибка при сжатии файла:\n{str(e)}")

    def edit_animations(self):
        if not self.last_image:
            messagebox.showwarning("Предупреждение", "Сначала откройте портрет")
            return
        editor = AnimationEditor(self.master, self.last_parser, self.last_image, self.last_palette)
        # После редактирования обнови лог и изображение, если нужно

if __name__ == '__main__':
    try:
        root = tk.Tk()
        app = PortraitViewerApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Ошибка запуска: {str(e)}")
        with open(f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 'w', encoding='utf-8') as f:
            f.write(f"Ошибка запуска: {str(e)}\n")
