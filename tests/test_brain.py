# -*- coding: utf-8 -*-
"""Поведение питомца и анимации (Qt не нужен).

Запуск:  python -m unittest discover tests
"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from q_pets.animation import ACTIVITIES, BASE, IDLE_COMMON, Animator, keyframes  # noqa: E402
from q_pets.brain import BUSY_DELAY, WORK_HOLD, PetBrain  # noqa: E402
from q_pets.pets import PETS, get_pet  # noqa: E402


def make_brain(pet=None, **kwargs):
    return PetBrain(pet or PETS[0], rng=random.Random(1), now=0.0, **kwargs)


class BrainTest(unittest.TestCase):

    def test_starts_working(self):
        brain = make_brain()
        self.assertEqual(brain.update(0.1), "focus")

    def test_typing_and_mouse(self):
        brain = make_brain()
        brain.key(1.0)
        self.assertEqual(brain.update(1.1), "typing")
        brain.mouse(1.5)
        self.assertEqual(brain.update(1.6), "mouse")
        self.assertEqual(brain.update(1.5 + WORK_HOLD + 0.1), "focus")

    def test_rest_after_idle_timeout(self):
        brain = make_brain()
        brain.key(1.0)
        self.assertEqual(brain.update(15.9), "focus")
        name = brain.update(16.1)
        self.assertIn(name, brain.idle_choices())
        # занятие длится до конца, потом сменяется другим
        duration = ACTIVITIES[name].duration
        self.assertEqual(brain.update(16.1 + duration - 0.1), name)
        self.assertNotEqual(brain.update(16.1 + duration + 0.05), name)

    def test_custom_idle_timeout(self):
        brain = make_brain(idle_timeout=30.0)
        self.assertEqual(brain.update(20.0), "focus")
        self.assertIn(brain.update(31.0), brain.idle_choices())

    def test_input_interrupts_rest(self):
        brain = make_brain()
        self.assertIn(brain.update(20.0), brain.idle_choices())
        brain.key(21.0)
        self.assertEqual(brain.update(21.05), "typing")

    def test_waits_while_qgis_busy(self):
        brain = make_brain()
        brain.set_busy(True, 5.0)
        self.assertEqual(brain.update(5.0 + BUSY_DELAY / 2), "focus")  # короткая перерисовка
        self.assertEqual(brain.update(5.0 + BUSY_DELAY + 0.1), "thinking")
        brain.key(7.0)
        self.assertEqual(brain.update(7.1), "typing")  # сам пользователь важнее
        self.assertEqual(brain.update(7.0 + WORK_HOLD + 0.1), "thinking")
        # долгий расчёт во время простоя — всё равно ждёт вместе с QGIS
        self.assertEqual(brain.update(60.0), "thinking")
        brain.set_busy(False, 61.0)
        self.assertEqual(brain.update(61.1), "focus")  # смотрит на результат
        self.assertIn(brain.update(61.0 + 15.1), brain.idle_choices())

    def test_nap_and_wake(self):
        brain = make_brain(nap_after=100.0)
        for t in range(16, 100, 2):
            brain.update(float(t))
        self.assertEqual(brain.update(100.5), "nap")
        self.assertEqual(brain.update(300.0), "nap")
        brain.mouse(301.0)
        self.assertEqual(brain.update(301.05), "wake")
        self.assertEqual(brain.update(301.5), "wake")
        self.assertEqual(brain.update(302.0), "mouse")

    def test_nap_disabled(self):
        brain = make_brain(nap_after=None)
        self.assertNotEqual(brain.update(1000.0), "nap")

    def test_poke_waves_then_returns(self):
        brain = make_brain()
        brain.poke(3.0)
        self.assertEqual(brain.update(3.0), "wave")
        brain.key(4.0)
        self.assertEqual(brain.update(4.1), "wave")  # сначала домашет
        self.assertEqual(brain.update(4.9), "typing")

    def test_idle_choices_include_special(self):
        for pet in PETS:
            brain = make_brain(pet)
            self.assertIn(pet["special"], brain.idle_choices())
            seen = set()
            now = 20.0
            for _ in range(60):
                brain.animator.name = None
                seen.add(brain.update(now))
                now += 0.01
            self.assertEqual(seen, set(IDLE_COMMON + [pet["special"]]))

    def test_no_same_rest_twice_in_a_row(self):
        brain = make_brain(nap_after=None)
        previous = None
        now = 16.0
        for _ in range(30):
            name = brain.update(now)
            self.assertNotEqual(name, previous)
            previous = name
            now += ACTIVITIES[name].duration + 0.01

    def test_switch_pet(self):
        brain = make_brain(PETS[0])
        for t in range(16, 40):
            brain.update(float(t))
        brain.set_pet(PETS[2], 40.0)
        self.assertNotIn("tiger", brain.idle_choices())
        self.assertNotEqual(brain.animator.name, "tiger")
        brain.pose(40.1)

    def test_unknown_pet_falls_back(self):
        self.assertIs(get_pet("нет такого"), PETS[0])


class AnimationTest(unittest.TestCase):

    def test_poses_are_complete_and_finite(self):
        for pet in PETS:
            for name, activity in ACTIVITIES.items():
                end = activity.duration or 20.0
                steps = 60
                for i in range(steps + 1):
                    pose = activity.func(end * i / steps, pet)
                    self.assertEqual(set(pose), set(BASE), name)
                    for key, value in pose.items():
                        self.assertTrue(math.isfinite(value), (name, key))

    def test_rests_end_where_work_starts(self):
        """Свои дела заканчиваются с кружкой и телефоном на месте и руками на клавиатуре."""
        for name in IDLE_COMMON + ["tiger", "daydream", "ponder"]:
            activity = ACTIVITIES[name]
            pose = activity.func(activity.duration, PETS[0])
            for key in ("mugx", "mugy", "phx", "phy", "phup", "hlx", "hly", "hrx", "hry"):
                self.assertAlmostEqual(pose[key], BASE[key], places=3, msg=(name, key))

    def test_keyframes_interpolate(self):
        track = keyframes((0.0, {}), (1.0, {"turn": 1.0}))
        self.assertAlmostEqual(track(0.0)["turn"], BASE["turn"])
        self.assertAlmostEqual(track(0.5)["turn"], (BASE["turn"] + 1.0) / 2)
        self.assertAlmostEqual(track(5.0)["turn"], 1.0)

    def test_blend_between_activities(self):
        anim = Animator(PETS[0], random.Random(0))
        anim.play("coffee", 0.0)
        held = anim.pose(3.0)
        self.assertLess(held["mugy"], 150)  # кружка у рта
        anim.play("typing", 3.0)
        self.assertAlmostEqual(anim.pose(3.0)["mugy"], held["mugy"], places=3)
        self.assertAlmostEqual(anim.pose(4.0)["mugy"], BASE["mugy"], places=3)

    def test_pet_pose_overrides(self):
        anim = Animator(PETS[0], random.Random(0))
        anim.play("typing", 0.0)
        self.assertEqual(anim.pose(1.0)["tongue"], 1.0)
        anim = Animator(PETS[2], random.Random(0))
        anim.play("typing", 0.0)
        self.assertEqual(anim.pose(1.0)["tongue"], 0.0)


if __name__ == "__main__":
    unittest.main()
