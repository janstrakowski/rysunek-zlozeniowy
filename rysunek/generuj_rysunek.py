#!/usr/bin/env python3
"""Rysunek złożeniowy: wałek z kołem zębatym, wpustem, wkrętami i pierścieniem.

Arkusz A3, podziałka 1:1, rzutowanie europejskie (metoda E).
Wymiary w mm. Geometria odtworzona z rysunków elementów i dobrana wg
PN-M-85005, PN-EN ISO 7434 oraz PN-M-85101.
"""

from __future__ import annotations

import math
import os

import pymupdf

# --- arkusz -----------------------------------------------------------------
W_MM, H_MM = 420.0, 297.0
PT = 72.0 / 25.4  # mm -> pt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ZL-01_wal_kolo_zebate.pdf")

FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

# grubości linii, mm
THICK = 0.50
THIN = 0.18
FRAME = 0.70
MID = 0.30

BLACK = (0, 0, 0)

# położenie widoku głównego: odsadzenie czopa na osi
OX, OY = 214.0, 198.0
# środek przekroju A-A
SX, SY = 108.0, 198.0
SCALE = 1.0  # 1:1


def P(x, y):
    return pymupdf.Point(x * PT, (H_MM - y) * PT)


class Draw:
    def __init__(self, page):
        self.page = page
        self.page.insert_font(fontname="sans", fontfile=FONT_REG)
        self.page.insert_font(fontname="sansb", fontfile=FONT_BOLD)
        self._fonts = {
            "sans": pymupdf.Font(fontfile=FONT_REG),
            "sansb": pymupdf.Font(fontfile=FONT_BOLD),
        }

    def line(self, x1, y1, x2, y2, w=THICK, dashes=None):
        sh = self.page.new_shape()
        sh.draw_line(P(x1, y1), P(x2, y2))
        kw = dict(color=BLACK, width=w * PT, closePath=False, lineCap=0, lineJoin=0)
        if dashes:
            kw["dashes"] = dashes
        sh.finish(**kw)
        sh.commit()

    def poly(self, pts, w=THICK, fill=None, close=False, dashes=None):
        if len(pts) < 2:
            return
        sh = self.page.new_shape()
        sh.draw_polyline([P(x, y) for x, y in pts])
        kw = dict(
            color=BLACK,
            width=0.01 if fill and w == 0 else w * PT,
            closePath=close,
            lineCap=0,
            lineJoin=0,
        )
        if fill is not None:
            kw["fill"] = fill
            kw["even_odd"] = False
        if dashes:
            kw["dashes"] = dashes
        sh.finish(**kw)
        sh.commit()

    def circle(self, cx, cy, r, w=THICK, dashes=None):
        sh = self.page.new_shape()
        sh.draw_circle(P(cx, cy), r * PT)
        kw = dict(color=BLACK, width=w * PT, lineCap=0)
        if dashes:
            kw["dashes"] = dashes
        sh.finish(**kw)
        sh.commit()

    def arc(self, cx, cy, r, a0, a1, w=THICK, dashes=None, steps=None):
        """Łuk, kąty w stopniach, 0° = +X, przeciwnie do ruchu wskazówek (y w górę)."""
        if steps is None:
            steps = max(8, int(abs(a1 - a0) / 4))
        pts = []
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        self.poly(pts, w=w, dashes=dashes)

    def text(self, x, y, s, size=3.5, align="left", bold=False, valign="base"):
        font = "sansb" if bold else "sans"
        fs = size * PT
        width = self._fonts[font].text_length(s, fontsize=fs)
        if align == "center":
            x = x - (width / PT) / 2
        elif align == "right":
            x = x - width / PT
        if valign == "mid":
            y = y - size * 0.35
        self.page.insert_text(
            P(x, y),
            s,
            fontname=font,
            fontsize=fs,
            color=BLACK,
        )

    def text_width(self, s, size=3.5, bold=False):
        font = "sansb" if bold else "sans"
        return self._fonts[font].text_length(s, fontsize=size * PT) / PT

    # --- linia punktowa (oś) ------------------------------------------------
    def centerline(self, x1, y1, x2, y2):
        # kreska 8, przerwa 1.2, kropka 0.4, przerwa 1.2  (w mm -> pt)
        pat = f"[{8 * PT:.2f} {1.15 * PT:.2f} {0.45 * PT:.2f} {1.15 * PT:.2f}] 0"
        self.line(x1, y1, x2, y2, w=THIN, dashes=pat)

    def dashdot_limited(self, x1, y1, x2, y2):
        """Linia punktowa o krótszym rytmie — okrąg podziałowy."""
        pat = f"[{4.5 * PT:.2f} {0.9 * PT:.2f} {0.35 * PT:.2f} {0.9 * PT:.2f}] 0"
        self.line(x1, y1, x2, y2, w=THIN, dashes=pat)

    # --- kreskowanie --------------------------------------------------------
    def hatch_poly(self, polygon, spacing=2.0, angle=45):
        if len(polygon) < 3:
            return
        th = math.radians(angle)
        ct, st = math.cos(th), math.sin(th)

        def rot(x, y):
            return (x * ct + y * st, -x * st + y * ct)

        def inv(xr, yr):
            return (xr * ct - yr * st, xr * st + yr * ct)

        rp = [rot(x, y) for x, y in polygon]
        ys = [p[1] for p in rp]
        y_lo, y_hi = min(ys), max(ys)
        n = len(rp)
        y = y_lo + spacing * 0.45
        while y < y_hi - 0.05:
            hits = []
            for i in range(n):
                xA, yA = rp[i]
                xB, yB = rp[(i + 1) % n]
                # półotwarty przedział, żeby wierzchołek liczył się raz
                if (yA <= y < yB) or (yB <= y < yA):
                    if abs(yB - yA) < 1e-9:
                        continue
                    t = (y - yA) / (yB - yA)
                    hits.append(xA + t * (xB - xA))
            hits.sort()
            # usuń dublety
            cleaned = []
            for h in hits:
                if not cleaned or abs(h - cleaned[-1]) > 0.05:
                    cleaned.append(h)
            for i in range(0, len(cleaned) - 1, 2):
                xa, xb = cleaned[i], cleaned[i + 1]
                if xb - xa < 0.35:
                    continue
                p1 = inv(xa, y)
                p2 = inv(xb, y)
                self.line(p1[0], p1[1], p2[0], p2[1], w=THIN)
            y += spacing

    def hatch_test(self, pred, bbox, spacing=2.0, angle=45, step=0.35):
        """Kreskowanie obszaru zadanego predykatem (x, y) -> bool. bbox = (x0,y0,x1,y1)."""
        x0, y0, x1, y1 = bbox
        th = math.radians(angle)
        ct, st = math.cos(th), math.sin(th)
        # prostokąt opisany w układzie obróconym
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        rc = [(x * ct + y * st, -x * st + y * ct) for x, y in corners]
        yr = [p[1] for p in rc]
        xr = [p[0] for p in rc]
        y_lo, y_hi = min(yr), max(yr)
        x_lo, x_hi = min(xr), max(xr)

        def inv(xr_, yr_):
            return (xr_ * ct - yr_ * st, xr_ * st + yr_ * ct)

        y = y_lo + spacing * 0.4
        while y < y_hi:
            # próbuj wzdłuż odcinka
            length = x_hi - x_lo
            n = max(2, int(length / step))
            inside_prev = None
            run_start = None
            for i in range(n + 1):
                xr_ = x_lo + (x_hi - x_lo) * i / n
                px, py = inv(xr_, y)
                inside = pred(px, py) if (x0 - 1 <= px <= x1 + 1 and y0 - 1 <= py <= y1 + 1) else False
                if inside_prev is None:
                    inside_prev = inside
                    if inside:
                        run_start = (px, py)
                    continue
                if inside != inside_prev:
                    # doprecyzuj granicę
                    lo_i = i - 1
                    hi_i = i
                    for _ in range(10):
                        mid = (lo_i + hi_i) / 2
                        mx = x_lo + (x_hi - x_lo) * mid / n
                        qx, qy = inv(mx, y)
                        if pred(qx, qy):
                            if inside:
                                hi_i = mid
                            else:
                                lo_i = mid
                        else:
                            if inside:
                                lo_i = mid
                            else:
                                hi_i = mid
                    bx = x_lo + (x_hi - x_lo) * ((lo_i + hi_i) / 2) / n
                    bp = inv(bx, y)
                    if inside:
                        run_start = bp
                    else:
                        if run_start is not None:
                            if math.hypot(bp[0] - run_start[0], bp[1] - run_start[1]) > 0.4:
                                self.line(run_start[0], run_start[1], bp[0], bp[1], w=THIN)
                        run_start = None
                    inside_prev = inside
            y += spacing

    # --- wymiary ------------------------------------------------------------
    def _arrow(self, x, y, ang):
        """Wypełniony grot. ang = kierunek grotu (dokąd wskazuje), stopnie."""
        a = math.radians(ang)
        L, W = 3.2, 0.85
        x1 = x - L * math.cos(a) + W * math.sin(a)
        y1 = y - L * math.sin(a) - W * math.cos(a)
        x2 = x - L * math.cos(a) - W * math.sin(a)
        y2 = y - L * math.sin(a) + W * math.cos(a)
        self.poly([(x, y), (x1, y1), (x2, y2)], w=0.04, fill=BLACK, close=True)

    def dim_h(self, x1, x2, y, text, ext_from=None, ext_to=None, text_size=3.5):
        """Wymiar poziomy. ext_from/to: y początku linii pomocniczych (przy obiekcie)."""
        if x2 < x1:
            x1, x2 = x2, x1
            if ext_from is not None and ext_to is not None:
                ext_from, ext_to = ext_to, ext_from
        gap = 1.0
        over = 2.0
        if ext_from is not None:
            y0 = ext_from
            sgn = 1 if y > y0 else -1
            self.line(x1, y0 + sgn * gap, x1, y + sgn * over, w=THIN)
        if ext_to is not None:
            y0 = ext_to
            sgn = 1 if y > y0 else -1
            self.line(x2, y0 + sgn * gap, x2, y + sgn * over, w=THIN)
        span = x2 - x1
        tw = self.text_width(text, text_size)
        # tekst w przerwie linii, jeśli się mieści
        if span > tw + 8:
            mid = (x1 + x2) / 2
            self.line(x1, y, mid - tw / 2 - 1.2, y, w=THIN)
            self.line(mid + tw / 2 + 1.2, y, x2, y, w=THIN)
            self._arrow(x1, y, 180)
            self._arrow(x2, y, 0)
            self.text(mid, y + 0.9, text, size=text_size, align="center")
        else:
            self.line(x1, y, x2, y, w=THIN)
            self._arrow(x1, y, 0)
            self._arrow(x2, y, 180)
            self.line(x1, y, x1 - 6, y, w=THIN)
            self.text(x1 - 6.6, y + 0.9, text, size=text_size, align="right")

    def dim_v(self, y1, y2, x, text, ext_from=None, ext_to=None, text_size=3.5, text_side="right"):
        if y2 < y1:
            y1, y2 = y2, y1
            if ext_from is not None and ext_to is not None:
                ext_from, ext_to = ext_to, ext_from
        gap = 1.0
        over = 2.0
        if ext_from is not None:
            x0 = ext_from
            sgn = 1 if x > x0 else -1
            self.line(x0 + sgn * gap, y1, x + sgn * over, y1, w=THIN)
        if ext_to is not None:
            x0 = ext_to
            sgn = 1 if x > x0 else -1
            self.line(x0 + sgn * gap, y2, x + sgn * over, y2, w=THIN)
        span = y2 - y1
        self.line(x, y1, x, y2, w=THIN)
        self._arrow(x, y1, -90)
        self._arrow(x, y2, 90)
        # tekst poziomy obok linii
        if text_side == "right":
            self.text(x + 1.6, (y1 + y2) / 2 - 1.2, text, size=text_size, align="left", valign="mid")
        else:
            self.text(x - 1.6, (y1 + y2) / 2 - 1.2, text, size=text_size, align="right", valign="mid")

    def leader_dot(self, x1, y1, x2, y2):
        self.line(x1, y1, x2, y2, w=THIN)
        self.circle_fill(x2, y2, 0.7)

    def circle_fill(self, cx, cy, r):
        sh = self.page.new_shape()
        sh.draw_circle(P(cx, cy), r * PT)
        sh.finish(color=BLACK, fill=BLACK, width=0.2, closePath=True)
        sh.commit()

    def balloon(self, cx, cy, n, tx, ty, r=4.2):
        # linia od brzegu kółka do punktu, kropka na elemencie
        ang = math.atan2(ty - cy, tx - cx)
        x_edge = cx + r * math.cos(ang)
        y_edge = cy + r * math.sin(ang)
        self.line(x_edge, y_edge, tx, ty, w=THIN)
        self.circle_fill(tx, ty, 0.65)
        self.circle(cx, cy, r, w=THIN)
        self.text(cx, cy - 1.15, str(n), size=3.5, align="center", bold=True)


