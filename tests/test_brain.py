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

from q_pets.animation import (ACTIVITIES, BASE, FOCUS, IDLE_COMMON, Animator,  # noqa: E402
                               keyframes)
from q_pets.brain import BUSY_DELAY, WORK_HOLD, PetBrain  # noqa: E402
from q_pets.pets import PETS, get_pet  # noqa: E402


def make_brain(pet=None, **kwargs):
    """По умолчанию без гостей и без ухода из кабинета — чтобы время в тестах было предсказуемым."""
    options = dict(boss=False, fox=False, can_leave=False)
    options.update(kwargs)
    return PetBrain(pet or PETS[0], rng=random.Random(1), now=0.0, **options)


class BrainTest(unittest.TestCase):

    def test_starts_working(self):
        brain = make_brain()
        self.assertEqual(brain.update(0.1), "read")

    def test_typing_mouse_and_wheel(self):
        brain = make_brain()
        brain.key(1.0)
        self.assertEqual(brain.update(1.1), "typing")
        brain.mouse(1.5)
        self.assertEqual(brain.update(1.6), "mouse")
        brain.mouse(2.0, wheel=True)
        self.assertEqual(brain.update(2.1), "scroll")
        brain.mouse(2.2)  # чуть сдвинул мышь, пока крутил колёсико — всё ещё крутит
        self.assertEqual(brain.update(2.3), "scroll")
        brain.mouse(3.0)
        self.assertEqual(brain.update(3.1), "mouse")
        # после работы сначала дочитывает экран
        self.assertEqual(brain.update(3.0 + WORK_HOLD + 0.1), "read")

    def test_focus_varies_without_input(self):
        brain = make_brain(idle_timeout=60.0)
        now, seen, previous = 0.0, [], None
        while now < 59.0:
            name = brain.update(now)
            if name != previous:
                seen.append(name)
                previous = name
            now += 0.1
        self.assertEqual(seen[0], "read")
        self.assertTrue(set(seen) <= set(FOCUS))
        self.assertGreaterEqual(len(set(seen)), 4)
        self.assertTrue(all(a != b for a, b in zip(seen, seen[1:])))

    def test_save_and_undo_reactions(self):
        brain = make_brain()
        brain.key(5.0, "save")
        self.assertEqual(brain.update(5.0), "saved")
        brain.key(6.5)
        self.assertEqual(brain.update(6.6), "saved")  # сначала порадуется
        self.assertEqual(brain.update(5.0 + ACTIVITIES["saved"].duration + 0.05), "typing")
        brain.key(10.0, "undo")
        self.assertEqual(brain.update(10.0), "oops")
        brain.key(11.0, "copy")  # прочие сочетания — просто печатает
        self.assertEqual(brain.update(12.1), "typing")

    def test_rest_after_idle_timeout(self):
        brain = make_brain()
        brain.key(1.0)
        self.assertIn(brain.update(15.9), FOCUS)
        name = brain.update(16.1)
        self.assertIn(name, brain.idle_choices())
        # занятие длится до конца, потом сменяется другим
        duration = ACTIVITIES[name].duration
        self.assertEqual(brain.update(16.1 + duration - 0.1), name)
        self.assertNotEqual(brain.update(16.1 + duration + 0.05), name)

    def test_custom_idle_timeout(self):
        brain = make_brain(idle_timeout=30.0)
        self.assertIn(brain.update(20.0), FOCUS)
        self.assertIn(brain.update(31.0), brain.idle_choices())

    def test_input_interrupts_rest(self):
        brain = make_brain()
        self.assertIn(brain.update(20.0), brain.idle_choices())
        brain.key(21.0)
        self.assertEqual(brain.update(21.05), "typing")

    def test_waits_while_qgis_busy(self):
        brain = make_brain()
        brain.set_busy(True, 5.0)
        self.assertIn(brain.update(5.0 + BUSY_DELAY / 2), FOCUS)  # короткая перерисовка
        self.assertEqual(brain.update(5.0 + BUSY_DELAY + 0.1), "thinking")
        brain.key(7.0)
        self.assertEqual(brain.update(7.1), "typing")  # сам пользователь важнее
        self.assertEqual(brain.update(7.0 + WORK_HOLD + 0.1), "thinking")
        # долгий расчёт во время простоя — всё равно ждёт вместе с QGIS
        self.assertEqual(brain.update(60.0), "thinking")
        brain.set_busy(False, 61.0)
        self.assertEqual(brain.update(61.1), "read")  # смотрит на результат
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

    def test_idle_choices_include_specials(self):
        for pet in PETS:
            brain = make_brain(pet)
            for special in pet["specials"]:
                self.assertIn(special, brain.idle_choices())
                self.assertIn(special, ACTIVITIES)
            seen = set()
            now = 20.0
            for _ in range(200):
                brain.animator.name = None
                seen.add(brain.update(now))
                now += 0.01
            self.assertEqual(seen, set(IDLE_COMMON + pet["specials"]))
        self.assertIn("leave", make_brain(can_leave=True).idle_choices())

    def test_no_same_rest_twice_in_a_row(self):
        brain = make_brain(nap_after=None)
        previous = None
        now = 16.0
        for _ in range(30):
            name = brain.update(now)
            self.assertNotEqual(name, previous)
            previous = name
            now += ACTIVITIES[name].duration + 0.01

    def test_leaves_the_room_and_comes_back(self):
        brain = make_brain(can_leave=True)
        brain.animator.play("leave", 20.0)
        self.assertEqual(brain.update(21.0), "leave")  # доходит до двери
        self.assertEqual(brain.update(23.5), "gone")
        away = brain.back_at - 23.5 + 3.4 + 3.3
        self.assertTrue(15.0 - 0.01 <= away <= 60.0 + 0.01, away)
        self.assertEqual(brain.update(brain.back_at - 0.1), "gone")
        self.assertEqual(brain.update(brain.back_at + 0.1), "return")
        self.assertNotIn(brain.update(brain.back_at + 3.5), ("gone", "return", "leave"))

    def test_input_brings_pet_back(self):
        brain = make_brain(can_leave=True)
        brain.animator.play("leave", 20.0)
        brain.update(23.5)
        brain.poke(24.0)
        self.assertEqual(brain.update(24.0), "gone")  # махать некому — питомца нет
        brain.key(25.0)
        self.assertEqual(brain.update(25.0), "return")
        self.assertEqual(brain.update(27.0), "return")  # сначала дойдёт до стола
        brain.key(28.3)
        self.assertEqual(brain.update(28.4), "typing")

    def test_walks_out_of_frame(self):
        gone = ACTIVITIES["gone"].func(0.0, PETS[0])
        self.assertGreater(gone["bdx"], 200)  # за правым краем кадра
        back = ACTIVITIES["return"].func(ACTIVITIES["return"].duration, PETS[0])
        self.assertAlmostEqual(back["bdx"], 0.0, places=3)
        self.assertAlmostEqual(back["bdy"], 0.0, places=3)

    def test_switch_pet(self):
        brain = make_brain(PETS[0])
        for t in range(16, 40):
            brain.update(float(t))
        brain.set_pet(PETS[2], 40.0)
        self.assertNotIn("tiger", brain.idle_choices())
        self.assertNotIn(brain.animator.name, PETS[0]["specials"])
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
        props = ("mugx", "mugy", "mugrot", "phx", "phy", "phup", "phback", "hlx", "hly", "hrx",
                 "hry", "lew", "rew", "lb", "rb", "armsback", "bnx", "bny", "bnrot", "bnbite",
                 "bnpeel", "bnvis", "rdx", "rdy", "rdup", "toy", "pen", "rthumb", "rpeace",
                 "glassoff", "jug", "pbvis", "dumb", "spin", "fly", "ftongue", "puff", "ruffle",
                 "bdx", "bdy", "achoo", "roar")
        specials = [name for pet in PETS for name in pet["specials"]]
        for name in FOCUS + IDLE_COMMON + specials + ["saved", "oops"]:
            activity = ACTIVITIES[name]
            pose = activity.func(activity.duration, PETS[0])
            for key in props:
                self.assertAlmostEqual(pose[key], BASE[key], places=3, msg=(name, key))

    def test_mug_held_by_handle_and_tilted_to_mouth(self):
        """Отпивая, наклоняет кружку к губам (по часовой), а не от них."""
        sip = ACTIVITIES["coffee"].func(4.2, PETS[0])
        self.assertGreater(sip["mugrot"], 10)
        self.assertLess(abs(sip["mugx"] - 141), 6)
        self.assertGreater(sip["hlx"], sip["mugx"])  # ладонь на ручке — справа от кружки

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


