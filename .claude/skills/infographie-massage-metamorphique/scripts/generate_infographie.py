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
COLOR_TITLE = (75, 90, 46)          # vert olive foncé (titres serif)
COLOR_TEXT = (43, 38, 32)           # texte courant, brun très foncé
COLOR_ACCROCHE_BG = (238, 224, 208)
COLOR_ACCROCHE_TEXT = (48, 38, 28)
COLOR_MEDAILLON_BG = (231, 217, 200)
COLOR_ICON_STROKE = (61, 48, 36)
COLOR_CTA_BG = (238, 227, 211)
COLOR_CTA_BORDER = (210, 190, 162)
COLOR_FOOTER_LINE = (196, 178, 152)
COLOR_HASHTAG = (110, 96, 78)

MARGIN_L = 62
CONTENT_R = 660          # bord droit de la colonne de texte
PHOTO_X0 = 700           # début de la bande photo
FEATHER_W = 170          # largeur de la zone de fondu photo -> fond
FOOTER_H = 118           # bande basse (hashtags + séparateur), pleine largeur

CTA_TEXT_X = MARGIN_L + 110
CTA_TW_MAX = CONTENT_R - 24 - CTA_TEXT_X

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
        "titre": f("Lora-Bold.ttf", 54),
        "sous_titre": f("Lora-Regular.ttf", 34),
        "accroche": f("Caveat-Variable.ttf", 46),
        "section_titre": f("InstrumentSans-Bold.ttf", 29),
        "corps": f("InstrumentSans-Regular.ttf", 27),
        "corps_gras": f("InstrumentSans-Bold.ttf", 27),
        "cta_texte": f("InstrumentSans-Regular.ttf", 26),
        "cta_valeur": f("InstrumentSans-Bold.ttf", 32),
        "cta_valeur_small": f("InstrumentSans-Bold.ttf", 24),
        "hashtag": f("InstrumentSans-Regular.ttf", 20),
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
    """Calcule les lignes de texte et de valeur (numéro/URL) de l'encart CTA,
    en choisissant automatiquement une police plus petite pour une ligne de
    valeur trop large (typiquement une URL) plutôt que de la faire déborder
    du cadre. Retourne (lignes_texte, [(ligne_valeur, police), ...], hauteur)."""
    texte_lines = wrap_plain(draw, cta.get("texte", ""), fonts["cta_texte"], CTA_TW_MAX)
    valeur_lines = []
    for raw_line in cta.get("valeur", "").split("\n"):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        font = fonts["cta_valeur"]
        if draw.textlength(raw_line, font=font) > CTA_TW_MAX:
            font = fonts["cta_valeur_small"]
            if draw.textlength(raw_line, font=font) > CTA_TW_MAX:
                warn(warnings, f"la valeur du CTA '{raw_line}' est trop longue pour l'encart "
                     "même en petite police : elle risque de déborder. Raccourcis-la.")
        valeur_lines.append((raw_line, font))
    h = 34 + 32 * len(texte_lines)
    if valeur_lines:
        h += 10 + 34 * len(valeur_lines)
    h += 26
    return texte_lines, valeur_lines, max(h, 100)


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

    y = 58

    # --- Branche décorative + icône d'en-tête -----------------------------
    if data.get("branche_decorative", True):
        icon_feuille(draw, MARGIN_L + 30, y + 24, 34)

    icone_entete = data.get("icone_entete")
    title_x = MARGIN_L
    if icone_entete:
        draw_medaillon(draw, MARGIN_L + 90 + 34, y + 90, 34, icone_entete, fonts, warnings)
        title_x = MARGIN_L + 90 + 34 + 34 + 24

    # --- Titre + sous-titre -------------------------------------------------
    titre = data["titre"]
    sous_titre = data.get("sous_titre")
    ty = y + 60
    draw.text((title_x, ty), titre, font=fonts["titre"], fill=COLOR_TITLE)
    if sous_titre:
        tw = draw.textlength(titre + " ", font=fonts["titre"])
        draw.text((title_x + tw, ty + 14), f"({sous_titre})", font=fonts["sous_titre"], fill=COLOR_TITLE)
    y = ty + 90

    # --- Bandeau accroche ----------------------------------------------------
    accroche = data.get("accroche")
    if accroche:
        lines = accroche.split("\n") if "\n" in accroche else wrap_plain(
            draw, accroche, fonts["accroche"], CONTENT_R - MARGIN_L - 60)
        line_h = 54
        box_h = 40 + line_h * len(lines)
        box = [MARGIN_L, y, CONTENT_R, y + box_h]
        draw.rounded_rectangle(box, radius=28, fill=COLOR_ACCROCHE_BG)
        ly = y + (box_h - line_h * len(lines)) / 2 + 4
        for line in lines:
            lw = draw.textlength(line, font=fonts["accroche"])
            draw.text((MARGIN_L + (box[2] - box[0] - lw) / 2, ly), line,
                      font=fonts["accroche"], fill=COLOR_ACCROCHE_TEXT)
            ly += line_h
        y = box[3] + 44
    else:
        y += 10

    # --- Sections --------------------------------------------------------
    sections = data.get("sections", [])
    if len(sections) > 3:
        warn(warnings, f"{len(sections)} sections fournies : au-delà de 3, le texte "
             "risque de déborder sur le pied de page. Vérifie le rendu final.")

    text_x = MARGIN_L + 100
    text_w = CONTENT_R - text_x
    section_gap = 40
    cta = data.get("cta")
    cta_texte_lines, cta_valeur_lines, cta_h = layout_cta(draw, cta, fonts, warnings) \
        if cta else ([], [], 0)

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
        measured_h += cta_h
    footer_limit = CANVAS_H - FOOTER_H - 30
    available = footer_limit - y
    y += max(0, min(160, (available - measured_h) / 2))

    for section in sections:
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

    if y > footer_limit:
        warn(warnings, "débordement : le texte des sections descend jusque dans le pied de "
             "page. Raccourcis un des textes et relance le script.")

    # --- Encart CTA --------------------------------------------------------
    if cta:
        cta_y0 = y
        box = [MARGIN_L, cta_y0, CONTENT_R, cta_y0 + cta_h]
        draw.rounded_rectangle(box, radius=24, fill=COLOR_CTA_BG, outline=COLOR_CTA_BORDER, width=2)
        draw_medaillon(draw, MARGIN_L + 55, cta_y0 + cta_h / 2, 34,
                       cta.get("icone", "telephone"), fonts, warnings)
        cy_line = cta_y0 + 34
        for line in cta_texte_lines:
            draw.text((CTA_TEXT_X, cy_line), line, font=fonts["cta_texte"], fill=COLOR_TEXT)
            cy_line += 32
        if cta_valeur_lines:
            cy_line += 10
            for vline, vfont in cta_valeur_lines:
                draw.text((CTA_TEXT_X, cy_line), vline, font=vfont, fill=COLOR_TITLE)
                cy_line += 34
        if cta_y0 + cta_h > footer_limit:
            warn(warnings, "débordement : l'encart CTA empiète sur le pied de page. "
                 "Raccourcis le texte des sections ou du CTA et relance le script.")

    # --- Pied de page : séparateur + hashtags + cœur ------------------------
    sep_y = CANVAS_H - FOOTER_H + 18
    draw.line([MARGIN_L, sep_y, CANVAS_W - MARGIN_L, sep_y], fill=COLOR_FOOTER_LINE, width=1)
    icon_lotus(draw, CANVAS_W / 2, sep_y, 16)

    hashtags = data.get("hashtags")
    if hashtags:
        lines = wrap_plain(draw, hashtags, fonts["hashtag"], CANVAS_W - 2 * MARGIN_L)
        if len(lines) > 2:
            warn(warnings, "les hashtags dépassent 2 lignes : les derniers ont été coupés. "
                 "Raccourcis la liste et relance le script.")
        hy = sep_y + 26
        for line in lines[:2]:
            lw = draw.textlength(line, font=fonts["hashtag"])
            draw.text(((CANVAS_W - lw) / 2, hy), line, font=fonts["hashtag"], fill=COLOR_HASHTAG)
            hy += 26

    icon_coeur_petit(draw, CANVAS_W / 2, CANVAS_H - 20, 10)

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
