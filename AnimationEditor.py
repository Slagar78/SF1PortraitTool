# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk

# таблицы преобразования SF1
SF1_TILE_TO_COORD = {
    (0x00,0x28):(6,0),
    (0x00,0x2C):(7,0),
    (0x00,0x29):(6,1),
    (0x00,0x2D):(7,1),
    (0x00,0x2A):(6,2),
    (0x00,0x2E):(7,2),
    (0x00,0x2B):(6,3),
    (0x00,0x2F):(7,3),
}
COORD_TO_SF1_TILE = {v:k for k,v in SF1_TILE_TO_COORD.items()}

class AnimationEditor:
    def __init__(self, parent, parser, image, palette):
        self.parent = parent
        self.parser = parser
        self.image = image
        self.palette = palette
        self.blink_frames = self.parse_animation('blink') if parser else []
        self.talk_frames = self.parse_animation('talk') if parser else []
        self.selected_tile = None
        self.current_anim_type = tk.StringVar(value='blink')  # текущий тип анимации

        self.window = tk.Toplevel(parent)
        self.window.title("Edit Animations")
        self.window.geometry("1000x600")

        # выбор анимации
        choice_frame = tk.Frame(self.window)
        choice_frame.pack()
        tk.Label(choice_frame, text="Animation type:").pack(side=tk.LEFT)
        tk.Radiobutton(choice_frame, text="Blink", variable=self.current_anim_type,
                       value='blink', command=self.refresh_table).pack(side=tk.LEFT)
        tk.Radiobutton(choice_frame, text="Talk", variable=self.current_anim_type,
                       value='talk', command=self.refresh_table).pack(side=tk.LEFT)

        self.scale = 4  # увеличиваем, чтобы было видно
        self.canvas_size = 64*self.scale
        cell = self.scale*8

        # рамка для цифр + Canvas
        frame_canvas = tk.Frame(self.window)
        frame_canvas.pack(side=tk.LEFT, padx=5, pady=5)

        # цифры сверху
        top_numbers = tk.Frame(frame_canvas)
        top_numbers.pack()
        tk.Label(top_numbers, width=4).grid(row=0,column=0)  # угол пустой
        for i in range(8):
            tk.Label(top_numbers, text=str(i), width=4).grid(row=0,column=i+1)

        # цифры слева + canvas
        main_frame = tk.Frame(frame_canvas)
        main_frame.pack()
        left_numbers = tk.Frame(main_frame)
        left_numbers.pack(side=tk.LEFT)
        for i in range(8):
            tk.Label(left_numbers, text=str(i), height=2).grid(row=i,column=0)

        # сам Canvas
        self.canvas = tk.Canvas(main_frame, width=self.canvas_size, height=self.canvas_size)
        self.canvas.pack(side=tk.LEFT)
        self.render_canvas()
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # таблица кадров
        table_frame = tk.LabelFrame(self.window, text="Frames (X,Y,X',Y')")
        table_frame.pack(side=tk.TOP, padx=5, pady=5, fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(table_frame, columns=("X","Y","X'","Y'"), show='headings', height=15)
        for col in ("X","Y","X'","Y'"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=50, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        # спинбоксы для редактирования кадра
        edit_frame = tk.LabelFrame(self.window, text="Edit selected frame")
        edit_frame.pack(side=tk.TOP, pady=5)
        tk.Label(edit_frame, text="X").grid(row=0,column=0)
        self.var_x = tk.StringVar()
        self.spin_x = tk.Spinbox(edit_frame, from_=0, to=5, width=3, textvariable=self.var_x)
        self.spin_x.grid(row=0,column=1)
        tk.Label(edit_frame, text="Y").grid(row=0,column=2)
        self.var_y = tk.StringVar()
        self.spin_y = tk.Spinbox(edit_frame, from_=0, to=7, width=3, textvariable=self.var_y)
        self.spin_y.grid(row=0,column=3)
        tk.Label(edit_frame, text="X'").grid(row=0,column=4)
        self.var_x2 = tk.StringVar()
        self.spin_x2 = tk.Spinbox(edit_frame, from_=6, to=7, width=3, textvariable=self.var_x2)
        self.spin_x2.grid(row=0,column=5)
        tk.Label(edit_frame, text="Y'").grid(row=0,column=6)
        self.var_y2 = tk.StringVar()
        self.spin_y2 = tk.Spinbox(edit_frame, from_=0, to=3, width=3, textvariable=self.var_y2)
        self.spin_y2.grid(row=0,column=7)
        tk.Button(edit_frame, text="Apply Values", command=self.apply_spinbox_values).grid(row=0,column=8,padx=5)

        # trace для реального времени обновления подсветки
        self.var_x.trace('w', self.update_highlight_from_spins)
        self.var_y.trace('w', self.update_highlight_from_spins)
        self.var_x2.trace('w', self.update_highlight_from_spins)
        self.var_y2.trace('w', self.update_highlight_from_spins)

        # кнопки
        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Add Frame", command=self.add_frame).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete Frame", command=self.delete_frame).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Apply Tile", command=self.apply_selected_tile).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Save", command=self.save_changes).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", command=self.window.destroy).pack(side=tk.LEFT, padx=5)

        self.refresh_table()

    def parse_animation(self, anim_type):
        data = self.parser.blink if anim_type == 'blink' else self.parser.talk
        if len(data) < 2 or data[0] != 0:
            return []
        frame_count = data[1]
        frames = []
        pos = 2
        for _ in range(frame_count):
            if pos+3 >= len(data): break
            x = data[pos]; y = data[pos+1]
            x2 = data[pos+2]; y2 = data[pos+3]
            # проверка SF1-кодов
            if (x,y) in SF1_TILE_TO_COORD:
                x,y = SF1_TILE_TO_COORD[(x,y)]
            if (x2,y2) in SF1_TILE_TO_COORD:
                x2,y2 = SF1_TILE_TO_COORD[(x2,y2)]
            frames.append((x,y,x2,y2))
            pos += 4
        return frames

    def render_canvas(self):
        """Отрисовывает портрет + сетку"""
        self.canvas.delete("all")
        display = self.image.resize((self.canvas_size, self.canvas_size), Image.NEAREST)
        self.photo = ImageTk.PhotoImage(display)
        self.canvas.create_image(0, 0, image=self.photo, anchor='nw')
        # сетка 8x8
        cell = self.scale*8
        for i in range(9):
            self.canvas.create_line(i*cell, 0, i*cell, self.canvas_size, fill="gray")
            self.canvas.create_line(0, i*cell, self.canvas_size, i*cell, fill="gray")
        # рамка аним. плиток (x=6–7,y=0–3)
        for y in range(4):
            for x in range(6,8):
                self.canvas.create_rectangle(x*cell, y*cell,
                                             (x+1)*cell, (y+1)*cell,
                                             outline="gray", width=2)

    def on_canvas_click(self, event):
        """Выбор плитки по клику"""
        cell = self.scale*8
        x = event.x // cell
        y = event.y // cell
        if x>=8 or y>=8: return
        self.selected_tile = (x,y)

    def highlight_tiles(self, x, y, x2, y2):
        cell = self.scale*8
        self.canvas.delete("highlight")
        # Обход неверных координат
        try:
            self.canvas.create_rectangle(x*cell,y*cell,(x+1)*cell,(y+1)*cell,
                                         outline="blue",width=3,tags="highlight")
        except Exception:
            pass
        try:
            self.canvas.create_rectangle(x2*cell,y2*cell,(x2+1)*cell,(y2+1)*cell,
                                         outline="green",width=3,tags="highlight")
        except Exception:
            pass

    def refresh_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        frames = self.blink_frames if self.current_anim_type.get()=='blink' else self.talk_frames
        for fr in frames:
            self.tree.insert('', tk.END, values=fr)

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        values = self.tree.item(sel[0],'values')
        # значения могут быть str; приводим к int/str корректно
        vx = int(values[0]); vy = int(values[1]); vx2 = int(values[2]); vy2 = int(values[3])
        self.var_x.set(str(vx))
        self.var_y.set(str(vy))
        self.var_x2.set(str(vx2))
        self.var_y2.set(str(vy2))
        self.highlight_tiles(vx, vy, vx2, vy2)

    def update_highlight_from_spins(self, *args):
        try:
            x = max(0, min(7, int(self.var_x.get())))
            y = max(0, min(7, int(self.var_y.get())))
            x2 = max(6, min(7, int(self.var_x2.get())))
            y2 = max(0, min(3, int(self.var_y2.get())))
            self.highlight_tiles(x, y, x2, y2)
        except ValueError:
            # если значение не int, игнорируем
            pass

    def apply_spinbox_values(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        frames = self.blink_frames if self.current_anim_type.get()=='blink' else self.talk_frames
        x = max(0,min(7,int(self.var_x.get())))
        y = max(0,min(7,int(self.var_y.get())))
        x2 = max(6,min(7,int(self.var_x2.get())))
        y2 = max(0,min(3,int(self.var_y2.get())))
        frames[idx] = (x,y,x2,y2)
        self.refresh_table()

    def add_frame(self):
        frames = self.blink_frames if self.current_anim_type.get()=='blink' else self.talk_frames
        frames.append((0,0,6,0))
        self.refresh_table()

    def delete_frame(self):
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        frames = self.blink_frames if self.current_anim_type.get()=='blink' else self.talk_frames
        del frames[idx]
        self.refresh_table()

    def apply_selected_tile(self):
        """Присвоить X',Y' кадру по выбранному тайлу"""
        if not self.selected_tile:
            messagebox.showinfo("Info","Выберите плитку")
            return
        sel = self.tree.selection()
        if not sel: return
        idx = self.tree.index(sel[0])
        frames = self.blink_frames if self.current_anim_type.get()=='blink' else self.talk_frames
        x,y,x2,y2 = frames[idx]
        tile_x, tile_y = self.selected_tile
        frames[idx] = (x,y,tile_x,tile_y)
        self.refresh_table()

    def save_changes(self):
        """
        Обновляем parser.blink/talk в памяти и сохраняем .bin на диск.
        """
        blink_new = self.encode_animation(self.blink_frames)
        talk_new = self.encode_animation(self.talk_frames)
        if self.parser:
            # обновляем в памяти
            self.parser.blink = blink_new
            self.parser.talk = talk_new
            # пытаемся записать в файл (перезаписать оригинальный .bin)
            try:
                saved_path = self.parser.save_sf1()  # по умолчанию перезапишет исходный файл
                # после сохранения можно повторно распарсить, чтобы внутреннее состояние соответствовало файлу
                try:
                    self.parser.parse()
                except Exception:
                    # не критично, главное что файл записан
                    pass
                self.refresh_table()
                messagebox.showinfo("Сохранено", f"Анимации обновлены и записаны в файл:\n{saved_path}")
            except Exception as e:
                messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить .bin: {e}")
        else:
            messagebox.showinfo("Сохранено","Анимации обновлены в памяти (parser отсутствует).")

    def encode_animation(self, frames):
        data = bytearray()
        data.append(0x00)
        # count must fit in one byte
        count = len(frames)
        if count > 255:
            raise ValueError("Too many frames (>255)")
        data.append(count)
        for x,y,x2,y2 in frames:
            # если координаты “особые” – кодируем в SF1 байты
            if (x,y) in COORD_TO_SF1_TILE:
                bx,by = COORD_TO_SF1_TILE[(x,y)]
            else:
                bx,by = int(x), int(y)
            if (x2,y2) in COORD_TO_SF1_TILE:
                bx2,by2 = COORD_TO_SF1_TILE[(x2,y2)]
            else:
                bx2,by2 = int(x2), int(y2)
            data.extend([int(bx) & 0xFF, int(by) & 0xFF, int(bx2) & 0xFF, int(by2) & 0xFF])
        return bytes(data)