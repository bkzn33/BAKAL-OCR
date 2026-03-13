import os
import sys
import threading
import re

# ── Kivy config BEFORE any kivy import ──────────────────────────────────────
os.environ['KIVY_NO_CONSOLELOG'] = '1'

from kivy.config import Config
Config.set('graphics', 'width',  '420')
Config.set('graphics', 'height', '820')
Config.set('graphics', 'resizable', '1')
Config.set('input', 'mouse', 'mouse,disable_multitouch')

import cv2
import numpy as np
import pytesseract
from PIL import Image as PILImage

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image as KivyImage
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse, Line
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget

import tkinter as tk
from tkinter import filedialog

# ── Tesseract ────────────────────────────────────────────────────────────────
pytesseract.pytesseract.tesseract_cmd = (
    r'C:\Program Files\Tesseract-OCR\tesseract.exe'
)

# ── Theme ────────────────────────────────────────────────────────────────────
BG         = (0.05, 0.05, 0.07, 1)
CARD       = (0.10, 0.10, 0.13, 1)
SURFACE    = (0.14, 0.14, 0.18, 1)
SURFACE2   = (0.18, 0.18, 0.23, 1)
BLUE       = (0.22, 0.49, 0.97, 1)
BLUE_SOFT  = (0.22, 0.49, 0.97, 0.18)
GREEN      = (0.18, 0.82, 0.58, 1)
GREEN_SOFT = (0.18, 0.82, 0.58, 0.16)
ORANGE     = (0.98, 0.60, 0.18, 1)
ORANGE_SOFT= (0.98, 0.60, 0.18, 0.16)
RED_SOFT   = (0.95, 0.30, 0.30, 0.16)
RED        = (0.95, 0.30, 0.30, 1)
WHITE      = (1, 1, 1, 1)
W80        = (1, 1, 1, 0.80)
W50        = (1, 1, 1, 0.50)
W20        = (1, 1, 1, 0.20)
W08        = (1, 1, 1, 0.08)
NONE       = (0, 0, 0, 0)

Window.clearcolor = BG[:3] + (1,)

# ── Language configs ─────────────────────────────────────────────────────────
LANGUAGES = {
    'Auto Detect': 'eng+ara+fra',
    'English':     'eng',
    'Arabic (العربية)': 'ara',
    'French (Français)': 'fra',
    'English + Arabic': 'eng+ara',
    'English + French': 'eng+fra',
    'Arabic + French': 'ara+fra',
    'All Languages': 'eng+ara+fra',
}

TRANSLATE_LANGS = {
    'English':  'en',
    'Arabic':   'ar',
    'French':   'fr',
    'Spanish':  'es',
    'German':   'de',
}


# ── UI Primitives ─────────────────────────────────────────────────────────────
class RoundedBox(Widget):
    def __init__(self, color=CARD, radius=12, **kw):
        super().__init__(**kw)
        self._color  = color
        self._radius = radius
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._color)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[dp(self._radius)] * 4)


class PillButton(ButtonBehavior, FloatLayout):
    def __init__(self, text='', icon='', bg=BLUE, fg=WHITE,
                 font_size=14, radius=24, **kw):
        super().__init__(**kw)
        self._bg     = bg
        self._fg     = fg
        self._radius = radius
        self._lbl    = Label(
            text=f'{icon}  {text}' if icon else text,
            font_size=dp(font_size), color=fg, bold=True,
            halign='center', valign='middle',
            size_hint=(1, 1), pos_hint={'x': 0, 'y': 0},
        )
        self.bind(pos=self._draw, size=self._draw)
        self.add_widget(self._lbl)

    def _draw(self, *_):
        self.canvas.before.clear()
        self._lbl.size      = self.size
        self._lbl.pos       = self.pos
        self._lbl.text_size = self.size
        r = min(dp(self._radius), self.height / 2)
        with self.canvas.before:
            Color(*self._bg)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[r] * 4)

    def on_press(self):
        with self.canvas.before:
            Color(0, 0, 0, 0.2)
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[min(dp(self._radius), self.height/2)] * 4)

    def on_release(self):
        self._draw()


