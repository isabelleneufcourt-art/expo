#!/usr/bin/env python3
"""Assemble un JSON structuré + une photo en une infographie JPEG 1080x1350
pour la page Instagram/Facebook de massage métamorphique.

Tout le placement (texte, retour à la ligne, icônes, photo) est déterministe.
Voir SKILL.md pour le format d'entrée attendu.
"""

import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# Constantes de mise en page (gabarit fixe)
# ---------------------------------------------------------------------------

CANVAS_W, CANVAS_H = 1080, 1350

BG_TOP = (251, 248, 244)
BG_BOTTOM = (240, 232, 219)
COLOR_TITLE = (40, 34, 27)           # brun très foncé, quasi noir (titres serif)
COLOR_TEXT = (43, 38, 32)            # texte courant, brun très foncé
COLOR_ACCROCHE_TEXT = (156, 80, 45)  # terracotta (accroche manuscrite)
COLOR_SWASH = (40, 34, 27)           # soulignements à main levée sous titre/accroche
COLOR_MEDAILLON_BG = (231, 217, 200)
COLOR_ICON_STROKE = (61, 48, 36)
COLOR_CTA_BG = (238, 227, 211)
COLOR_CTA_BORDER = (210, 190, 162)
COLOR_BADGE_BG = (54, 63, 38)        # badge lien : vert olive foncé
COLOR_BADGE_TEXT = (250, 248, 244)
COLOR_SEPARATOR = (214, 202, 184)    # ligne fine entre sections
COLOR_HASHTAG = (110, 96, 78)

MARGIN_L = 62
CONTENT_R = 660          # bord droit de la colonne de texte
PHOTO_X0 = 700           # début de la bande photo
FEATHER_W = 170          # largeur de la zone de fondu photo -> fond
FOOTER_H = 90            # bande basse (hashtags), pleine largeur

CTA_TEXT_X = MARGIN_L + 90
CTA_TW_MAX = CONTENT_R - 24 - CTA_TEXT_X
CTA_PAD_TOP = 32
CTA_LINE_H = 32
CTA_PAD_BOTTOM = 32
BADGE_H = 50
BADGE_PAD_X = 24
BADGE_GAP_BELOW = 16

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "assets", "fonts")


def warn(warnings, message):
    warnings.append(message)


