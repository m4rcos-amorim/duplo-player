"""File names of recorded segments and joined videos."""
from pathlib import Path
import tempfile
import unittest

from duplo.recording import joined_path, segment_path


class RecordingNameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_segments_are_numbered_per_video(self):
        video = Path('D:/Filmes/Jogo final, 2ª parte.mp4')
        self.assertEqual(segment_path(self.folder, video).name, 'Jogo final, 2ª parte_T1.mp4')
        for name in ('Jogo final, 2ª parte_T1.mp4', 'Jogo final, 2ª parte_T3.mp4', 'Outro_T7.mp4',
                     'Jogo final, 2ª parte_T2.mp4.part', 'Jogo final, 2ª parte_Tx.mp4'):
            (self.folder / name).touch()
        # After the highest number of the same video; other videos do not count.
        self.assertEqual(segment_path(self.folder, video).name, 'Jogo final, 2ª parte_T4.mp4')
        self.assertEqual(segment_path(self.folder, Path('Outro.mkv')).name, 'Outro_T8.mp4')
        self.assertEqual(segment_path(self.folder, Path('Novo.avi')).name, 'Novo_T1.mp4')

    def test_segment_without_a_video_name(self):
        self.assertEqual(segment_path(self.folder, None).name, 'Duplo_T1.mp4')

    def test_joined_video_uses_the_first_segment_name_and_never_overwrites(self):
        segments = [Path('trechos/Aula 3_T2.mp4'), Path('trechos/Aula 3_T5.mp4'), Path('trechos/Outro_T1.mp4')]
        self.assertEqual(joined_path(self.folder, segments).name, 'Aula 3_joined.mp4')
        (self.folder / 'Aula 3_joined.mp4').touch()
        (self.folder / 'Aula 3_joined_2.mp4').touch()
        self.assertEqual(joined_path(self.folder, segments).name, 'Aula 3_joined_3.mp4')


if __name__ == '__main__':
    unittest.main()