def model_to_paper(x, y):
    return (OX + x * SCALE, OY + y * SCALE)


def draw_main(d: Draw):
    """Przekrój wzdłużny przez oś wału, wpust (góra) i wkręty (dół koła, góra pierścienia)."""

    def M(x, y):
        return model_to_paper(x, y)

    # ---- kreskowanie koła (45°) ----
    # wieńce i piasta ponad rowkiem wpustu
    polys_gear = [
        # górny wieniec pod wrębem
        [(0.3, 23.15), (24.7, 23.15), (24.7, 29.7), (0.3, 29.7)],
        # górna piasta (ponad dnem rowka 19.2)
        [(0.3, 19.55), (38.7, 19.55), (38.7, 22.85), (0.3, 22.85)],
        # dolny wieniec
        [(0.3, -29.7), (24.7, -29.7), (24.7, -23.15), (0.3, -23.15)],
        # dolna piasta na lewo od wkrętu (wkręt x = 28..36)
        [(0.3, -22.85), (27.7, -22.85), (27.7, -16.35), (0.3, -16.35)],
        # dolna piasta na prawo od wkrętu
        [(36.3, -22.85), (38.7, -22.85), (38.7, -16.9), (36.3, -16.9)],
    ]
    for poly in polys_gear:
        d.hatch_poly([M(x, y) for x, y in poly], spacing=2.0, angle=45)

    # pierścień — kreskowanie przeciwne (135°)
    polys_ring = [
        # dół, pełny
        [(39.9, -25.6), (54.1, -25.6), (54.1, -17.3), (39.9, -17.3)],
        # góra, lewo od wkrętu (x wkrętu 43..51)
        [(39.9, 17.4), (42.7, 17.4), (42.7, 25.6), (39.9, 25.6)],
        # góra, prawo od wkrętu
        [(51.3, 17.4), (54.1, 17.4), (54.1, 25.6), (51.3, 25.6)],
    ]
    for poly in polys_ring:
        d.hatch_poly([M(x, y) for x, y in poly], spacing=2.0, angle=135)

    # ---- osie ----
    d.centerline(*M(-30, 0), *M(66, 0))

    # okrąg podziałowy na zębie (cienka linia punktowa), tylko na szerokości wieńca
    d.dashdot_limited(*M(0, 33), *M(25, 33))
    d.dashdot_limited(*M(0, -33), *M(25, -33))

    # linia dna wrębu / granica kreskowania Ø60 — gruba, jak na rysunku elementu
    d.line(*M(0, 30), *M(25, 30), w=THICK)
    d.line(*M(0, -30), *M(25, -30), w=THICK)

    # ---- wał ----
    # czop Ø45 urywany
    d.line(*M(-24, 22.5), *M(0, 22.5), w=THICK)
    d.line(*M(-24, -22.5), *M(0, -22.5), w=THICK)
    # urwanie wałka (łukowa linia przerwania)
    br = []
    for i in range(41):
        t = i / 40
        yy = 22.5 - 45.0 * t
        xx = -24 + 2.4 * math.sin(t * 2 * math.pi)
        br.append(M(xx, yy))
    d.poly(br, w=THICK)

    # odsadzenie
    d.line(*M(0, 22.5), *M(0, 19.2), w=THICK)  # góra, do dna rowka piasty (styk)
    d.line(*M(0, -22.5), *M(0, -17), w=THICK)

    # czop Ø32 — góra, rowek wpustu
    d.line(*M(0, 16), *M(3.75, 16), w=THICK)
    d.line(*M(3.75, 16), *M(3.75, 12), w=THICK)
    d.line(*M(3.75, 12), *M(28.75, 12), w=THICK)
    d.line(*M(28.75, 12), *M(28.75, 16), w=THICK)
    # powierzchnia czopa przerwana gniazdem wkrętu pierścienia (x = 45..49)
    d.line(*M(28.75, 16), *M(45, 16), w=THICK)
    d.line(*M(49, 16), *M(58, 16), w=THICK)
    # fazka 2×45° i czoło
    d.line(*M(58, 16), *M(60, 14), w=THICK)
    d.line(*M(60, 14), *M(60, -14), w=THICK)
    d.line(*M(60, -14), *M(58, -16), w=THICK)
    # dół czopa, z gniazdem stożkowym 90° pod wkręt poz. 4
    d.line(*M(0, -16), *M(28.8, -16), w=THICK)
    d.line(*M(28.8, -16), *M(32, -12.8), w=THICK)
    d.line(*M(32, -12.8), *M(35.2, -16), w=THICK)
    d.line(*M(35.2, -16), *M(58, -16), w=THICK)
    # gniazdo pod wkręt pierścienia, góra czopa
    d.line(*M(45, 16), *M(47, 14), w=THICK)
    d.line(*M(47, 14), *M(49, 16), w=THICK)

    # ---- wpust (niekreśkowany) ----
    d.poly(
        [
            M(3.75, 12),
            M(28.75, 12),
            M(28.75, 19.0),
            M(3.75, 19.0),
        ],
        w=THICK,
        close=True,
    )
    # luz 0,2 mm pod dnem rowka piasty zaznaczony odcinkiem dna
    d.line(*M(0, 19.2), *M(39, 19.2), w=THICK)

    # ---- koło zębate, zarys ----
    # góra
    d.line(*M(0, 36), *M(25, 36), w=THICK)
    d.line(*M(25, 36), *M(25, 23), w=THICK)
    d.line(*M(25, 23), *M(39, 23), w=THICK)
    d.line(*M(39, 23), *M(39, 19.2), w=THICK)
    d.line(*M(0, 36), *M(0, 19.2), w=THICK)
    # dół
    d.line(*M(0, -36), *M(25, -36), w=THICK)
    d.line(*M(25, -36), *M(25, -23), w=THICK)
    d.line(*M(25, -23), *M(39, -23), w=THICK)
    d.line(*M(39, -23), *M(39, -17), w=THICK)
    d.line(*M(39, -17), *M(38, -16), w=THICK)  # fazka otworu 1×45°
    d.line(*M(0, -36), *M(0, -17), w=THICK)
    d.line(*M(0, -17), *M(1, -16), w=THICK)
    # otwór dolny, przerwany wkrętem
    d.line(*M(1, -16), *M(28, -16), w=THICK)
    d.line(*M(36, -16), *M(38, -16), w=THICK)

    # ---- wkręt dociskowy M8×10 w kole (poz. 4), koniec stożkowy 90° ----
    # trzpień Ø8 od powierzchni wału do czoła (l = 10 liczone do wierzchołka)
    # wierzchołek w wierzchołku gniazda y=-12.8; czoło y=-22.8
    d.line(*M(28, -16.0), *M(28, -22.8), w=THICK)
    d.line(*M(36, -16.0), *M(36, -22.8), w=THICK)
    d.line(*M(28, -22.8), *M(36, -22.8), w=THICK)
    # stożek z = 3, podstawa Ø6
    d.line(*M(29, -15.8), *M(32, -12.8), w=THICK)
    d.line(*M(35, -15.8), *M(32, -12.8), w=THICK)
    d.line(*M(29, -15.8), *M(28, -16.0), w=THICK)
    d.line(*M(35, -15.8), *M(36, -16.0), w=THICK)
    # rowek wkrętaka n=1,2  t=2
    d.line(*M(31.4, -22.8), *M(31.4, -20.8), w=THICK)
    d.line(*M(32.6, -22.8), *M(32.6, -20.8), w=THICK)
    d.line(*M(31.4, -20.8), *M(32.6, -20.8), w=THICK)
    # średnica rdzenia gwintu (cienka), 0,8·d = 6,4
    d.line(*M(28.8, -20.6), *M(28.8, -16.2), w=THIN)
    d.line(*M(35.2, -20.6), *M(35.2, -16.2), w=THIN)
    # oś wkrętu
    d.centerline(*M(32, -11.5), *M(32, -24.5))

    # ---- pierścień osadczy typ A 32 ----
    # zarys zewnętrzny, przerwany wkrętem u góry
    d.line(*M(39, -26), *M(55, -26), w=THICK)
    d.line(*M(55, -26), *M(55, 26), w=THICK)
    d.line(*M(39, -26), *M(39, 26), w=THICK)
    d.line(*M(39, 26), *M(43, 26), w=THICK)
    d.line(*M(51, 26), *M(55, 26), w=THICK)
    # fazki otworu s = 1,6 × 45°
    d.line(*M(39, -17.6), *M(40.6, -16), w=THICK)
    d.line(*M(40.6, -16), *M(53.4, -16), w=THICK)
    d.line(*M(53.4, -16), *M(55, -17.6), w=THICK)
    d.line(*M(39, 17.6), *M(40.6, 16), w=THICK)
    d.line(*M(40.6, 16), *M(43, 16), w=THICK)
    d.line(*M(51, 16), *M(53.4, 16), w=THICK)
    d.line(*M(53.4, 16), *M(55, 17.6), w=THICK)
    # boki wkrętu przecinają ściankę — pionowe odcinki otworu zasłania wkręt

    # ---- wkręt M8×12 w pierścieniu (poz. 6) ----
    d.line(*M(43, 17), *M(43, 26), w=THICK)
    d.line(*M(51, 17), *M(51, 26), w=THICK)
    d.line(*M(43, 26), *M(51, 26), w=THICK)
    d.line(*M(44, 17), *M(47, 14), w=THICK)
    d.line(*M(50, 17), *M(47, 14), w=THICK)
    d.line(*M(44, 17), *M(43, 17), w=THICK)
    d.line(*M(50, 17), *M(51, 17), w=THICK)
    # rowek
    d.line(*M(46.4, 26), *M(46.4, 24), w=THICK)
    d.line(*M(47.6, 26), *M(47.6, 24), w=THICK)
    d.line(*M(46.4, 24), *M(47.6, 24), w=THICK)
    d.line(*M(43.8, 24.2), *M(43.8, 17.2), w=THIN)
    d.line(*M(50.2, 24.2), *M(50.2, 17.2), w=THIN)
    d.centerline(*M(47, 13), *M(47, 28.5))

    # płaszczyzna przekroju A-A (przez środek wpustu), groty w lewo
    xA = 16.25
    d.line(*M(xA, 37), *M(xA, 43), w=MID)
    d.line(*M(xA, -37), *M(xA, -43), w=MID)
    d._arrow(*M(xA, 43), 180)
    d._arrow(*M(xA, -43), 180)
    d.text(*M(xA - 3.2, 44.2), "A", size=5, align="right", bold=True)
    d.text(*M(xA - 3.2, -45.6), "A", size=5, align="right", bold=True)