def fail(field, message):
    print(json.dumps({"erreur": field, "message": message}, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Polices
# ---------------------------------------------------------------------------

def load_fonts():
    def f(name, size):
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

    fonts = {
        "surtitre": f("InstrumentSans-Bold.ttf", 24),
        "accroche": f("Caveat-Variable.ttf", 46),
        "section_titre": f("InstrumentSans-Bold.ttf", 29),
        "corps": f("InstrumentSans-Regular.ttf", 27),
        "corps_gras": f("InstrumentSans-Bold.ttf", 27),
        "cta_texte": f("InstrumentSans-Regular.ttf", 26),
        "cta_texte_gras": f("InstrumentSans-Bold.ttf", 26),
        "lien_badge": f("InstrumentSans-Bold.ttf", 22),
        "lien_badge_small": f("InstrumentSans-Bold.ttf", 17),
        "hashtag": f("InstrumentSans-Regular.ttf", 21),
    }
    # Police manuscrite variable : on force un poids plus soutenu (~650)
    # pour rester lisible en petit corps sur fond clair.
    try:
        fonts["accroche"].set_variation_by_axes([650])
    except Exception:
        pass
    return fonts


# ---------------------------------------------------------------------------
# Icônes ligne-art (dessinées, pas d'emoji : rendu garanti identique partout)
# ---------------------------------------------------------------------------

def _stroke(draw):
    return dict(fill=None, outline=COLOR_ICON_STROKE, width=3)


def icon_cerveau(draw, cx, cy, r):
    draw.ellipse([cx - r * 0.75, cy - r * 0.55, cx + r * 0.75, cy + r * 0.55],
                 outline=COLOR_ICON_STROKE, width=3)
    # sillon central en zigzag doux (hémisphères)
    draw.line([cx, cy - r * 0.5, cx, cy + r * 0.5], fill=COLOR_ICON_STROKE, width=2)
    for side in (-1, 1):
        for dy in (-0.28, 0.05, 0.35):
            x0, x1 = sorted([cx + side * r * 0.05, cx + side * r * 0.55])
            draw.arc([x0, cy + dy * r - r * 0.16, x1, cy + dy * r + r * 0.16],
                     150 if side < 0 else -30, 330 if side < 0 else 150,
                     fill=COLOR_ICON_STROKE, width=2)


def icon_papillon(draw, cx, cy, r):
    draw.line([cx, cy - r * 0.5, cx, cy + r * 0.55], fill=COLOR_ICON_STROKE, width=3)
    draw.ellipse([cx - r * 0.07, cy - r * 0.62, cx + r * 0.07, cy - r * 0.48],
                 fill=COLOR_ICON_STROKE)
    for side in (-1, 1):
        upper = [(cx, cy - r * 0.45), (cx + side * r * 0.35, cy - r * 0.62),
                 (cx + side * r * 0.78, cy - r * 0.28), (cx + side * r * 0.5, cy - r * 0.02),
                 (cx, cy - r * 0.08)]
        lower = [(cx, cy - r * 0.02), (cx + side * r * 0.5, cy + r * 0.05),
                 (cx + side * r * 0.5, cy + r * 0.38), (cx + side * r * 0.15, cy + r * 0.52),
                 (cx, cy + r * 0.28)]
        for wing in (upper, lower):
            draw.line(wing + [wing[0]], fill=COLOR_ICON_STROKE, width=2, joint="curve")


def icon_feuille(draw, cx, cy, r):
    draw.line([cx - r * 0.6, cy + r * 0.5, cx + r * 0.55, cy - r * 0.5],
              fill=COLOR_ICON_STROKE, width=2)
    for t in (0.15, 0.45, 0.75):
        lx = cx - r * 0.6 + t * (r * 1.15)
        ly = cy + r * 0.5 - t * (r * 1.0)
        draw.ellipse([lx - r * 0.22, ly - r * 0.12, lx + r * 0.22, ly + r * 0.12],
                     outline=COLOR_ICON_STROKE, width=2)


def icon_arbre(draw, cx, cy, r):
    draw.ellipse([cx - r * 0.55, cy - r * 0.7, cx + r * 0.55, cy + r * 0.2],
                 outline=COLOR_ICON_STROKE, width=3)
    draw.line([cx, cy + r * 0.1, cx, cy + r * 0.65], fill=COLOR_ICON_STROKE, width=4)


def icon_noeud(draw, cx, cy, r):
    draw.arc([cx - r * 0.6, cy - r * 0.45, cx + r * 0.1, cy + r * 0.45], 20, 340,
              fill=COLOR_ICON_STROKE, width=3)
    draw.arc([cx - r * 0.1, cy - r * 0.45, cx + r * 0.6, cy + r * 0.45], 200, 160,
              fill=COLOR_ICON_STROKE, width=3)


def icon_croix(draw, cx, cy, r):
    d = r * 0.5
    draw.line([cx - d, cy - d, cx + d, cy + d], fill=COLOR_ICON_STROKE, width=4)
    draw.line([cx - d, cy + d, cx + d, cy - d], fill=COLOR_ICON_STROKE, width=4)


def icon_colonne(draw, cx, cy, r):
    draw.line([cx, cy - r * 0.65, cx, cy + r * 0.65], fill=COLOR_ICON_STROKE, width=2)
    for i in range(-2, 3):
        y = cy + i * r * 0.28
        draw.ellipse([cx - r * 0.3, y - r * 0.12, cx + r * 0.3, y + r * 0.12],
                     outline=COLOR_ICON_STROKE, width=2)


def icon_silhouette(draw, cx, cy, r):
    draw.ellipse([cx - r * 0.28, cy - r * 0.65, cx + r * 0.28, cy - r * 0.15],
                 outline=COLOR_ICON_STROKE, width=3)
    draw.arc([cx - r * 0.55, cy - r * 0.3, cx + r * 0.55, cy + r * 0.75], 180, 360,
              fill=COLOR_ICON_STROKE, width=3)
    _heart(draw, cx, cy + r * 0.15, r * 0.22, COLOR_ICON_STROKE, outline_only=True)


def icon_lotus(draw, cx, cy, r):
    base_y = cy + r * 0.35
    for angle in (-60, -30, 0, 30, 60):
        rad = math.radians(angle)
        tip_x = cx + math.sin(rad) * r * 0.6
        tip_y = base_y - math.cos(rad) * r * 0.75
        draw.line([cx, base_y, tip_x, tip_y], fill=COLOR_ICON_STROKE, width=2)
        draw.ellipse([tip_x - r * 0.12, tip_y - r * 0.12, tip_x + r * 0.12, tip_y + r * 0.12],
                     outline=COLOR_ICON_STROKE, width=2)
    draw.line([cx - r * 0.55, base_y, cx + r * 0.55, base_y], fill=COLOR_ICON_STROKE, width=2)


def icon_telephone(draw, cx, cy, r):
    # combiné stylisé : deux courbes en S + embouts (oreille / micro)
    draw.arc([cx - r * 0.5, cy - r * 0.5, cx + r * 0.2, cy + r * 0.2], 30, 200,
              fill=COLOR_ICON_STROKE, width=5)
    draw.arc([cx - r * 0.2, cy - r * 0.2, cx + r * 0.5, cy + r * 0.5], 210, 20,
              fill=COLOR_ICON_STROKE, width=5)
    ear = (cx - r * 0.5 + r * 0.35, cy - r * 0.5 + r * 0.02)
    mouth = (cx + r * 0.5 - r * 0.35, cy + r * 0.5 - r * 0.02)
    for pt in (ear, mouth):
        draw.ellipse([pt[0] - r * 0.1, pt[1] - r * 0.1, pt[0] + r * 0.1, pt[1] + r * 0.1],
                     fill=COLOR_ICON_STROKE)


def icon_enveloppe(draw, cx, cy, r):
    box = [cx - r * 0.6, cy - r * 0.4, cx + r * 0.6, cy + r * 0.4]
    draw.rectangle(box, outline=COLOR_ICON_STROKE, width=3)
    draw.line([box[0], box[1], cx, cy + r * 0.12], fill=COLOR_ICON_STROKE, width=2)
    draw.line([box[2], box[1], cx, cy + r * 0.12], fill=COLOR_ICON_STROKE, width=2)


def icon_question(draw, cx, cy, r, fonts):
    text = "?"
    bbox = draw.textbbox((0, 0), text, font=fonts["section_titre"])
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]), text,
               font=fonts["section_titre"], fill=COLOR_ICON_STROKE)


