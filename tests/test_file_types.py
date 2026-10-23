"""The Windows file-type script offers exactly the formats the player opens."""
from pathlib import Path
import re
import unittest

from duplo.model import EXTENSIONS

SCRIPT = Path(__file__).resolve().parent.parent / 'tools' / 'register-file-types.ps1'


class FileTypeScriptTests(unittest.TestCase):
    def test_script_extensions_match_the_player(self):
        text = SCRIPT.read_text(encoding='utf-8-sig')
        listing = re.search(r'\$Extensions = @\((.*?)\)', text, re.S).group(1)
        self.assertEqual(set(re.findall(r"'(\.[a-z0-9]+)'", listing)), EXTENSIONS)

    def test_script_only_writes_the_current_user_registry(self):
        text = SCRIPT.read_text(encoding='utf-8-sig')
        self.assertNotIn('HKLM:', text)
        self.assertNotIn('UserChoice', text)


if __name__ == '__main__':
    unittest.main()