class BossTest(unittest.TestCase):

    def visit(self, brain, start):
        brain.boss.enabled = True
        brain.boss.call(start)

    def test_catches_slacking_pet(self):
        brain = make_brain(boss=True)
        self.assertIn(brain.update(20.0), brain.idle_choices())  # отдыхает
        self.visit(brain, 21.0)
        brain.update(21.0)
        self.assertEqual(brain.boss.state, "enter")
        brain.update(23.7)  # начальник дошёл и смотрит
        self.assertEqual(brain.boss.outcome, "caught")
        self.assertEqual(brain.animator.name, "startle")
        self.assertEqual(brain.update(24.9), "fake_typing")
        self.assertEqual(brain.update(28.0), "fake_typing")
        brain.update(30.8)  # поговорил и уходит
        self.assertEqual(brain.boss.state, "leave")
        self.assertIn(brain.update(30.9), FOCUS)  # после начальника ещё работает
        brain.update(33.5)
        self.assertFalse(brain.boss.present)
        self.assertGreater(brain.boss.next_visit, 33.5 + 400)

    def test_napping_pet_is_caught_too(self):
        brain = make_brain(boss=True, nap_after=60.0)
        for t in range(16, 70, 2):
            brain.update(float(t))
        self.assertEqual(brain.animator.name, "nap")
        self.visit(brain, 70.0)
        brain.update(70.0)
        brain.update(72.7)
        self.assertEqual(brain.boss.outcome, "caught")

    def test_working_pet_gets_a_task(self):
        brain = make_brain(boss=True)
        self.visit(brain, 5.0)
        t = 5.0
        while t < 7.8:
            brain.key(t)
            brain.update(t)
            t += 0.1
        self.assertEqual(brain.boss.outcome, "working")
        self.assertEqual(brain.animator.name, "listen")
        view = brain.boss.render(t + 5.5)
        self.assertGreater(view["reply_a"], 0.5)  # «Сделаю!»
        self.assertIn(view["reply"], ("Сделаю!", "Будет готово!", "Уже занимаюсь!", "Принято!"))

    def test_empty_chair(self):
        brain = make_brain(boss=True, can_leave=True)
        brain.animator.play("leave", 20.0)
        brain.update(23.5)
        brain.back_at = 1e9
        self.visit(brain, 24.0)
        brain.update(24.0)
        brain.update(26.7)
        self.assertEqual(brain.boss.outcome, "away")
        brain.back_at = 27.0
        self.assertEqual(brain.update(28.0), "gone")  # при начальнике не возвращается
        brain.update(33.8)
        self.assertEqual(brain.update(33.9), "return")

    def test_names_pet_in_lines(self):
        brain = make_brain(PETS[4], boss=True)
        lines = set()
        for i in range(40):
            brain.boss.state = None
            self.visit(brain, 100.0 * i)
            brain.update(100.0 * i)
            brain.key(100.0 * i + 2.5)
            brain.update(100.0 * i + 2.7)
            lines.add(brain.boss.line)
        self.assertTrue(any("Денис" in line for line in lines))
        self.assertFalse(any("{name}" in line for line in lines))