def icon_horloge_noeud(draw, cx, cy, r):
    # horloge à gauche (agenda chargé) + gribouillis noué à droite (sollicitations)
    hx, hy, hr = cx - r * 0.35, cy, r * 0.42
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], outline=COLOR_ICON_STROKE, width=3)
    draw.line([hx, hy, hx, hy - hr * 0.7], fill=COLOR_ICON_STROKE, width=2)
    draw.line([hx, hy, hx + hr * 0.5, hy], fill=COLOR_ICON_STROKE, width=2)
    sx = cx + r * 0.32
    pts = [(sx - r * 0.28, cy - r * 0.35), (sx + r * 0.25, cy - r * 0.2),
           (sx - r * 0.22, cy), (sx + r * 0.28, cy + r * 0.18),
           (sx - r * 0.15, cy + r * 0.38)]
    draw.line(pts, fill=COLOR_ICON_STROKE, width=2, joint="curve")


def icon_colonne_ondes(draw, cx, cy, r):
    draw.line([cx, cy - r * 0.6, cx, cy + r * 0.6], fill=COLOR_ICON_STROKE, width=2)
    for i in range(-2, 3):
        yy = cy + i * r * 0.26
        draw.ellipse([cx - r * 0.26, yy - r * 0.1, cx + r * 0.26, yy + r * 0.1],
                     outline=COLOR_ICON_STROKE, width=2)
    for side in (-1, 1):
        for dy in (-0.3, 0, 0.3):
            x0 = cx + side * r * 0.42
            x1 = cx + side * r * 0.68
            draw.line([x0, cy + dy * r, x1, cy + dy * r], fill=COLOR_ICON_STROKE, width=2)


