# -*- coding: utf-8 -*-
"""Поведение питомца (без Qt): что он делает в зависимости от действий пользователя.

Порядок важности:
1. реакция (помахать после щелчка, «сохранено» на Ctrl+S, «ой» на Ctrl+Z, проснуться);
2. только что нажимали клавиши или мышь — печатает, водит мышкой или крутит колёсико;
3. QGIS занят дольше BUSY_DELAY — ждёт вместе с QGIS;
4. простой меньше idle_timeout — работает без нажатий (читает экран, пишет заметки…);
5. дольше — занимается своими делами, а после nap_after — дремлет.
"""

import random

from .animation import FOCUS, IDLE_COMMON, REACTIONS, Animator

WORK_HOLD = 1.2   # сек.: столько ещё печатает/водит мышкой после последнего нажатия
BUSY_DELAY = 0.7  # сек.: короткая перерисовка карты не отвлекает питомца
COMBOS = {"save": "saved", "undo": "oops"}


class PetBrain:

    def __init__(self, pet, idle_timeout=15.0, nap_after=180.0, rng=None, now=0.0):
        self.rng = rng or random.Random()
        self.pet = pet
        self.animator = Animator(pet, self.rng)
        self.idle_timeout = idle_timeout
        self.nap_after = nap_after  # None — не засыпать
        self.last_key = self.last_mouse = self.last_wheel = -1e9
        self.last_activity = now
        self.busy_since = None
        self.pending_reaction = None
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

    def update(self, now):
        anim = self.animator
        current = anim.name

        if self.pending_reaction:
            anim.play(self.pending_reaction, now)
            self.pending_reaction = None
            return anim.name
        if current in REACTIONS and not anim.finished(now):
            return current

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
        return IDLE_COMMON + list(self.pet["specials"])

    def idle_choices(self):
        return self.choices("idle")

    def pick(self, group, choices):
        options = [n for n in choices if n != self.animator.name]
        weights = [1.5 if n in self.pet["specials"] else 1.0 for n in options]
        return self.rng.choices(options, weights)[0]

    # -------------------------------------------------- для рисования

    def pose(self, now):
        p = self.animator.pose(now)
        p["eyes"] *= self.animator.blink(now)
        return p

    def screen(self):
        return self.animator.activity.screen