def draw_section(d: Draw):
    """Przekrój A-A poprzeczny przez wpust (x = 16,25 mm od odsadzenia)."""
    cx, cy = SX, SY

    def L(x, y):
        return (cx + x, cy + y)

    # kreskowanie wieńca: pierścień r=16..30 z wycięciem rowka
    def in_mat(x, y):
        dx, dy = x - cx, y - cy
        r2 = dx * dx + dy * dy
        if r2 > 30.0 * 30.0 or r2 < 16.0 * 16.0:
            return False
        if abs(dx) <= 4.0 and 16.0 <= dy <= 19.2:
            return False
        return True

    d.hatch_test(in_mat, (cx - 31, cy - 31, cx + 31, cy + 31), spacing=2.0, angle=45)

    # okręgi: wierzchołków Ø72 gruba, podziałowa Ø66 punktowa, dna Ø60 cienka
    d.circle(cx, cy, 36, w=THICK)
    # podziałowa jako łuk pełny linią punktową — rysowana odcinkami łuku
    pat = f"[{3.2 * PT:.2f} {0.8 * PT:.2f} {0.3 * PT:.2f} {0.8 * PT:.2f}] 0"
    d.circle(cx, cy, 33, w=THIN, dashes=pat)
    d.circle(cx, cy, 30, w=THIN)

    # rowek w piaście
    y_bore = math.sqrt(16.0 ** 2 - 4.0 ** 2)  # 15.49
    d.line(*L(-4, 19.2), *L(4, 19.2), w=THICK)
    d.line(*L(-4, 19.2), *L(-4, y_bore), w=THICK)
    d.line(*L(4, 19.2), *L(4, y_bore), w=THICK)
    # łuk otworu (większa część okręgu)
    a_right = math.degrees(math.atan2(y_bore, 4))  # ~75.5°
    a_left = math.degrees(math.atan2(y_bore, -4))  # ~104.5°
    # od prawej krawędzi rowka, dołem, do lewej: z 75.5° w dół do -180 i do 104.5? 
    # kąt punktu (4, 15.49) = 75.5°, punktu (-4, 15.49) = 180-75.5 = 104.5°.
    # łuk otworu idzie od 75.5° malejąco przez 0, -90, -180/180 do 104.5°.
    d.arc(cx, cy, 16, a_right, a_right - (360 - (a_left - a_right)), w=THICK, steps=72)

    # wał z rowkiem (niekreśkowany)
    d.arc(cx, cy, 16, a_right, a_right - (360 - (a_left - a_right)), w=THICK, steps=72)
    d.line(*L(-4, y_bore), *L(-4, 12), w=THICK)
    d.line(*L(4, y_bore), *L(4, 12), w=THICK)
    d.line(*L(-4, 12), *L(4, 12), w=THICK)

    # wpust 8×7, fazki 0,8×45°
    d.poly(
        [
            L(-3.2, 12),
            L(3.2, 12),
            L(4.0, 12.8),
            L(4.0, 18.2),
            L(3.2, 19.0),
            L(-3.2, 19.0),
            L(-4.0, 18.2),
            L(-4.0, 12.8),
        ],
        w=THICK,
        close=True,
    )

    # osie
    d.centerline(cx - 42, cy, cx + 42, cy)
    d.centerline(cx, cy - 42, cx, cy + 42)

    d.text(cx, cy - 44, "A–A", size=4.5, align="center", bold=True)