def icon_lien(draw, cx, cy, r):
    draw.arc([cx - r * 0.55, cy - r * 0.3, cx + r * 0.15, cy + r * 0.3], 40, 320,
              fill=COLOR_ICON_STROKE, width=3)
    draw.arc([cx - r * 0.15, cy - r * 0.3, cx + r * 0.55, cy + r * 0.3], 220, 140,
              fill=COLOR_ICON_STROKE, width=3)


def icon_coeur_petit(draw, cx, cy, r):
    _heart(draw, cx, cy, r, COLOR_ICON_STROKE, outline_only=False)


def _heart(draw, cx, cy, r, color, outline_only):
    p1 = (cx - r, cy - r * 0.3)
    p2 = (cx, cy + r * 0.9)
    p3 = (cx + r, cy - r * 0.3)
    kw = dict(outline=color, width=2) if outline_only else dict(fill=color)
    draw.pieslice([cx - r * 1.4, cy - r * 1.1, cx, cy + r * 0.3], 180, 360, **kw)
    draw.pieslice([cx, cy - r * 1.1, cx + r * 1.4, cy + r * 0.3], 180, 360, **kw)
    draw.polygon([p1, p2, p3], **kw)


ICONS = {
    "cerveau": icon_cerveau,
    "papillon": icon_papillon,
    "feuille": icon_feuille,
    "arbre": icon_arbre,
    "noeud": icon_noeud,
    "croix": icon_croix,
    "colonne": icon_colonne,
    "silhouette": icon_silhouette,
    "lotus": icon_lotus,
    "telephone": icon_telephone,
    "enveloppe": icon_enveloppe,
    "lien": icon_lien,
    "coeur": icon_coeur_petit,
    "horloge_noeud": icon_horloge_noeud,
    "colonne_ondes": icon_colonne_ondes,
}


def draw_icon(draw, name, cx, cy, r, fonts, warnings):
    if name == "question":
        icon_question(draw, cx, cy, r, fonts)
        return
    fn = ICONS.get(name)
    if fn is None:
        warn(warnings, f"icône inconnue '{name}' : un cercle simple a été dessiné à la place.")
        draw.ellipse([cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5],
                     outline=COLOR_ICON_STROKE, width=3)
        return
    fn(draw, cx, cy, r)


def draw_medaillon(draw, cx, cy, radius, icon_name, fonts, warnings):
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=COLOR_MEDAILLON_BG)
    draw_icon(draw, icon_name, cx, cy, radius, fonts, warnings)


# ---------------------------------------------------------------------------
# Texte : parsing **gras** + retour à la ligne déterministe
# ---------------------------------------------------------------------------

def parse_bold_runs(text):
    """'a **b** c' -> [('a ', False), ('b', True), (' c', False)]"""
    runs = []
    bold = False
    for i, chunk in enumerate(text.split("**")):
        if chunk:
            runs.append((chunk, bold))
        bold = not bold
    return runs


def tokenize_words(text):
    """'la **tête**. Cette' -> [[('la', False)], [('tête', True), ('.', False)],
    [('Cette', False)]] : un mot est une liste de fragments (texte, gras) qui
    se touchent SANS espace (la frontière **...** ne crée jamais d'espace
    fantôme), les mots eux-mêmes étant séparés par les espaces du texte source."""
    words, current = [], []
    for chunk, bold in parse_bold_runs(text):
        parts = chunk.split(" ")
        for i, part in enumerate(parts):
            if i > 0:
                if current:
                    words.append(current)
                current = []
            if part:
                current.append((part, bold))
    if current:
        words.append(current)
    return words