class CircleBtn(ButtonBehavior, Widget):
    def __init__(self, icon='', bg=SURFACE, fg=WHITE, sz=48, **kw):
        kw.setdefault('size', (dp(sz), dp(sz)))
        kw.setdefault('size_hint', (None, None))
        super().__init__(**kw)
        self._bg = bg
        self._lbl = Label(text=icon, font_size=dp(sz * 0.40),
                          color=fg, halign='center', valign='middle')
        self.add_widget(self._lbl)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.before.clear()
        self._lbl.pos = self.pos
        self._lbl.size = self.size
        self._lbl.text_size = self.size
        with self.canvas.before:
            Color(*self._bg)
            Ellipse(pos=self.pos, size=self.size)

    def on_press(self):
        with self.canvas.before:
            Color(1, 1, 1, 0.15)
            Ellipse(pos=self.pos, size=self.size)

    def on_release(self):
        self._draw()


class ScanFrame(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._t = 0.0
        self.bind(pos=self._draw, size=self._draw)
        Clock.schedule_interval(self._tick, 1 / 30)

    def _tick(self, dt):
        self._t = (self._t + dt * 0.35) % 1.0
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        c, t = dp(30), dp(3)
        with self.canvas:
            Color(*BLUE)
            Line(points=[x, y+h-c, x, y+h, x+c, y+h],       width=t, cap='round')
            Line(points=[x+w-c, y+h, x+w, y+h, x+w, y+h-c], width=t, cap='round')
            Line(points=[x, y+c, x, y, x+c, y],              width=t, cap='round')
            Line(points=[x+w-c, y, x+w, y, x+w, y+c],       width=t, cap='round')
            Color(0.22, 0.49, 0.97, 0.55)
            sy = y + self._t * h
            Line(points=[x+dp(10), sy, x+w-dp(10), sy], width=dp(2))


# ── Camera Screen ─────────────────────────────────────────────────────────────
class CameraScreen(FloatLayout):
    def __init__(self, on_capture=None, on_gallery=None, on_close=None, **kw):
        super().__init__(**kw)
        self._on_capture  = on_capture
        self._on_gallery  = on_gallery
        self._on_close    = on_close
        self._cap         = None
        self._last_frame  = None
        self._frame_event = None
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda w, _: setattr(self._bg, 'pos', w.pos),
                  size=lambda w, _: setattr(self._bg, 'size', w.size))

        self._preview = KivyImage(allow_stretch=True, keep_ratio=True,
                                   size_hint=(1, 1),
                                   pos_hint={'x': 0, 'y': 0})
        self.add_widget(self._preview)

        # Top bar
        top = BoxLayout(size_hint=(1, None), height=dp(68),
                        pos_hint={'x': 0, 'top': 1},
                        padding=[dp(16), dp(10)], spacing=dp(12))
        with top.canvas.before:
            Color(0, 0, 0, 0.6)
            r = Rectangle()
        top.bind(pos=lambda w, _: setattr(r, 'pos', w.pos),
                 size=lambda w, _: setattr(r, 'size', w.size))

        x_btn = CircleBtn('✕', bg=(1,1,1,0.2), sz=42)
        x_btn.bind(on_release=lambda _: self._close())
        top.add_widget(x_btn)
        top.add_widget(Label(text='Point at text', font_size=dp(16),
                             color=WHITE, bold=True))
        top.add_widget(Widget())
        self.add_widget(top)

        # Scan frame
        self.add_widget(ScanFrame(size_hint=(0.82, 0.50),
                                   pos_hint={'center_x': .5, 'center_y': .52}))

        # Hint
        self.add_widget(Label(text='Align text within the frame',
                              font_size=dp(12), color=W50,
                              size_hint=(1, None), height=dp(28),
                              pos_hint={'x': 0, 'center_y': .20},
                              halign='center'))

        # Bottom bar
        bot = BoxLayout(size_hint=(1, None), height=dp(115),
                        pos_hint={'x': 0, 'y': 0},
                        padding=[dp(28), dp(16)], spacing=dp(20))
        with bot.canvas.before:
            Color(0, 0, 0, 0.70)
            r2 = Rectangle()
        bot.bind(pos=lambda w, _: setattr(r2, 'pos', w.pos),
                 size=lambda w, _: setattr(r2, 'size', w.size))

        gal = CircleBtn('🖼', bg=(1,1,1,0.18), sz=54)
        gal.bind(on_release=lambda _: self._gallery())
        bot.add_widget(gal)

        wrap = BoxLayout(size_hint=(1, 1))
        shutter = CircleBtn('⬤', bg=WHITE, fg=BG, sz=70)
        shutter.bind(on_release=lambda _: self._capture())
        wrap.add_widget(Widget())
        wrap.add_widget(shutter)
        wrap.add_widget(Widget())
        bot.add_widget(wrap)
        bot.add_widget(Widget(size_hint=(None, None), size=(dp(54), dp(54))))
        self.add_widget(bot)

    def start(self):
        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(1)
        self._frame_event = Clock.schedule_interval(self._tick, 1/30)

    def stop(self):
        if self._frame_event:
            self._frame_event.cancel()
            self._frame_event = None
        if self._cap:
            self._cap.release()
            self._cap = None

    def _tick(self, dt):
        if not self._cap or not self._cap.isOpened():
            return
        ret, frame = self._cap.read()
        if not ret:
            return
        self._last_frame = frame
        rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        flip = cv2.flip(rgb, 0)
        h, w, _ = flip.shape
        tex = Texture.create(size=(w, h), colorfmt='rgb')
        tex.blit_buffer(flip.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        self._preview.texture = tex

    def _capture(self):
        if self._last_frame is not None:
            path = 'captured_photo.jpg'
            cv2.imwrite(path, self._last_frame)
            self.stop()
            if self._on_capture:
                self._on_capture(path)

    def _gallery(self):
        self.stop()
        path = _pick_file()
        if path and self._on_gallery:
            self._on_gallery(path)
        elif self._on_close:
            self._on_close()

    def _close(self):
        self.stop()
        if self._on_close:
            self._on_close()


def _pick_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    p = filedialog.askopenfilename(
        title='Select image',
        filetypes=[('Images', '*.jpg *.jpeg *.png *.bmp *.tiff *.webp'),
                   ('All', '*.*')])
    root.destroy()
    return p or None


# ── OCR helpers ───────────────────────────────────────────────────────────────
def preprocess(image_path):
    img = cv2.imread(image_path)
    if img is None:
        pil = PILImage.open(image_path).convert('RGB')
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

    h, w = img.shape[:2]
    if w < 1600:
        s   = 1600 / w
        img = cv2.resize(img, None, fx=s, fy=s,
                         interpolation=cv2.INTER_CUBIC)

    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray  = clahe.apply(gray)
    gray  = cv2.fastNlMeansDenoising(gray, h=12)
    kern  = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    gray  = cv2.filter2D(gray, -1, kern)
    _, bw = cv2.threshold(gray, 0, 255,
                          cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    km    = np.ones((2, 2), np.uint8)
    bw    = cv2.morphologyEx(bw, cv2.MORPH_OPEN, km)
    return PILImage.fromarray(bw)


def run_ocr(image_path, lang_code):
    pil = preprocess(image_path)
    configs = [
        f'--oem 3 --psm 6 -l {lang_code}',
        f'--oem 3 --psm 3 -l {lang_code}',
        f'--oem 3 --psm 11 -l {lang_code}',
        f'--oem 3 --psm 4 -l {lang_code}',
    ]
    best = ''
    for cfg in configs:
        try:
            r = pytesseract.image_to_string(pil, config=cfg).strip()
            if len(r) > len(best):
                best = r
        except Exception:
            pass

    lines = best.splitlines()
    clean = []
    for ln in lines:
        if not ln.strip():
            continue
        alnum = sum(c.isalnum() or c.isspace() for c in ln)
        if len(ln) == 0 or alnum / len(ln) > 0.38:
            clean.append(ln)
    return '\n'.join(clean).strip()


def translate_text(text, target_lang):
    """Free translation via MyMemory API (no key needed)."""
    import urllib.request
    import urllib.parse
    import json

    if not text.strip():
        return ''

    # Split into chunks ≤ 500 chars for the free API
    chunks     = []
    words      = text.split()
    chunk      = ''
    for w in words:
        if len(chunk) + len(w) + 1 > 490:
            chunks.append(chunk.strip())
            chunk = ''
        chunk += w + ' '
    if chunk.strip():
        chunks.append(chunk.strip())

    translated = []
    for ch in chunks:
        try:
            q   = urllib.parse.quote(ch)
            url = (f'https://api.mymemory.translated.net/get'
                   f'?q={q}&langpair=auto|{target_lang}')
            with urllib.request.urlopen(url, timeout=6) as resp:
                data = json.loads(resp.read().decode())
                translated.append(
                    data['responseData']['translatedText'])
        except Exception:
            translated.append(ch)   # fallback: original

    return ' '.join(translated)


# ── Tab button ────────────────────────────────────────────────────────────────
class TabBtn(ButtonBehavior, Widget):
    def __init__(self, text, active=False, on_activate=None, **kw):
        super().__init__(**kw)
        self._text      = text
        self._active    = active
        self._cb        = on_activate
        self._lbl = Label(text=text, font_size=dp(13),
                          halign='center', valign='middle',
                          bold=active)
        self.add_widget(self._lbl)
        self.bind(pos=self._draw, size=self._draw)

    def set_active(self, v):
        self._active    = v
        self._lbl.bold  = v
        self._draw()

    def _draw(self, *_):
        self.canvas.before.clear()
        self._lbl.pos       = self.pos
        self._lbl.size      = self.size
        self._lbl.text_size = self.size
        self._lbl.color     = WHITE if self._active else W50
        with self.canvas.before:
            if self._active:
                Color(*BLUE)
                RoundedRectangle(pos=self.pos, size=self.size,
                                 radius=[dp(20)] * 4)

    def on_release(self):
        if self._cb:
            self._cb()


# ── Main screen ───────────────────────────────────────────────────────────────
class MainScreen(FloatLayout):

    def __init__(self, **kw):
        super().__init__(**kw)
        self._cam_screen  = None
        self._ocr_text    = ''
        self._active_tab  = 'ocr'   # 'ocr' | 'translate'
        self._build()

    # ─────────────────────────────────────────────────────────────────
    def _build(self):
        with self.canvas.before:
            Color(*BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg_rect, 'pos', self.pos),
                  size=lambda *_: setattr(self._bg_rect, 'size', self.size))

        root = BoxLayout(orientation='vertical', size_hint=(1, 1),
                         spacing=0, padding=0)

        root.add_widget(self._build_header())
        root.add_widget(self._build_preview())
        root.add_widget(self._build_action_row())
        root.add_widget(self._build_lang_row())
        root.add_widget(self._build_status_row())
        root.add_widget(self._build_tab_bar())
        root.add_widget(self._build_content_area())

        self.add_widget(root)

    # ── Header ───────────────────────────────────────────────────────
    def _build_header(self):
        bar = BoxLayout(size_hint=(1, None), height=dp(66),
                        padding=[dp(18), dp(10), dp(18), dp(6)],
                        spacing=dp(10))
        with bar.canvas.before:
            Color(*BG)
            r = Rectangle()
        bar.bind(pos=lambda w, _: setattr(r, 'pos', w.pos),
                 size=lambda w, _: setattr(r, 'size', w.size))

        # Logo area
        logo_box = BoxLayout(size_hint=(None, None),
                             size=(dp(110), dp(38)),
                             spacing=dp(6))

        # Colored squares logo
        dot_widget = Widget(size_hint=(None, None), size=(dp(32), dp(32)))
        with dot_widget.canvas:
            # B square
            Color(0.22, 0.49, 0.97, 1)
            RoundedRectangle(pos=(dot_widget.x, dot_widget.y + dp(16)),
                             size=(dp(14), dp(14)), radius=[dp(3)]*4)
            # A square
            Color(0.18, 0.82, 0.58, 1)
            RoundedRectangle(pos=(dot_widget.x + dp(16), dot_widget.y + dp(16)),
                             size=(dp(14), dp(14)), radius=[dp(3)]*4)
            # K square
            Color(0.98, 0.60, 0.18, 1)
            RoundedRectangle(pos=(dot_widget.x, dot_widget.y),
                             size=(dp(14), dp(14)), radius=[dp(3)]*4)
            # A square
            Color(0.95, 0.30, 0.30, 1)
            RoundedRectangle(pos=(dot_widget.x + dp(16), dot_widget.y),
                             size=(dp(14), dp(14)), radius=[dp(3)]*4)
        logo_box.add_widget(dot_widget)

        name_col = BoxLayout(orientation='vertical', size_hint=(None, None),
                             size=(dp(68), dp(32)), spacing=0)
        name_col.add_widget(Label(text='BAKAL', font_size=dp(16),
                                  bold=True, color=WHITE,
                                  halign='left', valign='bottom',
                                  size_hint=(1, None), height=dp(18)))
        name_col.add_widget(Label(text='OCR & Translate', font_size=dp(9),
                                  color=W50, halign='left', valign='top',
                                  size_hint=(1, None), height=dp(12)))
        logo_box.add_widget(name_col)
        bar.add_widget(logo_box)
        bar.add_widget(Widget())

        # Version badge
        badge = BoxLayout(size_hint=(None, None), size=(dp(42), dp(22)),
                          padding=[dp(6), dp(2)])
        with badge.canvas.before:
            Color(*BLUE_SOFT)
            RoundedRectangle(pos=badge.pos, size=badge.size,
                             radius=[dp(10)]*4)
        badge.bind(pos=lambda w, _: (
            w.canvas.before.clear(),
            w.canvas.before.__enter__(),
            Color(*BLUE_SOFT).__class__,  # noop
        ))
        bar.add_widget(Label(text='v2.0', font_size=dp(11),
                             color=BLUE, bold=True,
                             size_hint=(None, None), size=(dp(42), dp(22))))
        return bar

    # ── Preview card ─────────────────────────────────────────────────
    def _build_preview(self):
        wrap = BoxLayout(size_hint=(1, None), height=dp(200),
                         padding=[dp(14), dp(4), dp(14), dp(4)])

        card = FloatLayout()
        with card.canvas.before:
            Color(*CARD)
            self._preview_rect = RoundedRectangle(radius=[dp(18)]*4)
        card.bind(
            pos=lambda w, _: setattr(self._preview_rect, 'pos', w.pos),
            size=lambda w, _: setattr(self._preview_rect, 'size', w.size))

        self._preview_img = KivyImage(allow_stretch=True, keep_ratio=True,
                                       size_hint=(1, 1),
                                       pos_hint={'x': 0, 'y': 0})
        card.add_widget(self._preview_img)

        self._preview_hint = Label(
            text='📷  Tap Camera or Gallery to start',
            font_size=dp(13), color=W20,
            halign='center', valign='middle',
            size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        card.add_widget(self._preview_hint)

        wrap.add_widget(card)
        return wrap

    # ── Action buttons ────────────────────────────────────────────────
    def _build_action_row(self):
        row = BoxLayout(size_hint=(1, None), height=dp(52),
                        padding=[dp(14), 0], spacing=dp(10))

        cam = PillButton('Camera', '📷', bg=BLUE,
                         font_size=14, radius=24, size_hint=(1, 1))
        cam.bind(on_release=lambda _: self._open_camera())
        row.add_widget(cam)

        gal = PillButton('Gallery', '🖼', bg=SURFACE,
                         fg=WHITE, font_size=14, radius=24,
                         size_hint=(1, 1))
        gal.bind(on_release=lambda _: self._open_gallery())
        row.add_widget(gal)

        return row

    # ── Language row ──────────────────────────────────────────────────
    def _build_lang_row(self):
        row = BoxLayout(size_hint=(1, None), height=dp(48),
                        padding=[dp(14), dp(6)], spacing=dp(8))

        row.add_widget(Label(text='OCR Lang:', font_size=dp(12),
                             color=W50, size_hint=(None, 1),
                             width=dp(72), halign='right',
                             valign='middle'))

        self._lang_spinner = Spinner(
            text='Auto Detect',
            values=list(LANGUAGES.keys()),
            font_size=dp(13),
            size_hint=(1, None),
            height=dp(36),
            background_color=SURFACE,
            color=WHITE,
            option_cls='SpinnerOption',
        )
        row.add_widget(self._lang_spinner)
        return row

    # ── Status row ────────────────────────────────────────────────────
    def _build_status_row(self):
        row = BoxLayout(size_hint=(1, None), height=dp(30),
                        padding=[dp(18), 0])
        self._status_lbl = Label(
            text='Ready — select an image to scan',
            font_size=dp(12), color=W50,
            halign='left', valign='middle')
        self._status_lbl.bind(
            size=lambda w, _: setattr(w, 'text_size', w.size))
        row.add_widget(self._status_lbl)
        return row

    # ── Tab bar ───────────────────────────────────────────────────────
    def _build_tab_bar(self):
        bar = BoxLayout(size_hint=(1, None), height=dp(42),
                        padding=[dp(14), dp(4)], spacing=dp(8))

        tab_wrap = BoxLayout(size_hint=(None, 1), width=dp(220),
                             spacing=0)
        with tab_wrap.canvas.before:
            Color(*SURFACE)
            self._tab_bg = RoundedRectangle(radius=[dp(22)]*4)
        tab_wrap.bind(
            pos=lambda w, _: setattr(self._tab_bg, 'pos', w.pos),
            size=lambda w, _: setattr(self._tab_bg, 'size', w.size))

        self._tab_ocr = TabBtn(
            'Extracted Text', active=True,
            on_activate=lambda: self._switch_tab('ocr'),
            size_hint=(1, 1))
        self._tab_tr = TabBtn(
            'Translation', active=False,
            on_activate=lambda: self._switch_tab('translate'),
            size_hint=(1, 1))
        tab_wrap.add_widget(self._tab_ocr)
        tab_wrap.add_widget(self._tab_tr)
        bar.add_widget(tab_wrap)
        bar.add_widget(Widget())

        # Copy button
        self._copy_btn = PillButton('Copy', '📋',
                                    bg=GREEN_SOFT, fg=GREEN,
                                    font_size=13, radius=18,
                                    size_hint=(None, None),
                                    size=(dp(90), dp(34)))
        self._copy_btn.bind(on_release=lambda _: self._copy())
        bar.add_widget(self._copy_btn)
        return bar

    # ── Content area ──────────────────────────────────────────────────
    def _build_content_area(self):
        self._content_stack = BoxLayout(
            orientation='vertical', size_hint=(1, 1))

        # ── OCR pane
        self._ocr_pane = BoxLayout(
            orientation='vertical', size_hint=(1, 1))

        ocr_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self._ocr_input = TextInput(
            hint_text='Extracted text will appear here...',
            hint_text_color=W20,
            font_size=dp(15),
            multiline=True,
            background_color=NONE,
            foreground_color=WHITE,
            cursor_color=BLUE,
            size_hint=(1, None),
            height=dp(300),
            padding=[dp(18), dp(10)],
        )
        self._ocr_input.bind(
            minimum_height=self._ocr_input.setter('height'))
        ocr_scroll.add_widget(self._ocr_input)
        self._ocr_pane.add_widget(ocr_scroll)

        # ── Translate pane
        self._tr_pane = BoxLayout(
            orientation='vertical', size_hint=(1, 1), spacing=0)

        tr_header = BoxLayout(size_hint=(1, None), height=dp(44),
                              padding=[dp(14), dp(6)], spacing=dp(8))
        tr_header.add_widget(Label(text='Translate to:', font_size=dp(12),
                                   color=W50, size_hint=(None, 1),
                                   width=dp(84)))
        self._tr_lang_spinner = Spinner(
            text='English',
            values=list(TRANSLATE_LANGS.keys()),
            font_size=dp(13),
            size_hint=(1, None),
            height=dp(32),
            background_color=SURFACE,
            color=WHITE,
        )
        tr_header.add_widget(self._tr_lang_spinner)

        tr_btn = PillButton('Translate', '🌐',
                            bg=ORANGE_SOFT, fg=ORANGE,
                            font_size=13, radius=16,
                            size_hint=(None, None),
                            size=(dp(110), dp(32)))
        tr_btn.bind(on_release=lambda _: self._translate())
        tr_header.add_widget(tr_btn)
        self._tr_pane.add_widget(tr_header)

        tr_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self._tr_input = TextInput(
            hint_text='Translation will appear here...',
            hint_text_color=W20,
            font_size=dp(15),
            multiline=True,
            background_color=NONE,
            foreground_color=WHITE,
            cursor_color=ORANGE,
            size_hint=(1, None),
            height=dp(280),
            padding=[dp(18), dp(10)],
        )
        self._tr_input.bind(
            minimum_height=self._tr_input.setter('height'))
        tr_scroll.add_widget(self._tr_input)
        self._tr_pane.add_widget(tr_scroll)

        self._content_stack.add_widget(self._ocr_pane)
        return self._content_stack

    # ── Tab switch ────────────────────────────────────────────────────
    def _switch_tab(self, tab):
        self._active_tab = tab
        self._tab_ocr.set_active(tab == 'ocr')
        self._tab_tr.set_active(tab == 'translate')
        self._content_stack.clear_widgets()
        if tab == 'ocr':
            self._content_stack.add_widget(self._ocr_pane)
        else:
            self._content_stack.add_widget(self._tr_pane)

    # ── Camera / Gallery ──────────────────────────────────────────────
    def _open_camera(self):
        self._status('Opening camera...')
        self._cam_screen = CameraScreen(
            on_capture=self._on_photo,
            on_gallery=self._on_gallery_img,
            on_close=self._close_camera,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
        )
        self.add_widget(self._cam_screen)
        self._cam_screen.start()

    def _close_camera(self):
        if self._cam_screen:
            self._cam_screen.stop()
            self.remove_widget(self._cam_screen)
            self._cam_screen = None
        self._status('Ready — select an image to scan')

    def _on_photo(self, path):
        self._close_camera()
        self._process(path)

    def _open_gallery(self):
        self._status('Opening gallery...')
        path = _pick_file()
        if path:
            self._on_gallery_img(path)
        else:
            self._status('No file selected')

    def _on_gallery_img(self, path):
        self._process(path)

    # ── OCR processing ────────────────────────────────────────────────
    def _process(self, path):
        self._status('Processing image...')
        self._preview_img.source = path
        self._preview_img.reload()
        self._preview_hint.opacity = 0
        lang = LANGUAGES.get(self._lang_spinner.text, 'eng+ara+fra')
        t = threading.Thread(target=self._ocr_thread,
                             args=(path, lang))
        t.daemon = True
        t.start()

    def _ocr_thread(self, path, lang):
        try:
            text = run_ocr(path, lang)
            self._ocr_text = text
            words = len(text.split()) if text else 0
            lines = len([l for l in text.splitlines() if l.strip()]) if text else 0
            if text:
                st = f'✓  Done — {words} words · {lines} lines'
            else:
                st = '⚠  No text detected — try better lighting'

            def upd(dt):
                self._status(st)
                self._ocr_input.text = text
                self._tr_input.text  = ''

            Clock.schedule_once(upd)
        except Exception as e:
            Clock.schedule_once(
                lambda dt: self._status(f'Error: {e}'))

    # ── Translation ───────────────────────────────────────────────────
    def _translate(self):
        src = self._ocr_input.text.strip()
        if not src:
            self._status('⚠  No text to translate — run OCR first')
            return
        target = TRANSLATE_LANGS.get(self._tr_lang_spinner.text, 'en')
        self._status('Translating...')
        self._tr_input.text = 'Translating...'

        def _thread():
            result = translate_text(src, target)

            def upd(dt):
                self._tr_input.text = result
                self._status(f'✓  Translated to {self._tr_lang_spinner.text}')

            Clock.schedule_once(upd)

        t = threading.Thread(target=_thread)
        t.daemon = True
        t.start()

    # ── Copy ──────────────────────────────────────────────────────────
    def _copy(self):
        if self._active_tab == 'ocr':
            text = self._ocr_input.text.strip()
        else:
            text = self._tr_input.text.strip()

        if text and text != 'Translating...':
            Clipboard.copy(text)
            old = self._status_lbl.text
            self._status('✓  Copied to clipboard!')
            Clock.schedule_once(lambda dt: self._status(old), 2)
        else:
            self._status('Nothing to copy yet')

    # ── Status helper ─────────────────────────────────────────────────
    def _status(self, msg):
        self._status_lbl.text = msg


# ── App ───────────────────────────────────────────────────────────────────────
class BakalApp(App):
    title = 'BAKAL OCR'

    def build(self):
        Window.clearcolor = BG[:3] + (1,)
        return MainScreen()


if __name__ == '__main__':
    BakalApp().run()