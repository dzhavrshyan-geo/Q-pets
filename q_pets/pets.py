# -*- coding: utf-8 -*-
"""Питомцы: внешний вид и любимые занятия каждого.

Чтобы добавить питомца, достаточно добавить сюда описание: рисует их drawing.py,
а любимые занятия (specials) — анимации из animation.py.
"""

PETS = [
    {
        "key": "bow",
        "name": "Бантик и тигрёнок",
        "fur": "#7B4024",
        "fur_light": "#A9643A",
        "skin": "#EBC3A6",
        "hand": "#8A5A43",
        "wall": "#EADCC8",
        "clothes": "suit",
        "jacket": "#26262C",
        "tie": "#141417",
        "headwear": "bow",
        "headphones": "#202024",
        "lashes": True,
        "blush": 0.35,
        "tail": True,
        "blanket": "fuzzy",
        "mug": "#FAFAF7",
        "mug_print": "monkey",
        "phone": "#1E1E22",
        "desk_extra": "folders",
        "accent": "#E0679A",
        "specials": ["tiger", "tiger_play"],
        "read_item": "paper",
        # Сосредоточенно высовывает язык, когда печатает
        "poses": {"typing": {"tongue": 1.0}},
    },
    {
        "key": "cap",
        "name": "Розовая кепка",
        "fur": "#B5602D",
        "fur_light": "#DA8B4F",
        "skin": "#F0C9AA",
        "hand": "#9B6446",
        "wall": "#EEE5D6",
        "clothes": "shirt",
        "tie": "#22305A",
        "headwear": "cap",
        "cap": "#F4A9BC",
        "headphones": "#F2A2B6",
        "lashes": True,
        "blush": 0.7,
        "tail": True,
        "blanket": "penguins",
        "mug": "#F6B5C4",
        "mug_print": "heart",
        "phone": "#F08FA9",
        "desk_extra": "penguin",
        "accent": "#E0679A",
        "specials": ["daydream", "dance"],
        "read_item": "paper",
        "poses": {},
    },
    {
        "key": "chimp",
        "name": "Шимпанзе в галстуке",
        "fur": "#2C2521",
        "fur_light": "#4A3E36",
        "skin": "#CDA98C",
        "hand": "#5C4A40",
        "wall": "#E5E2D8",
        "clothes": "shirt",
        "tie": "#24376E",
        "headwear": None,
        "headphones": None,
        "lashes": False,
        "blush": 0.0,
        "tail": False,
        "blanket": None,
        "mug": "#FAFAF7",
        "mug_print": "qgis",
        "phone": "#3A3D44",
        "desk_extra": "books",
        "accent": "#5A9E3A",
        "specials": ["ponder", "plane"],
        "read_item": "book",
        "chimp": True,
        "poses": {},
    },
]

PETS_BY_KEY = {pet["key"]: pet for pet in PETS}


def get_pet(key):
    return PETS_BY_KEY.get(key, PETS[0])
