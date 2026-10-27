# -*- coding: utf-8 -*-
"""Поведение питомца (без Qt): что он делает в зависимости от действий пользователя.

Порядок важности:
1. реакция (помахать после щелчка, «сохранено» на Ctrl+S, «ой» на Ctrl+Z, проснуться,
   испугаться начальника) и уход из кабинета — доигрываются до конца;
2. в кабинете начальник — питомец слушает его или изо всех сил печатает;
3. только что нажимали клавиши или мышь — печатает, водит мышкой или крутит колёсико;
4. QGIS занят дольше BUSY_DELAY — ждёт вместе с QGIS;
5. простой меньше idle_timeout — работает без нажатий (читает экран, пишет заметки…);
6. дольше — занимается своими делами (иногда выходит из кабинета на 15–60 с),
   а после nap_after — дремлет.
"""

import random

from .animation import ACTIVITIES, AWAY, FOCUS, IDLE_COMMON, REACTIONS, Animator
from .visitors import Boss, Fox

WORK_HOLD = 1.2   # сек.: столько ещё печатает/водит мышкой после последнего нажатия
BUSY_DELAY = 0.7  # сек.: короткая перерисовка карты не отвлекает питомца
COMBOS = {"save": "saved", "undo": "oops"}
AWAY_TIME = (15.0, 60.0)  # сек.: сколько питомца нет в кабинете (вместе с уходом и возвращением)
LEAVE_WEIGHT = 0.5        # выходит из кабинета реже, чем занимается другими делами
# Застать за этим — значит застать бездельничающим
SLACKING = set(IDLE_COMMON) | {"nap", "wake", "nod_off", "tiger", "tiger_play", "daydream",
                               "dance", "ponder", "plane", "fly", "glasses", "mane", "roar"}


class PetBrain:

    def __init__(self, pet, idle_timeout=15.0, nap_after=180.0, rng=None, now=0.0,
                 boss=True, fox=True, can_leave=True):
        self.rng = rng or random.Random()
        self.pet = pet
        self.animator = Animator(pet, self.rng)
        self.idle_timeout = idle_timeout
        self.nap_after = nap_after  # None — не засыпать
        self.last_key = self.last_mouse = self.last_wheel = -1e9
        self.last_activity = now
        self.busy_since = None
        self.pending_reaction = None
        self.can_leave = can_leave  # иногда выходить из кабинета
        self.back_at = None       # когда вернуться в кабинет
        self.boss_mode = None     # None / "caught" / "listen" / "away"
        self.boss = Boss(self.rng, now, boss)
        self.fox = Fox(self.rng, now, fox)
        self.update(now)

    # -------------------------------------------------- события

    def key(self, now, combo=None):
        self.last_key = self.last_activity = now
        if combo in COMBOS:
            self.pending_reaction = COMBOS[combo]

    def mouse(self, now, wheel=False):
        self.last_mouse = self.last_activity = now
        if wheel:
            self.last_wheel = now

    def poke(self, now):
        self.pending_reaction = "wave"

    def set_busy(self, busy, now):
        if busy and self.busy_since is None:
            self.busy_since = now
        elif not busy and self.busy_since is not None:
            # QGIS закончил — питомец ещё посмотрит на результат
            self.busy_since = None
            self.last_activity = now

    def set_pet(self, pet, now):
        self.pet = pet
        self.animator.pet = pet
        self.animator.name = None
        self.animator.from_pose = None
        self.update(now)

    # -------------------------------------------------- решение

    def wanted(self, now):
        """Чем питомец должен заниматься сейчас: занятие или группа (focus/idle)."""
        if now - max(self.last_key, self.last_mouse) < WORK_HOLD:
            if self.last_key >= self.last_mouse:
                return "typing"
            return "scroll" if self.last_wheel >= self.last_mouse - 0.3 else "mouse"
        if self.busy_since is not None and now - self.busy_since >= BUSY_DELAY:
            return "thinking"
        idle_for = now - self.last_activity
        if idle_for < self.idle_timeout:
            return "focus"
        if self.nap_after is not None and idle_for >= self.nap_after:
            return "nap"
        return "idle"

    # -------------------------------------------------- начальник

    def boss_check(self, now):
        """Начальник вошёл и смотрит, чем занят питомец."""
        name = self.animator.name
        if name in ("leave", "gone"):
            self.boss_mode = "away"
            return "away"
        if name in SLACKING:
            self.boss_mode = "caught"
            self.pending_reaction = "startle"
            return "caught"
        self.boss_mode = "listen"
        return "working"

    def boss_left(self, now):
        if self.boss_mode in ("caught", "listen"):
            self.last_activity = now  # после разговора ещё поработает
        self.boss_mode = None

    @property
    def away(self):
        return self.animator.name in AWAY

    # -------------------------------------------------- решение

    def update(self, now):
        self.boss.update(now, self)
        self.fox.update(now, self, self.boss.present)
        return self.decide(now)

    def decide(self, now):
        anim = self.animator
        current = anim.name

        if self.pending_reaction:
            if current in AWAY and self.pending_reaction != "startle":
                self.pending_reaction = None  # питомца нет на месте — махать некому
            else:
                anim.play(self.pending_reaction, now)
                self.pending_reaction = None
                return anim.name
        if current in REACTIONS and not anim.finished(now):
            return current

        # вышел из кабинета: ушёл → пусто → вернулся
        if current == "leave":
            anim.play("gone", now)
            total = self.rng.uniform(*AWAY_TIME)
            walking = ACTIVITIES["leave"].duration + ACTIVITIES["return"].duration
            self.back_at = now + max(5.0, total - walking)
            return "gone"
        if current == "gone":
            if self.boss_mode == "away":
                return current  # при начальнике не возвращается
            if now >= self.back_at or self.wanted(now) not in ("idle", "nap"):
                anim.play("return", now)
                return "return"
            return current

        if self.boss_mode == "caught":
            anim.play("fake_typing", now)
            return "fake_typing"
        if self.boss_mode == "listen":
            anim.play("listen", now)
            return "listen"

        name = self.wanted(now)
        if current == "nap" and name != "nap":
            anim.play("wake", now)
            return "wake"
        if name in ("focus", "idle"):
            group = self.choices(name)
            if current in group and not anim.finished(now):
                return current
            # после работы сначала дочитывает то, что на экране
            name = "read" if name == "focus" and current not in group else self.pick(name, group)
        anim.play(name, now)
        return name

    def choices(self, group):
        if group == "focus":
            return list(FOCUS)
        return IDLE_COMMON + list(self.pet["specials"]) + (["leave"] if self.can_leave else [])

    def idle_choices(self):
        return self.choices("idle")

    def pick(self, group, choices):
        options = [n for n in choices if n != self.animator.name]
        weights = [1.5 if n in self.pet["specials"] else LEAVE_WEIGHT if n == "leave" else 1.0
                   for n in options]
        return self.rng.choices(options, weights)[0]

    # -------------------------------------------------- для рисования

    def pose(self, now):
        p = self.animator.pose(now)
        p["eyes"] *= self.animator.blink(now)
        return p

    def screen(self):
        return self.animator.activity.screen

    def visitors(self, now):
        return {"boss": self.boss.render(now), "fox": self.fox.render(now)}