def word_width(draw, word, font_regular, font_bold):
    return sum(draw.textlength(part, font=(font_bold if bold else font_regular))
               for part, bold in word)


def wrap_runs(draw, text, font_regular, font_bold, max_width):
    """Découpe le texte (avec **gras**) en lignes de mots, chaque mot gardant
    son détail gras, sans jamais dépasser max_width."""
    words = tokenize_words(text)
    space_w = draw.textlength(" ", font=font_regular)
    lines, current, current_w = [], [], 0
    for word in words:
        w = word_width(draw, word, font_regular, font_bold)
        added_w = w if not current else w + space_w
        if current and current_w + added_w > max_width:
            lines.append(current)
            current, current_w = [word], w
        else:
            current.append(word)
            current_w += added_w
    if current:
        lines.append(current)
    return lines


def draw_wrapped(draw, xy, text, font_regular, font_bold, max_width, fill, line_height):
    x0, y = xy
    lines = wrap_runs(draw, text, font_regular, font_bold, max_width)
    space_w = draw.textlength(" ", font=font_regular)
    for line in lines:
        x = x0
        for word in line:
            for part, bold in word:
                f = font_bold if bold else font_regular
                draw.text((x, y), part, font=f, fill=fill)
                x += draw.textlength(part, font=f)
            x += space_w
        y += line_height
    return y  # y final (bas du bloc)


def layout_cta(draw, cta, fonts, warnings):
    """Calcule la hauteur de l'encart CTA (texte, éventuellement gras via
    **...**) et, si un lien est fourni, la police/largeur du badge qui vient
    chevaucher le bas du cadre — en choisissant automatiquement une police
    plus petite si l'URL est trop longue plutôt que de la faire déborder.
    Retourne (cta_h, badge_font_ou_None, badge_w, hauteur_totale_du_bloc)."""
    n_lines = len(wrap_runs(draw, cta.get("texte", ""), fonts["cta_texte"],
                            fonts["cta_texte_gras"], CTA_TW_MAX))
    cta_h = CTA_PAD_TOP + CTA_LINE_H * max(n_lines, 1) + CTA_PAD_BOTTOM

    badge_font, badge_w = None, 0
    lien = cta.get("lien")
    if lien:
        max_badge_w = CONTENT_R - MARGIN_L
        badge_font = fonts["lien_badge"]
        tw = draw.textlength(lien, font=badge_font)
        if tw + 2 * BADGE_PAD_X > max_badge_w:
            badge_font = fonts["lien_badge_small"]
            tw = draw.textlength(lien, font=badge_font)
            if tw + 2 * BADGE_PAD_X > max_badge_w:
                warn(warnings, f"le lien du CTA '{lien}' est trop long pour l'encart même en "
                     "petite police : il risque de déborder. Raccourcis-le.")
        badge_w = min(max_badge_w, tw + 2 * BADGE_PAD_X)

    total_h = cta_h + (BADGE_H / 2 + BADGE_GAP_BELOW if lien else 0)
    return cta_h, badge_font, badge_w, total_h


