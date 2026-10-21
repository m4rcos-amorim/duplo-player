"""The interface exists in English and Portuguese, and the two stay in step."""
import os
import re
import string
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication, QPushButton

from duplo import i18n
from duplo.i18n import tr
from duplo.model import PlaybackOrder, Repeat
from duplo.window import PlayerWindow

app = QApplication.instance() or QApplication([])
ACCENTED = re.compile('[áàâãéêíóôõúçÁÉÍÓÚÇ]')
# These strings are bilingual on purpose (the language menu is shown to everyone).
BILINGUAL = {'menu.language'}


def fields(text):
    return sorted(name for _, name, _, _ in string.Formatter().parse(text) if name is not None)


class TranslationTableTests(unittest.TestCase):
    def test_every_key_has_both_languages_with_the_same_placeholders(self):
        for key in i18n.keys():
            pt, en = i18n.pair(key)
            self.assertTrue(pt.strip() and en.strip(), key)
            self.assertEqual(fields(pt), fields(en), f'placeholders differ in {key}')

    def test_english_text_has_no_portuguese_accents(self):
        for key in i18n.keys():
            if key in BILINGUAL:
                continue
            self.assertIsNone(ACCENTED.search(i18n.pair(key)[1]), f'accented text in English for {key}')

    def test_help_text_has_the_same_number_of_lines_in_both_languages(self):
        pt, en = i18n.pair('help.body')
        self.assertEqual(len(pt.splitlines()), len(en.splitlines()))

    def test_unknown_language_and_key_are_rejected(self):
        with self.assertRaises(ValueError):
            i18n.set_language('xx')
        with self.assertRaises(KeyError):
            tr('does.not.exist')


class LanguageChoiceTests(unittest.TestCase):
    def setUp(self):
        self.saved = i18n.language()
        self.env = os.environ.pop('DUPLO_LANG', None)

    def tearDown(self):
        i18n.set_language(self.saved)
        os.environ.pop('DUPLO_LANG', None)
        if self.env is not None:
            os.environ['DUPLO_LANG'] = self.env

    class FakeSettings:
        def __init__(self, value):
            self.stored = value

        def value(self, key, default=None):
            return self.stored if key == 'language' else default

    def test_environment_variable_wins(self):
        os.environ['DUPLO_LANG'] = 'pt'
        self.assertEqual(i18n.init(self.FakeSettings('en')), 'pt')

    def test_saved_setting_is_used_without_the_variable(self):
        self.assertEqual(i18n.init(self.FakeSettings('pt')), 'pt')
        self.assertEqual(i18n.init(self.FakeSettings('en')), 'en')

    def test_invalid_setting_falls_back_to_the_system_language(self):
        self.assertIn(i18n.init(self.FakeSettings('klingon')), ('en', 'pt'))

    def test_enum_labels_follow_the_language(self):
        i18n.set_language('en')
        self.assertEqual(Repeat.ALL.label, 'Repeat list')
        self.assertEqual(PlaybackOrder.SHUFFLE_LIST.label, 'Shuffle list')
        i18n.set_language('pt')
        self.assertEqual(Repeat.ALL.label, 'Repetir lista')
        self.assertEqual(PlaybackOrder.SHUFFLE_LIST.label, 'Aleatório lista')


class WindowLanguageTests(unittest.TestCase):
    def tearDown(self):
        window = getattr(self, 'window', None)
        if window is not None:
            window.close()

    def make(self, language):
        i18n.set_language(language)
        self.window = PlayerWindow(silent=True, settings=False)
        return self.window

    def test_english_window_shows_no_portuguese(self):
        window = self.make('en')
        texts = [window.list_count.text(), window.filename.text(), window.ab_label.text(),
                 window.zoom_info.text(), window.record_info.text(), window.statusBar().currentMessage()]
        for button in window.findChildren(QPushButton):
            texts += [button.toolTip(), button.accessibleName()]
        texts = [text for text in texts if text]
        self.assertTrue(texts)
        for text in texts:
            self.assertIsNone(ACCENTED.search(text), text)
        self.assertEqual(window.filename.text(), 'No video open')
        self.assertIn('Sequential', window.shuffle_button.toolTip())
        self.assertIn('No repeat', window.repeat_button.toolTip())
        self.assertEqual(window.list_count.text(), 'LIST · 0 videos')
        self.assertTrue(window.zoom_info.text().startswith('View A'))

    def test_portuguese_window_keeps_its_original_text(self):
        window = self.make('pt')
        self.assertEqual(window.filename.text(), 'Nenhum vídeo aberto')
        self.assertEqual(window.list_count.text(), 'LISTA · 0 vídeos')
        self.assertIn('Sequencial', window.shuffle_button.toolTip())
        self.assertTrue(window.zoom_info.text().startswith('Perspectiva A'))

    def test_changing_language_is_saved_for_the_next_start(self):
        window = self.make('en')

        class Settings:
            saved = {}

            def setValue(self, key, value):
                self.saved[key] = value

        window.settings = Settings()
        from unittest.mock import patch
        with patch('duplo.window.QMessageBox.information') as notice:
            window.choose_language('pt')
            window.choose_language('en')  # same as the current language: nothing to do
        self.assertEqual(Settings.saved, {'language': 'pt'})
        notice.assert_called_once()
        window.settings = None


if __name__ == '__main__':
    unittest.main()
