# -*- coding: utf-8 -*-
"""Окно вопроса викторины в стиле «Кто хочет стать миллионером».

Щелчок по ответу: правильный — подсвечивается жёлтым; неправильный — выбранный
загорается красным, а правильный — жёлтым. Через несколько секунд (или по
кнопке «Дальше») окно возвращается к питомцу.
"""

import html

from qgis.PyQt.QtCore import Qt, QTimer, pyqtSignal
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from .quiz import LETTERS

AUTO_CLOSE_MS = 6000

BACKGROUND = ("#QPetsQuiz { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
              "stop:0 #142C78, stop:1 #050B2C); }")
QUESTION_STYLE = ("color: white; background: #0A1640; border: 2px solid #7FA7FF; "
                  "border-radius: 10px; padding: 4px 6px; font-size: 9pt;")
ANSWER_STYLES = {
    "normal": "color: white; background: #0B1A4A; border: 2px solid #5D86E8;",
    "right": "color: #1A1200; background: #F5B700; border: 2px solid #FFE082;",
    "wrong": "color: white; background: #B3261E; border: 2px solid #FF8A80;",
    "dim": "color: #8A97C2; background: #0B1A4A; border: 2px solid #34457A;",
}
BUTTON_STYLE = ("QPushButton { color: #F5C542; background: transparent; border: 1px solid #F5C542; "
                "border-radius: 8px; padding: 1px 8px; font-size: 8pt; } "
                "QPushButton:hover { background: #1C3380; }")


class AnswerLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class QuizWidget(QWidget):
    answered = pyqtSignal(bool)  # правильно ли ответили
    finished = pyqtSignal()      # вернуться к питомцу

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("QPetsQuiz")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(BACKGROUND)
        self.setMinimumSize(0, 0)
        self.question = None
        self.done = False

        self.title = QLabel("Викторина: Лесоустроительная инструкция", self)
        self.title.setStyleSheet("color: #F5C542; font-weight: bold; font-size: 8pt;")
        self.title.setWordWrap(True)
        self.text = QLabel(self)
        self.text.setWordWrap(True)
        self.text.setStyleSheet(QUESTION_STYLE)
        self.text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.answers = []
        for i in range(4):
            label = AnswerLabel(self)
            label.clicked.connect(lambda i=i: self.choose(i))
            self.answers.append(label)
        self.result = QLabel(self)
        self.result.setWordWrap(True)
        self.button = QPushButton("Пропустить", self)
        self.button.setStyleSheet(BUTTON_STYLE)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.clicked.connect(self.close_question)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close_question)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.addWidget(self.result, 1)
        bottom.addWidget(self.button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)
        for label in [self.title, self.text, self.result] + self.answers:
            label.setMinimumWidth(1)  # длинный текст переносится, а не раздвигает окно
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.title)
        layout.addWidget(self.text)
        for label in self.answers:
            layout.addWidget(label)
        layout.addStretch(1)
        layout.addLayout(bottom)

    def show_question(self, question, score_text=""):
        self.question = question
        self.done = False
        self.timer.stop()
        self.text.setText(question["q"])
        for i, label in enumerate(self.answers):
            self.paint_answer(i, "normal")
        self.result.setText(score_text)
        self.result.setStyleSheet("color: #8A97C2; font-size: 8pt;")
        self.button.setText("Пропустить")

    def paint_answer(self, i, state):
        letter_color = "#1A1200" if state == "right" else "#F5A623"
        text = html.escape(self.question["options"][i])
        self.answers[i].setText("<span style='color:%s; font-weight:bold'>%s:</span> %s"
                                % (letter_color, LETTERS[i], text))
        self.answers[i].setStyleSheet(ANSWER_STYLES[state]
                                      + " border-radius: 11px; padding: 3px 7px; font-size: 9pt;")

    def choose(self, i):
        if self.done or self.question is None:
            return
        self.done = True
        right = self.question["answer"]
        for k in range(4):
            state = "right" if k == right else "wrong" if k == i else "dim"
            self.paint_answer(k, state)
        ok = i == right
        ref = self.question.get("ref")
        tail = " (%s)" % ref if ref else ""
        if ok:
            self.result.setText("Правильно!" + tail)
            self.result.setStyleSheet("color: #7CFC9A; font-weight: bold; font-size: 8pt;")
        else:
            self.result.setText("Неправильно. Верный ответ — %s%s" % (LETTERS[right], tail))
            self.result.setStyleSheet("color: #FF8A80; font-weight: bold; font-size: 8pt;")
        self.button.setText("Дальше")
        self.answered.emit(ok)
        self.timer.start(AUTO_CLOSE_MS)

    def close_question(self):
        self.timer.stop()
        self.finished.emit()