class FoxTest(unittest.TestCase):

    def test_peeks_and_thinks(self):
        brain = make_brain(fox=True)
        brain.fox.call(1.0)
        brain.update(1.0)
        self.assertTrue(brain.fox.present)
        view = brain.fox.render(5.0)
        self.assertGreater(view["rise"], 0.9)
        self.assertGreater(view["think_a"], 0.9)
        self.assertTrue(14 < view["x"] < 106)  # внутри окна
        brain.update(11.5)
        self.assertFalse(brain.fox.present)

    def test_hides_when_spotted(self):
        brain = make_brain(fox=True)
        brain.fox.call(1.0)
        brain.update(1.0)
        brain.animator.play("window", 2.0)  # питомец посмотрел в окно
        brain.fox.update(2.5, brain, False)
        self.assertIsNotNone(brain.fox.duck_at)
        self.assertEqual(brain.fox.render(2.6)["think_a"], 0.0)
        brain.fox.update(3.2, brain, False)
        self.assertFalse(brain.fox.present)

    def test_no_fox_while_boss_is_here(self):
        brain = make_brain(fox=True, boss=True)
        brain.boss.call(1.0)
        brain.fox.call(1.0)
        brain.update(1.0)
        self.assertTrue(brain.boss.present)
        self.assertFalse(brain.fox.present)


class QuizTest(unittest.TestCase):

    QUESTIONS = [{"id": i, "q": "Вопрос %d?" % i,
                  "options": ["верно %d" % i, "нет a", "нет b", "нет c"], "ref": "п. %d" % i}
                 for i in range(1, 6)]

    def test_shuffles_options_and_keeps_answer(self):
        from q_pets.quiz import Quiz
        quiz = Quiz(self.QUESTIONS, rng=random.Random(2))
        seen_positions = set()
        for _ in range(5):
            q = quiz.next()
            self.assertEqual(q["options"][q["answer"]], "верно %d" % q["id"])
            self.assertEqual(set(q["options"]) - {"верно %d" % q["id"]}, {"нет a", "нет b", "нет c"})
            seen_positions.add(q["answer"])
        self.assertGreater(len(seen_positions), 1)

    def test_no_repeats_until_all_asked(self):
        from q_pets.quiz import Quiz
        quiz = Quiz(self.QUESTIONS, seen=[1, 2], rng=random.Random(3))
        ids = [quiz.next()["id"] for _ in range(3)]
        self.assertEqual(sorted(ids), [3, 4, 5])
        self.assertIn(quiz.next()["id"], range(1, 6))  # круг пройден — заново
        self.assertEqual(len(quiz.seen), 1)

    def test_ids_round_trip(self):
        from q_pets.quiz import format_ids, parse_ids
        self.assertEqual(parse_ids(format_ids([3, 17, 42])), [3, 17, 42])
        self.assertEqual(parse_ids(""), [])
        self.assertEqual(parse_ids(None), [])

    def test_bundled_questions_are_well_formed(self):
        from q_pets.quiz_questions import QUESTIONS
        ids = [q["id"] for q in QUESTIONS]
        self.assertEqual(len(ids), len(set(ids)))
        for q in QUESTIONS:
            self.assertEqual(len(q["options"]), 4, q["id"])
            self.assertEqual(len(set(q["options"])), 4, q["id"])
            self.assertTrue(q["q"].strip())


if __name__ == "__main__":
    unittest.main()
