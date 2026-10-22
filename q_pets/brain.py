# -*- coding: utf-8 -*-
"""Поведение питомца (без Qt): что он делает в зависимости от действий пользователя.

Порядок важности:
1. реакция (помахать после щелчка по питомцу, проснуться);
2. только что нажимали клавиши или мышь — печатает или работает мышкой;
3. QGIS занят дольше BUSY_DELAY — ждёт вместе с QGIS;
4. простой меньше idle_timeout — продолжает работать (читает экран);
5. дольше — занимается своими делами, а после nap_after — дремлет.
"""

import random

from .animation import IDLE_COMMON, Animator

WORK_HOLD = 1.2   # сек.: столько ещё печатает/водит мышкой после последнего нажатия
BUSY_DELAY = 0.7  # сек.: короткая перерисовка карты не отвлекает питомца
REACTIONS = ("wave", "wake")


class PetBrain:

    def __init__(self, pet, idle_timeout=15.0, nap_after=180.0, rng=None, now=0.0):
        self.rng = rng or random.Random()
        self.pet = pet
        self.animator = Animator(pet, self.rng)
        self.idle_timeout = idle_timeout
        self.nap_after = nap_after  # None — не засыпать
        self.last_key = self.last_mouse = -1e9
        self.last_activity = now
        self.busy_since = None
        self.pending_reaction = None
        self.last_idle = None
        self.update(now)

    # -------------------------------------------------- события

    def key(self, now):
        self.last_key = self.last_activity = now

    def mouse(self, now):
        self.last_mouse = self.last_activity = now

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
        self.last_idle = None
        self.animator.name = None
        self.animator.from_pose = None
        self.update(now)

    # -------------------------------------------------- решение

    def wanted(self, now):
        """Чем питомец должен заниматься сейчас, без учёта реакций."""
        if now - max(self.last_key, self.last_mouse) < WORK_HOLD:
            return "typing" if self.last_key >= self.last_mouse else "mouse"
        if self.busy_since is not None and now - self.busy_since >= BUSY_DELAY:
            return "thinking"
        idle_for = now - self.last_activity
        if idle_for < self.idle_timeout:
            return "focus"
        if self.nap_after is not None and idle_for >= self.nap_after:
            return "nap"
        return None  # свои дела

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
        if name is None:
            if current in self.idle_choices() and not anim.finished(now):
                return current
            name = self.next_idle()
        anim.play(name, now)
        return name

    def idle_choices(self):
        return IDLE_COMMON + [self.pet["special"]]

    def next_idle(self):
        choices = [n for n in self.idle_choices() if n != self.last_idle]
        weights = [1.6 if n == self.pet["special"] else 1.0 for n in choices]
        self.last_idle = self.rng.choices(choices, weights)[0]
        return self.last_idle

    # -------------------------------------------------- для рисования

    def pose(self, now):
        p = self.animator.pose(now)
        p["eyes"] *= self.animator.blink(now)
        return p

    def screen(self):
        return self.animator.activity.screen