def draw_dimensions(d: Draw):
    # długość czopa 60 — od płaszczyzny oporowej do czoła
    d.dim_h(
        OX + 0,
        OX + 60,
        OY + 60,
        "60",
        ext_from=OY + 36,
        ext_to=OY + 14,
    )
    # Ø72 — gabaryt. Tekst nad górnym grotem, żeby nie nachodził na pasowanie.
    x72 = OX + 96
    d.line(OX + 25, OY + 36, x72 + 2, OY + 36, w=THIN)
    d.line(OX + 25, OY - 36, x72 + 2, OY - 36, w=THIN)
    d.line(x72, OY - 36, x72, OY + 36, w=THIN)
    d._arrow(x72, OY + 36, 90)
    d._arrow(x72, OY - 36, -90)
    d.text(x72 + 2.2, OY + 38.2, "Ø72", size=3.5, align="left")
    # pasowanie czopa — odnośnik pod wałem, poniżej linii wymiarowej Ø72
    d.line(OX + 57, OY - 16, OX + 80, OY - 46, w=THIN)
    d.line(OX + 80, OY - 46, OX + 124, OY - 46, w=THIN)
    d.circle_fill(OX + 57, OY - 16, 0.55)
    d.text(OX + 82, OY - 44.6, "Ø32 H8/js7", size=3.5, align="left")
    # Ø45 odsadzenia
    d.dim_v(
        OY - 22.5,
        OY + 22.5,
        OX - 38,
        "Ø45",
        ext_from=OX - 14,
        ext_to=OX - 14,
        text_side="left",
    )
    # średnica podziałowa — wymiar pomocniczy, z lewej strony przekroju
    d.line(SX - 23.3, SY + 23.3, SX - 42, SY + 44, w=THIN)
    d.line(SX - 42, SY + 44, SX - 62, SY + 44, w=THIN)
    d.text(SX - 63, SY + 42.6, "(Ø66)", size=3.2, align="right")


