from pathlib import Path
import random
import tempfile
import unittest

from duplo.model import ABLoop, Playlist, Repeat, PlaybackOrder, timestamp


class PlaylistTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.paths = [Path(self.directory.name) / f'video{i}.mp4' for i in range(4)]
        for path in self.paths:
            path.write_bytes(b'test fixture')
        self.playlist = Playlist(random.Random(1))
        self.playlist.add(self.paths)
        self.playlist.select(0)

    def tearDown(self):
        self.directory.cleanup()

    def test_no_duplicates_or_nonvideos(self):
        bad = Path(self.directory.name) / 'document.txt'
        bad.write_text('not a video')
        self.assertEqual(self.playlist.add(self.paths + [bad]), [])
        self.assertEqual(len(self.playlist.items), 4)

    def test_sequential_end_and_repeat_all(self):
        self.playlist.select(3)
        self.assertIsNone(self.playlist.next(automatic=True))
        self.playlist.repeat = Repeat.ALL
        self.assertEqual(self.playlist.next(automatic=True), self.paths[0])

    def test_repeat_one_does_not_block_manual_next(self):
        self.playlist.repeat = Repeat.ONE
        self.assertEqual(self.playlist.next(automatic=True), self.paths[0])
        self.assertEqual(self.playlist.next(), self.paths[1])

    def test_shuffle_cycle_has_no_repeats_and_stops(self):
        self.playlist.set_shuffle(True)
        seen = [self.playlist.current]
        seen += [self.playlist.next(automatic=True) for _ in range(3)]
        self.assertEqual(set(seen), set(self.paths))
        self.assertIsNone(self.playlist.next(automatic=True))

    def test_shuffle_repeat_all_and_previous_history(self):
        self.playlist.set_shuffle(True)
        self.playlist.repeat = Repeat.ALL
        first = self.playlist.current
        self.playlist.next()
        self.assertEqual(self.playlist.previous(), first)
        self.playlist.reset_order()
        for _ in range(12):
            previous = self.playlist.current
            self.assertIsNotNone(self.playlist.next(automatic=True))
            self.assertNotEqual(self.playlist.current, previous)

    def test_toggle_shuffle_resets_completed_cycle(self):
        self.playlist.set_shuffle(True)
        for _ in range(3):
            self.playlist.next()
        self.playlist.set_shuffle(False)
        self.playlist.set_shuffle(True)
        self.assertIsNotNone(self.playlist.next())

    def test_remove_updates_index_and_keeps_files(self):
        self.playlist.select(2)
        self.playlist.remove(self.paths[0])
        self.assertEqual(self.playlist.current, self.paths[2])
        self.assertTrue(self.paths[0].exists())
        self.assertEqual(self.playlist.remove(self.paths[2]), 1)

    def test_random_video_can_revisit_and_repeat_icon_controls_cycles(self):
        self.playlist.set_order(PlaybackOrder.RANDOM_VIDEO)
        with __import__('unittest.mock', fromlist=['patch']).patch.object(self.playlist.rng, 'choice', side_effect=[1, 0, 1]):
            result = [self.playlist.next(automatic=True) for _ in range(3)]
        self.assertEqual(result, [self.paths[1], self.paths[0], self.paths[1]])
        self.assertIsNone(self.playlist.next(automatic=True))
        self.playlist.repeat = Repeat.ALL
        self.assertIsNotNone(self.playlist.next(automatic=True))
        self.playlist.repeat = Repeat.ONE
        current = self.playlist.current
        self.assertEqual(self.playlist.next(automatic=True), current)

    def test_order_change_never_changes_repeat(self):
        for repeat in Repeat:
            self.playlist.repeat = repeat
            for order in PlaybackOrder:
                self.playlist.set_order(order)
                self.assertEqual(self.playlist.repeat, repeat)


class LoopTests(unittest.TestCase):
    def test_marks_validation_and_clear(self):
        loop = ABLoop()
        self.assertFalse(loop.mark_b(1500))
        loop.mark_a(1000)
        self.assertFalse(loop.mark_b(999))
        self.assertFalse(loop.mark_b(1050))
        self.assertTrue(loop.mark_b(1100))
        self.assertTrue(loop.enabled)
        loop.mark_a(2000)
        self.assertIsNone(loop.b)
        loop.clear()
        self.assertFalse(loop.enabled)

    def test_timestamp(self):
        self.assertEqual(timestamp(-1), '00:00:00')
        self.assertEqual(timestamp(3661000), '01:01:01')


if __name__ == '__main__':
    unittest.main()