def draw_tracked(draw, xy, text, font, fill, tracking):
    """Dessine du texte avec un espacement supplémentaire entre lettres
    (used pour le petit intitulé en capitales au-dessus du titre)."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return x


def draw_swash(draw, x0, y, width, color, thickness=3):
    """Trait de soulignement 'à main levée' : une légère courbe suivie d'un
    petit relevé de stylo en fin de trait."""
    n = 20
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append((x0 + t * width, y + math.sin(t * math.pi) * 4))
    draw.line(pts, fill=color, width=thickness, joint="curve")
    ex, ey = pts[-1]
    draw.line([ex, ey, ex + 12, ey - 9], fill=color, width=thickness)


def layout_titre(draw, titre, warnings):
    """Choisit la plus grande taille de Lora-Bold (entre 44 et 84px) qui fait
    tenir le titre (converti en capitales) sur une ligne dans la colonne de
    texte ; au-delà, il est réparti sur plusieurs lignes plutôt que de
    déborder sur la bande photo."""
    path = os.path.join(FONT_DIR, "Lora-Bold.ttf")
    max_w = CONTENT_R - MARGIN_L
    text = titre.upper()
    size = 84
    font = ImageFont.truetype(path, size)
    while size > 44 and draw.textlength(text, font=font) > max_w:
        size -= 4
        font = ImageFont.truetype(path, size)
    lines = [text]
    if draw.textlength(text, font=font) > max_w:
        lines = wrap_plain(draw, text, font, max_w)
        if len(lines) > 2:
            warn(warnings, "le titre est long et tient sur plus de 2 lignes : vérifie qu'il ne "
                 "déborde pas sur la photo. Raccourcis-le si besoin.")
    return font, lines


def draw_justified_tags(draw, tags, y, font, fill, x0, x1, min_gap=14):
    """Répartit les hashtags sur toute la largeur (comme dans le gabarit de
    référence) si ça tient sur une ligne avec un espacement raisonnable ;
    sinon renvoie False pour laisser l'appelant retomber sur un rendu
    centré/multi-lignes classique."""
    widths = [draw.textlength(t, font=font) for t in tags]
    total_w = sum(widths)
    n = len(tags)
    if n == 0:
        return True
    if n == 1:
        draw.text(((x0 + x1) / 2 - widths[0] / 2, y), tags[0], font=font, fill=fill)
        return True
    gap = (x1 - x0 - total_w) / (n - 1)
    if gap < min_gap:
        return False
    x = x0
    for tag, w in zip(tags, widths):
        draw.text((x, y), tag, font=font, fill=fill)
        x += w + gap
    return True


def wrap_plain(draw, text, font, max_width):
    words = text.split(" ")
    lines, current = [], []
    for word in words:
        trial = " ".join(current + [word])
        if current and draw.textlength(trial, font=font) > max_width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


# ---------------------------------------------------------------------------
# Rendu
# ---------------------------------------------------------------------------

def make_background():
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_TOP)
    px = img.load()
    for y in range(CANVAS_H):
        t = y / (CANVAS_H - 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        for x in range(CANVAS_W):
            px[x, y] = (r, g, b)
    return img


def paste_photo_band(canvas, photo_path, warnings):
    band_w = CANVAS_W - PHOTO_X0
    band_h = CANVAS_H - FOOTER_H
    try:
        photo = Image.open(photo_path).convert("RGB")
    except Exception as e:
        fail("image", f"Impossible d'ouvrir l'image '{photo_path}' : {e}")

    scale = max(band_w / photo.width, band_h / photo.height)
    new_size = (max(1, round(photo.width * scale)), max(1, round(photo.height * scale)))
    photo = photo.resize(new_size, Image.LANCZOS)
    left = (photo.width - band_w) // 2
    top = (photo.height - band_h) // 2
    photo = photo.crop((left, top, left + band_w, top + band_h))

    # Masque : 0 -> fond visible, 255 -> photo pleine, fondu sur FEATHER_W px.
    mask = Image.new("L", (band_w, band_h), 255)
    mpx = mask.load()
    for x in range(min(FEATHER_W, band_w)):
        alpha = int(255 * (x / FEATHER_W))
        for y in range(band_h):
            mpx[x, y] = alpha
    canvas.paste(photo, (PHOTO_X0, 0), mask)


def render(data, image_path, output_path):
    warnings = []
    fonts = load_fonts()
    canvas = make_background()
    draw = ImageDraw.Draw(canvas)

    paste_photo_band(canvas, image_path, warnings)

    y = 56

    # --- Titre : kicker (surtitre) + gros mot-titre + soulignement --------
    surtitre = data.get("surtitre")
    if surtitre:
        draw_tracked(draw, (MARGIN_L, y), surtitre.upper(), fonts["surtitre"], COLOR_TITLE,
                     tracking=4)
        y += 38

    titre_font, titre_lines = layout_titre(draw, data["titre"], warnings)
    line_h = titre_font.size * 1.05
    for line in titre_lines:
        draw.text((MARGIN_L, y), line, font=titre_font, fill=COLOR_TITLE)
        y += line_h
    last_line = titre_lines[-1]
    last_w = draw.textlength(last_line, font=titre_font)
    last_bbox = draw.textbbox((MARGIN_L, y - line_h), last_line, font=titre_font)
    draw_swash(draw, MARGIN_L, last_bbox[3] + 8, min(last_w, 260), COLOR_SWASH)
    y += 26

    # --- Accroche (manuscrite, sans encadré, alignée à gauche) ------------
    accroche = data.get("accroche")
    if accroche:
        max_w = CONTENT_R - MARGIN_L
        lines = accroche.split("\n") if "\n" in accroche else wrap_plain(
            draw, accroche, fonts["accroche"], max_w)
        line_h = 52
        last_w = 0
        for line in lines:
            draw.text((MARGIN_L, y), line, font=fonts["accroche"], fill=COLOR_ACCROCHE_TEXT)
            last_w = draw.textlength(line, font=fonts["accroche"])
            y += line_h
        last_bbox = draw.textbbox((MARGIN_L, y - line_h), lines[-1], font=fonts["accroche"])
        draw_swash(draw, MARGIN_L, last_bbox[3] + 6, min(last_w, 220), COLOR_ACCROCHE_TEXT)
        y += 30
    else:
        y += 14

    # --- Sections (séparées par un filet fin) -----------------------------
    sections = data.get("sections", [])
    if len(sections) > 3:
        warn(warnings, f"{len(sections)} sections fournies : au-delà de 3, le texte "
             "risque de déborder sur le pied de page. Vérifie le rendu final.")

    text_x = MARGIN_L + 100
    text_w = CONTENT_R - text_x
    section_gap = 40
    cta = data.get("cta")
    cta_h, badge_font, badge_w, cta_total_h = layout_cta(draw, cta, fonts, warnings) \
        if cta else (0, None, 0, 0)

    # Pré-mesure (sans rien dessiner) pour centrer verticalement le bloc
    # sections+CTA dans l'espace restant, plutôt que de le coller en haut et
    # laisser tout le vide s'accumuler juste avant le pied de page.
    measured_h = 0
    for section in sections:
        h = 40 if section.get("titre_section") else 0
        h += 36 * len(wrap_runs(draw, section.get("texte", ""), fonts["corps"],
                                fonts["corps_gras"], text_w))
        measured_h += max(h, 70) + section_gap
    if cta:
        measured_h += cta_total_h
    footer_limit = CANVAS_H - FOOTER_H - 30
    available = footer_limit - y
    y += max(0, min(160, (available - measured_h) / 2))

    for idx, section in enumerate(sections):
        icone = section.get("icone", "")
        titre_section = section.get("titre_section", "")
        texte = section.get("texte", "")

        block_top = y
        by = y
        if titre_section:
            draw.text((text_x, by), titre_section, font=fonts["section_titre"], fill=COLOR_TEXT)
            by += 40
        by = draw_wrapped(draw, (text_x, by), texte, fonts["corps"], fonts["corps_gras"],
                          text_w, COLOR_TEXT, line_height=36)

        block_h = by - block_top
        medaillon_cy = block_top + max(block_h, 70) / 2
        draw_medaillon(draw, MARGIN_L + 44, medaillon_cy, 44, icone, fonts, warnings)

        y = by + section_gap
        if idx < len(sections) - 1:
            sep_y = y - section_gap / 2
            draw.line([text_x, sep_y, CONTENT_R, sep_y], fill=COLOR_SEPARATOR, width=1)

    if y > footer_limit:
        warn(warnings, "débordement : le texte des sections descend jusque dans le pied de "
             "page. Raccourcis un des textes et relance le script.")

    # --- Encart CTA (icône + phrase, badge lien à cheval sur le bas) ------
    if cta:
        cta_y0 = y
        box = [MARGIN_L, cta_y0, CONTENT_R, cta_y0 + cta_h]
        draw.rounded_rectangle(box, radius=24, fill=COLOR_CTA_BG, outline=COLOR_CTA_BORDER, width=2)
        draw_icon(draw, cta.get("icone", "telephone"), MARGIN_L + 44, cta_y0 + cta_h / 2, 26,
                  fonts, warnings)
        draw_wrapped(draw, (CTA_TEXT_X, cta_y0 + CTA_PAD_TOP), cta.get("texte", ""),
                    fonts["cta_texte"], fonts["cta_texte_gras"], CTA_TW_MAX, COLOR_TEXT,
                    CTA_LINE_H)
        lien = cta.get("lien")
        if lien and badge_font:
            badge_y0 = cta_y0 + cta_h - BADGE_H / 2
            draw.rounded_rectangle([MARGIN_L, badge_y0, MARGIN_L + badge_w, badge_y0 + BADGE_H],
                                   radius=BADGE_H / 2, fill=COLOR_BADGE_BG)
            bbox = draw.textbbox((0, 0), lien, font=badge_font)
            th = bbox[3] - bbox[1]
            draw.text((MARGIN_L + BADGE_PAD_X, badge_y0 + (BADGE_H - th) / 2 - bbox[1]),
                      lien, font=badge_font, fill=COLOR_BADGE_TEXT)
        if cta_y0 + cta_total_h > footer_limit:
            warn(warnings, "débordement : l'encart CTA (avec son badge lien) empiète sur le "
                 "pied de page. Raccourcis le texte et relance le script.")

    # --- Pied de page : hashtags répartis sur la largeur ------------------
    hashtags = data.get("hashtags")
    if hashtags:
        tags = hashtags.split()
        hy = CANVAS_H - FOOTER_H + 34
        x0, x1 = MARGIN_L, CANVAS_W - MARGIN_L
        if not draw_justified_tags(draw, tags, hy, fonts["hashtag"], COLOR_HASHTAG, x0, x1):
            lines = wrap_plain(draw, hashtags, fonts["hashtag"], x1 - x0)
            if len(lines) > 2:
                warn(warnings, "les hashtags dépassent 2 lignes : les derniers ont été "
                     "coupés. Raccourcis la liste et relance le script.")
            for line in lines[:2]:
                lw = draw.textlength(line, font=fonts["hashtag"])
                draw.text(((CANVAS_W - lw) / 2, hy), line, font=fonts["hashtag"],
                          fill=COLOR_HASHTAG)
                hy += 26

    canvas.convert("RGB").save(output_path, "JPEG", quality=92)
    return warnings, len(sections)


# ---------------------------------------------------------------------------
# CLI + validation d'entrée
# ---------------------------------------------------------------------------

def validate(data):
    if "titre" not in data or not data["titre"]:
        fail("titre", "Champ 'titre' manquant ou vide.")
    if "cta" in data and data["cta"]:
        if not data["cta"].get("texte"):
            fail("cta.texte", "Le champ 'cta.texte' est obligatoire dès que 'cta' est fourni.")
    for i, section in enumerate(data.get("sections", [])):
        if not section.get("texte"):
            fail(f"sections[{i}].texte", "Chaque section doit avoir un champ 'texte'.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="chemin du JSON structuré")
    parser.add_argument("--image", required=True, help="chemin de la photo (JPEG/PNG)")
    parser.add_argument("--output", required=True, help="chemin du JPEG de sortie")
    args = parser.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as e:
        fail("input", f"JSON illisible : {e}")

    validate(data)

    if not os.path.isfile(args.image):
        fail("image", f"Fichier introuvable : {args.image}")

    warnings, nb_sections = render(data, args.image, args.output)

    print(json.dumps({
        "fichier_genere": args.output,
        "dimensions": [CANVAS_W, CANVAS_H],
        "nb_sections": nb_sections,
        "avertissements": warnings,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