def draw_balloons(d: Draw):
    # 1 wałek
    d.balloon(OX - 22, OY + 34, 1, OX - 12, OY + 22.5)
    # 2 koło zębate — lewy róg wieńca
    d.balloon(OX - 30, OY + 48, 2, OX + 1, OY + 34)
    # 3 wpust — pas między wymiarem 60 a linią Ø72
    d.balloon(OX + 34, OY + 48, 3, OX + 16, OY + 19.0)
    # 5 pierścień — prawe czoło, z dala od wkrętu
    d.balloon(OX + 86, OY + 48, 5, OX + 55, OY + 14)
    # 6 wkręt pierścienia
    d.balloon(OX + 78, OY + 8, 6, OX + 51, OY + 22)
    # 4 wkręt koła
    d.balloon(OX + 52, OY - 50, 4, OX + 34, OY - 22.8)


def draw_cutting_note(d: Draw):
    d.text(SX, SY + 46, "A", size=5, align="center", bold=True)


def draw_frame_and_tables(d: Draw):
    # ramka
    L, B, R, T = 20, 10, 410, 287
    d.poly([(L, B), (R, B), (R, T), (L, T)], w=FRAME, close=True)

    # tabliczka 190 × 42, prawy dolny róg
    x0, y0, tw, th = 220, 10, 190, 44
    d.poly([(x0, y0), (x0 + tw, y0), (x0 + tw, y0 + th), (x0, y0 + th)], w=MID, close=True)
    # podziały tabliczki
    d.line(x0, y0 + 16, x0 + tw, y0 + 16, w=THIN)
    d.line(x0, y0 + 30, x0 + tw, y0 + 30, w=THIN)
    d.line(x0 + 28, y0 + 30, x0 + 28, y0 + th, w=THIN)
    d.line(x0 + 78, y0 + 30, x0 + 78, y0 + th, w=THIN)
    d.line(x0 + 118, y0 + 30, x0 + 118, y0 + th, w=THIN)
    d.line(x0 + 78, y0 + 37, x0 + tw, y0 + 37, w=THIN)
    d.line(x0 + 148, y0 + 30, x0 + 148, y0 + th, w=THIN)

    d.text(x0 + 14, y0 + 35.2, "ZL-01", size=4.2, align="center", bold=True)
    d.text(x0 + 14, y0 + 31.2, "Nr rys.", size=2.2, align="center")

    d.text(x0 + 80, y0 + 40.2, "Podziałka", size=2.2, align="left")
    d.text(x0 + 112, y0 + 40.0, "1:1", size=3.2, align="left", bold=True)
    d.text(x0 + 150, y0 + 40.2, "Format", size=2.2, align="left")
    d.text(x0 + 176, y0 + 40.0, "A3", size=3.2, align="left", bold=True)

    d.text(x0 + 80, y0 + 32.6, "Arkusz", size=2.2, align="left")
    d.text(x0 + 112, y0 + 32.4, "1/1", size=3.2, align="left", bold=True)
    d.text(x0 + 150, y0 + 32.6, "Data", size=2.2, align="left")
    d.text(x0 + 168, y0 + 32.4, "2026-11-13", size=3.0, align="left")

    d.text(x0 + 3, y0 + 24.2, "Wałek z kołem zębatym", size=4.4, align="left", bold=True)
    d.text(x0 + 3, y0 + 18.4, "Rysunek złożeniowy", size=3.0, align="left")

    d.text(x0 + 3, y0 + 9.5, "Kreślił", size=2.4, align="left")
    d.text(x0 + 22, y0 + 9.2, "Jan", size=3.4, align="left", bold=True)
    d.text(x0 + 70, y0 + 9.5, "Rzutowanie: metoda europejska (E)", size=2.6, align="left")
    # symbol metody E: trapez | dwa okręgi
    sx, sy = x0 + 168, y0 + 8.2
    d.poly([(sx, sy + 3.2), (sx, sy - 3.2), (sx + 7, sy - 1.5), (sx + 7, sy + 1.5)], w=THIN, close=True)
    d.circle(sx + 12.2, sy, 3.1, w=THIN)
    d.circle(sx + 12.2, sy, 1.5, w=THIN)

    # wykaz części — nad tabliczką, ta sama szerokość
    rows = [
        ("1", "Wałek", "—", "1", "Ø32js7"),
        ("2", "Koło zębate m = 3, z = 22", "—", "1", "otwór Ø32H8"),
        ("3", "Wpust pryzmatyczny 8x7x25", "PN-M-85005", "1", "h9"),
        ("4", "Wkręt dociskowy M8x10", "PN-EN ISO 7434", "1", "w kole"),
        ("5", "Pierścień osadczy typ A 32", "PN-M-85101", "1", "lekki"),
        ("6", "Wkręt dociskowy M8x12", "PN-EN ISO 7434", "1", "w pierścieniu"),
    ]
    rh = 8.0
    header_h = 8.0
    bh = header_h + rh * len(rows)
    by = y0 + th  # spód wykazu = wierzch tabliczki
    d.poly([(x0, by), (x0 + tw, by), (x0 + tw, by + bh), (x0, by + bh)], w=MID, close=True)
    # kolumny: Lp 12 | Nazwa 86 | Oznaczenie 52 | Szt. 12 | Uwagi 28
    cols = [0, 12, 98, 150, 164, 190]
    for c in cols[1:-1]:
        d.line(x0 + c, by, x0 + c, by + bh, w=THIN)
    # nagłówek
    d.line(x0, by + bh - header_h, x0 + tw, by + bh - header_h, w=THIN)
    headers = ["Lp.", "Nazwa części", "Oznaczenie", "Szt.", "Uwagi"]
    for i, htxt in enumerate(headers):
        cx = x0 + (cols[i] + cols[i + 1]) / 2
        d.text(cx, by + bh - header_h + 2.4, htxt, size=2.6, align="center", bold=True)
    for i, row in enumerate(rows):
        yb = by + bh - header_h - (i + 1) * rh
        d.line(x0, yb + rh, x0 + tw, yb + rh, w=THIN)
        for j, val in enumerate(row):
            cx = x0 + (cols[j] + cols[j + 1]) / 2
            # nazwa i oznaczenie dosunięte do lewej, reszta na środku
            if j in (1, 2, 4):
                d.text(x0 + cols[j] + 1.4, yb + 2.6, val, size=2.7, align="left")
            else:
                d.text(cx, yb + 2.6, val, size=2.7, align="center")

    d.text(x0 + 3, by + bh + 2.2, "Wykaz części", size=3.2, align="left", bold=True)

    # uwagi
    nx, ny = 28, 100
    d.text(nx, ny + 28, "Uwagi", size=3.6, align="left", bold=True)
    notes = [
        "1. Połączenie wpustowe zwykłe: wpust h9, rowek w wale N9,",
        "    rowek w piaście JS9. Wpust 8x7 (t1 = 4; t2 = 3,2).",
        "2. Koło dosunąć do odsadzenia Ø45. Wkręt poz. 4 dokręcić",
        "    w gniazdo stożkowe 90° wału.",
        "3. Pierścień osadczy dosunąć do czoła koła i ustalić",
        "    wkrętem poz. 6.",
        "4. Ostre krawędzie stępić.",
        "5. Wymiary wykonawcze części — według rysunków elementów.",
    ]
    for i, line in enumerate(notes):
        d.text(nx, ny + 22 - i * 4.3, line, size=2.9, align="left")


def build():
    doc = pymupdf.open()
    page = doc.new_page(width=W_MM * PT, height=H_MM * PT)
    d = Draw(page)
    draw_main(d)
    draw_section(d)
    draw_dimensions(d)
    draw_balloons(d)
    draw_frame_and_tables(d)
    doc.set_metadata(
        {
            "title": "ZL-01 Wałek z kołem zębatym — rysunek złożeniowy",
            "author": "Jan",
            "subject": "Rysunek złożeniowy wg PN",
        }
    )
    doc.save(OUT, garbage=4, deflate=True)
    doc.close()
    print(OUT)


if __name__ == "__main__":
    build()
