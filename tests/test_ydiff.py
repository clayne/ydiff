#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for ydiff"""

import sys
import unittest
import tempfile
import subprocess
import os

sys.path.insert(0, '')
import ydiff  # nopep8


class SplitToWordsTest(unittest.TestCase):

    def test_ok(self):
        tests = [
            # (input, want)
            ('HELLO_WORLD = 0', ['HELLO', '_', 'WORLD', ' ', '=', ' ', '0']),
            ('class HelloWorld\n', ['class', ' ', 'Hello', 'World', '\n']),
            ('int foo3\n', ['int', ' ', 'foo', '3', '\n']),
            ('int f3\n', ['int', ' ', 'f3', '\n']),
            ('a.addOption', ['a', '.', 'add', 'Option']),
            ('a.AddOption', ['a', '.', 'Add', 'Option']),
            ('class HelloW0rld\n', ['class', ' ', 'Hello', 'W0rld', '\n']),
            ('hello_w0rld++\n', ['hello', '_', 'w0rld', '+', '+', '\n']),
            ('var foo []string', ['var', ' ', 'foo', ' ', '[', ']', 'string']),
            ('i -= 1\n', ['i', ' ', '-', '=', ' ', '1', '\n']),
        ]
        for s, want in tests:
            got = ydiff._split_to_words(s)
            self.assertEqual(want, got)


class StrSplitTest(unittest.TestCase):

    def test_not_colorized(self):
        text = 'Hi, 你好\n'
        tests = [
            # (width, want)
            (4, ('Hi, ', '你好\n', 4)),
            (5, ('Hi, 你', '好\n', 6)),
            (8, ('Hi, 你好', '\n', 8)),
            (9, ('Hi, 你好\n', '', 9)),
            (10, ('Hi, 你好\n', '', 9)),
        ]
        for width, want in tests:
            got = ydiff._strsplit(text, width, {})
            self.assertEqual(want, got)

    def test_colorized(self):
        g = '\x1b[32m'  # green
        b = '\x1b[34m'  # blue
        r = '\x1b[0m'   # reset
        # Width:     1----2----------3-----[4]5--[6]7
        parts = [g, 'H', 'i', r, b, '!', r, '你', '好']
        codes = {g, b, r}
        tests = [
            # (width, want_left, want_right, want_width)
            (1, (g, 'H', r), (g, 'i', r, b, '!', r, '你好'), 1),
            (2, (g, 'Hi', r, b, r), (b, '!', r, '你好'), 2),
            (3, (g, 'Hi', r, b, '!', r), ('你好'), 3),
            (4, (g, 'Hi', r, b, '!', r, '你'), ('好',), 5),
            (5, (g, 'Hi', r, b, '!', r, '你'), ('好',), 5),
            (6, (g, 'Hi', r, b, '!', r, '你好'), (), 7),
            (7, (g, 'Hi', r, b, '!', r, '你好'), (), 7),
            (8, (g, 'Hi', r, b, '!', r, '你好'), (), 7),
        ]
        for width, want_left, want_right, want_width in tests:
            got = ydiff._strsplit(''.join(parts), width, codes)
            self.assertEqual(''.join(want_left), got[0])
            self.assertEqual(''.join(want_right), got[1])
            self.assertEqual(want_width, got[2])


class StrTrimTest(unittest.TestCase):

    def test_not_colorized(self):
        text = 'Hi, 你好\n'
        tests = [
            # (width, want)
            (4, ('Hi, ', '你好\n', 4)),
            (5, ('Hi, 你', '好\n', 6)),
            (8, ('Hi, 你好', '\n', 8)),
            (9, ('Hi, 你好\n', '', 9)),
            (10, ('Hi, 你好\n', '', 9)),
        ]
        for width, want in tests:
            got = ydiff._strsplit(text, width, {})
            self.assertEqual(want, got)

    def test_colorized(self):
        g = '\x1b[32m'  # green
        b = '\x1b[34m'  # blue
        r = '\x1b[0m'   # reset
        # Width:     1----2----------3-----[4]5--[6]7
        parts = [g, 'H', 'i', r, b, '!', r, '你', '好']
        codes = {g, b, r}
        tests = [
            # (width, pad, want)
            (1, False, (g, r, '>')),
            (2, False, (g, 'H', r, '>')),
            (3, False, (g, 'Hi', r, b, r, '>')),
            (4, False, (g, 'Hi', r, b, '!', r, '>')),
            (5, False, (g, 'Hi', r, b, '!', r, '你>')),
            (6, False, (g, 'Hi', r, b, '!', r, '你>')),
            (7, False, (g, 'Hi', r, b, '!', r, '你好')),
            (8, False, (g, 'Hi', r, b, '!', r, '你好')),
            (8, True, (g, 'Hi', r, b, '!', r, '你好 ')),
        ]
        for width, pad, want in tests:
            got = ydiff._strtrim(''.join(parts), width, '>', pad, codes)
            self.assertEqual(''.join(want), got, 'width %d failed' % width)


class DecodeTest(unittest.TestCase):

    def test_normal(self):
        octets = b'\xe4\xbd\xa0\xe5\xa5\xbd'
        want = '你好'
        self.assertEqual(ydiff._decode(octets), want)

    def test_latin_1(self):
        octets = b'\x80\x02q\x01(U'
        want = '\x80\x02q\x01(U'
        self.assertEqual(ydiff._decode(octets), want)


class HunkTest(unittest.TestCase):

    def test_get_old_text(self):
        hunk = ydiff.Hunk([], '@@ -1,2 +1,2 @@', (1, 2), (1, 2))
        hunk.append(('-', 'foo\n'))
        hunk.append(('+', 'bar\n'))
        hunk.append((' ', 'common\n'))
        self.assertEqual(hunk._get_old_text(), ['foo\n', 'common\n'])

    def test_get_new_text(self):
        hunk = ydiff.Hunk([], '@@ -1,2 +1,2 @@', (1, 2), (1, 2))
        hunk.append(('-', 'foo\n'))
        hunk.append(('+', 'bar\n'))
        hunk.append((' ', 'common\n'))
        self.assertEqual(hunk._get_new_text(), ['bar\n', 'common\n'])


class DiffMarkupTest(unittest.TestCase):

    def _init_diff(self):
        """Return a minimal diff contains all required samples
            header
            --- old
            +++ new
            hunk header
            @@ -1,5 +1,5 @@
            -_hello
            +hello+
            +spammm
             world
            -garb
            -Again
            -	tabbed
            +again
            + spaced
        """

        hunk = ydiff.Hunk(['hunk header\n'], '@@ -1,5 +1,5 @@\n',
                          (1, 5), (1, 5))
        hunk.append(('-', '_hello\n'))
        hunk.append(('+', 'hello+\n'))
        hunk.append(('+', 'spammm\n'))
        hunk.append((' ', 'world\n'))
        hunk.append(('-', 'garb\n'))
        hunk.append(('-', 'Again\n'))
        hunk.append(('-', '\ttabbed\n'))
        hunk.append(('+', 'again\n'))
        hunk.append(('+', ' spaced\n'))
        diff = ydiff.UnifiedDiff(
            ['header\n'], '--- old\n', '+++ new\n', [hunk])
        return diff

    def test_markup_traditional_hunk_header(self):
        hunk = ydiff.Hunk(['hunk header\n'], '@@ -0 +0 @@\n', (0, 0), (0, 0))
        diff = ydiff.UnifiedDiff([], '--- old\n', '+++ new\n', [hunk])
        marker = ydiff.DiffMarker()

        out = list(marker.markup(diff))
        self.assertEqual(len(out), 4)

        self.assertEqual(out[0], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[36mhunk header\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[34m@@ -0 +0 @@\n\x1b[0m')

    def test_markup_traditional_old_changed(self):
        hunk = ydiff.Hunk([], '@@ -1 +0,0 @@\n', (1, 0), (0, 0))
        hunk.append(('-', 'spam\n'))
        diff = ydiff.UnifiedDiff([], '--- old\n', '+++ new\n', [hunk])
        marker = ydiff.DiffMarker()

        out = list(marker.markup(diff))
        self.assertEqual(len(out), 4)

        self.assertEqual(out[0], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[34m@@ -1 +0,0 @@\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[31m-spam\n\x1b[0m')

    def test_markup_traditional_new_changed(self):
        hunk = ydiff.Hunk([], '@@ -0,0 +1 @@\n', (0, 0), (1, 0))
        hunk.append(('+', 'spam\n'))
        diff = ydiff.UnifiedDiff([], '--- old\n', '+++ new\n', [hunk])
        marker = ydiff.DiffMarker()

        out = list(marker.markup(diff))
        self.assertEqual(len(out), 4)

        self.assertEqual(out[0], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[34m@@ -0,0 +1 @@\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[32m+spam\n\x1b[0m')

    def test_markup_traditional_both_changed(self):
        hunk = ydiff.Hunk([], '@@ -1,2 +1,2 @@\n', (1, 2), (1, 2))
        hunk.append(('-', 'hell-\n'))
        hunk.append(('+', 'hell+\n'))
        hunk.append((' ', 'common\n'))
        diff = ydiff.UnifiedDiff([], '--- old\n', '+++ new\n', [hunk])
        marker = ydiff.DiffMarker()

        out = list(marker.markup(diff))
        self.assertEqual(len(out), 6)

        self.assertEqual(out[0], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[34m@@ -1,2 +1,2 @@\n\x1b[0m')
        self.assertEqual(
            out[3],
            '\x1b[31m-\x1b[0m\x1b[31mhell'
            '\x1b[7m\x1b[31m-\x1b[0m\x1b[31m\n\x1b[0m')
        self.assertEqual(
            out[4],
            '\x1b[32m+\x1b[0m\x1b[32mhell'
            '\x1b[7m\x1b[32m+\x1b[0m\x1b[32m\n\x1b[0m')
        self.assertEqual(out[5], '\x1b[0m common\n\x1b[0m')

    def test_markup_side_by_side_padded(self):
        diff = self._init_diff()
        marker = ydiff.DiffMarker(side_by_side=True, width=7)

        out = list(marker.markup(diff))
        self.assertEqual(len(out), 11)

        sys.stdout.write('\n')
        for markup in out:
            sys.stdout.write(markup)

        self.assertEqual(out[0], '\x1b[36mheader\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[36mhunk header\n\x1b[0m')
        self.assertEqual(out[4], '\x1b[34m@@ -1,5 +1,5 @@\n\x1b[0m')
        self.assertEqual(
            out[5],
            '\x1b[33m1\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31m_\x1b[0m\x1b[31mhello\x1b[0m  '
            '\x1b[0m\x1b[33m1\x1b[0m '
            '\x1b[32mhello\x1b[7m\x1b[32m+\x1b[0m\x1b[32m\x1b[0m\n')
        self.assertEqual(
            out[6],
            '\x1b[33m '
            '\x1b[0m         '
            '\x1b[0m\x1b[33m2\x1b[0m '
            '\x1b[32mspammm\x1b[0m\n')
        self.assertEqual(
            out[7],
            '\x1b[33m2\x1b[0m '
            '\x1b[0mworld\x1b[0m   '
            '\x1b[0m\x1b[33m3\x1b[0m '
            '\x1b[0mworld\x1b[0m\n')
        self.assertEqual(
            out[8],
            '\x1b[33m3\x1b[0m '
            '\x1b[31mgarb\x1b[0m '
            '\x1b[0m\x1b[33m '
            '\x1b[0m \n')
        self.assertEqual(
            out[9],
            '\x1b[33m4\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31mAgain\x1b[0m\x1b[31m\x1b[0m   '
            '\x1b[0m\x1b[33m4\x1b[0m '
            '\x1b[32m\x1b[7m\x1b[32magain\x1b[0m\x1b[32m\x1b[0m\n')
        self.assertEqual(
            out[10],
            '\x1b[33m5\x1b[0m '
            '\x1b[31m \x1b[7m\x1b[31m     \x1b[0m\x1b[95m>\x1b[0m '
            '\x1b[0m\x1b[33m5\x1b[0m '
            '\x1b[32m \x1b[7m\x1b[32mspaced\x1b[0m\x1b[32m\x1b[0m\n')

    # This test is not valid anymore
    def __test_markup_side_by_side_neg_width(self):
        diff = self._init_diff()
        marker = ydiff.DiffMarker(side_by_side=True, width=-1)
        out = list(marker.markup(diff))
        self.assertEqual(len(out), 11)

        self.assertEqual(out[0], '\x1b[36mheader\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[36mhunk header\n\x1b[0m')
        self.assertEqual(out[4], '\x1b[34m@@ -1,4 +1,4 @@\n\x1b[0m')
        self.assertEqual(
            out[5],
            '\x1b[33m1\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31mh\x1b[0m\x1b[31mhello\x1b[0m ' +
            (' ' * 74) +
            '\x1b[0m\x1b[33m1\x1b[0m '
            '\x1b[32mhello\x1b[7m\x1b[32mo\x1b[0m\x1b[32m\x1b[0m\n')
        self.assertEqual(
            out[6],
            '\x1b[33m '
            '\x1b[0m  ' + (' ' * 80) +
            '\x1b[0m\x1b[33m2\x1b[0m '
            '\x1b[32mspammm\x1b[0m\n')
        self.assertEqual(
            out[7],
            '\x1b[33m2\x1b[0m '
            '\x1b[0mworld\x1b[0m ' + (' ' * 75) +
            '\x1b[0m\x1b[33m3\x1b[0m '
            '\x1b[0mworld\x1b[0m\n')
        self.assertEqual(
            out[8],
            '\x1b[33m3\x1b[0m '
            '\x1b[31mgarb\x1b[0m '
            '\x1b[0m\x1b[33m '
            '\x1b[0m \n')
        self.assertEqual(
            out[9],
            '\x1b[33m4\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31mAgain\x1b[0m ' +
            (' ' * 75) +
            '\x1b[0m\x1b[33m4\x1b[0m '
            '\x1b[32m\x1b[7m\x1b[32magain\x1b[0m\n')

    def test_markup_side_by_side_off_by_one(self):
        diff = self._init_diff()
        marker = ydiff.DiffMarker(side_by_side=True, width=6)
        out = list(marker.markup(diff))
        self.assertEqual(len(out), 11)

        sys.stdout.write('\n')
        for markup in out:
            sys.stdout.write(markup)

        self.assertEqual(out[0], '\x1b[36mheader\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[36mhunk header\n\x1b[0m')
        self.assertEqual(out[4], '\x1b[34m@@ -1,5 +1,5 @@\n\x1b[0m')
        self.assertEqual(
            out[5],
            '\x1b[33m1\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31m_\x1b[0m\x1b[31mhello\x1b[0m '
            '\x1b[0m\x1b[33m1\x1b[0m '
            '\x1b[32mhello\x1b[7m\x1b[32m+\x1b[0m\x1b[32m\x1b[0m\n')
        self.assertEqual(
            out[6],
            '\x1b[33m \x1b[0m        '
            '\x1b[0m\x1b[33m2\x1b[0m '
            '\x1b[32mspammm\x1b[0m\n')
        self.assertEqual(
            out[7],
            '\x1b[33m2\x1b[0m '
            '\x1b[0mworld\x1b[0m  '
            '\x1b[0m\x1b[33m3\x1b[0m '
            '\x1b[0mworld\x1b[0m\n')
        self.assertEqual(
            out[8],
            '\x1b[33m3\x1b[0m '
            '\x1b[31mgarb\x1b[0m '
            '\x1b[0m\x1b[33m '
            '\x1b[0m \n')
        self.assertEqual(
            out[9],
            '\x1b[33m4\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31mAgain\x1b[0m\x1b[31m\x1b[0m  '
            '\x1b[0m\x1b[33m4\x1b[0m '
            '\x1b[32m\x1b[7m\x1b[32magain\x1b[0m\x1b[32m\x1b[0m\n')
        self.assertEqual(
            out[10],
            '\x1b[33m5\x1b[0m '
            '\x1b[31m \x1b[7m\x1b[31m    \x1b[0m\x1b[95m>\x1b[0m '
            '\x1b[0m\x1b[33m5\x1b[0m '
            '\x1b[32m \x1b[7m\x1b[32mspac\x1b[0m\x1b[95m>\x1b[0m\n')

    def test_markup_side_by_side_wrapped(self):
        diff = self._init_diff()
        marker = ydiff.DiffMarker(side_by_side=True, width=5)
        out = list(marker.markup(diff))
        self.assertEqual(len(out), 11)

        sys.stdout.write('\n')
        for markup in out:
            sys.stdout.write(markup)

        self.assertEqual(out[0], '\x1b[36mheader\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[36mhunk header\n\x1b[0m')
        self.assertEqual(out[4], '\x1b[34m@@ -1,5 +1,5 @@\n\x1b[0m')
        self.assertEqual(
            out[5],
            '\x1b[33m1\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31m_\x1b[0m\x1b[31mhel\x1b[0m\x1b[95m>\x1b[0m '  # nopep8
            '\x1b[0m\x1b[33m1\x1b[0m '
            '\x1b[32mhell\x1b[0m\x1b[95m>\x1b[0m\n')
        self.assertEqual(
            out[6],
            '\x1b[33m \x1b[0m       '
            '\x1b[0m\x1b[33m2\x1b[0m '
            ''
            '\x1b[32mspam\x1b[0m\x1b[95m>\x1b[0m\n')
        self.assertEqual(
            out[7],
            '\x1b[33m2\x1b[0m '
            '\x1b[0mworld\x1b[0m '
            '\x1b[0m\x1b[33m3\x1b[0m '
            '\x1b[0mworld\x1b[0m\n')
        self.assertEqual(
            out[8],
            '\x1b[33m3\x1b[0m '
            '\x1b[31mgarb\x1b[0m '
            '\x1b[0m\x1b[33m '
            '\x1b[0m \n')
        self.assertEqual(
            out[9],
            '\x1b[33m4\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31mAgain\x1b[0m\x1b[31m\x1b[0m '
            '\x1b[0m\x1b[33m4\x1b[0m '
            '\x1b[32m\x1b[7m\x1b[32magain\x1b[0m\x1b[32m\x1b[0m\n')
        self.assertEqual(
            out[10],
            '\x1b[33m5\x1b[0m '
            '\x1b[31m \x1b[7m\x1b[31m   \x1b[0m\x1b[95m>\x1b[0m '
            '\x1b[0m\x1b[33m5\x1b[0m '
            '\x1b[32m \x1b[7m\x1b[32mspa\x1b[0m\x1b[95m>\x1b[0m\n')

    def test_markup_side_by_side_tabbed(self):
        diff = self._init_diff()
        marker = ydiff.DiffMarker(side_by_side=True, width=8, tab_width=2)
        out = list(marker.markup(diff))
        self.assertEqual(len(out), 11)

        sys.stdout.write('\n')
        for markup in out:
            sys.stdout.write(markup)

        self.assertEqual(out[0], '\x1b[36mheader\n\x1b[0m')
        self.assertEqual(out[1], '\x1b[33m--- old\n\x1b[0m')
        self.assertEqual(out[2], '\x1b[33m+++ new\n\x1b[0m')
        self.assertEqual(out[3], '\x1b[36mhunk header\n\x1b[0m')
        self.assertEqual(out[4], '\x1b[34m@@ -1,5 +1,5 @@\n\x1b[0m')
        self.assertEqual(
            out[5],
            '\x1b[33m1\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31m_\x1b[0m\x1b[31mhello\x1b[0m   '
            '\x1b[0m\x1b[33m1\x1b[0m '
            '\x1b[32mhello\x1b[7m\x1b[32m+\x1b[0m\x1b[32m\x1b[0m\n')
        self.assertEqual(
            out[6],
            '\x1b[33m '
            '\x1b[0m          '
            '\x1b[0m\x1b[33m2\x1b[0m '
            '\x1b[32mspammm\x1b[0m\n')
        self.assertEqual(
            out[7],
            '\x1b[33m2\x1b[0m '
            '\x1b[0mworld\x1b[0m    '
            '\x1b[0m\x1b[33m3\x1b[0m '
            '\x1b[0mworld\x1b[0m\n')
        self.assertEqual(
            out[8],
            '\x1b[33m3\x1b[0m '
            '\x1b[31mgarb\x1b[0m '
            '\x1b[0m\x1b[33m '
            '\x1b[0m \n')
        self.assertEqual(
            out[9],
            '\x1b[33m4\x1b[0m '
            '\x1b[31m\x1b[7m\x1b[31mAgain\x1b[0m\x1b[31m\x1b[0m    '
            '\x1b[0m\x1b[33m4\x1b[0m '
            '\x1b[32m\x1b[7m\x1b[32magain\x1b[0m\x1b[32m\x1b[0m\n')
        self.assertEqual(
            out[10],
            '\x1b[33m5\x1b[0m '
            '\x1b[31m \x1b[7m\x1b[31m tabbed\x1b[0m\x1b[31m\x1b[0m '
            '\x1b[0m\x1b[33m5\x1b[0m '
            '\x1b[32m \x1b[7m\x1b[32mspaced\x1b[0m\x1b[32m\x1b[0m\n')


class UnifiedDiffTest(unittest.TestCase):

    diff = ydiff.UnifiedDiff(None, None, None, None)

    def test_is_hunk_meta_normal(self):
        self.assertTrue(self.diff.is_hunk_meta('@@ -1 +1 @@'))
        self.assertTrue(self.diff.is_hunk_meta('@@ -3,7 +3,6 @@'))
        self.assertTrue(self.diff.is_hunk_meta('@@ -3,7 +3,6 @@ class Foo'))
        self.assertTrue(self.diff.is_hunk_meta('@@ -3,7 +3,6 @@ class Foo\n'))
        self.assertTrue(
            self.diff.is_hunk_meta('@@ -3,7 +3,6 @@ class Foo\r\n'))

    def test_is_hunk_meta_svn_prop(self):
        self.assertTrue(self.diff.is_hunk_meta('## -0,0 +1 ##'))
        self.assertTrue(self.diff.is_hunk_meta('## -0,0 +1 ##\n'))
        self.assertTrue(self.diff.is_hunk_meta('## -0,0 +1 ##\r\n'))

    def test_is_hunk_meta_neg(self):
        self.assertFalse(self.diff.is_hunk_meta('@@ -1 + @@'))
        self.assertFalse(self.diff.is_hunk_meta('@@ -this is not a hunk meta'))
        self.assertFalse(self.diff.is_hunk_meta('## -this is not either'))

    def test_parse_hunk_meta_normal(self):
        self.assertEqual(self.diff.parse_hunk_meta('@@ -3,7 +3,6 @@'),
                         ((3, 7), (3, 6)))

    def test_parse_hunk_meta_missing(self):
        self.assertEqual(self.diff.parse_hunk_meta('@@ -3 +3,6 @@'),
                         ((3, 1), (3, 6)))
        self.assertEqual(self.diff.parse_hunk_meta('@@ -3,7 +3 @@'),
                         ((3, 7), (3, 1)))
        self.assertEqual(self.diff.parse_hunk_meta('@@ -3 +3 @@'),
                         ((3, 1), (3, 1)))

    def test_parse_hunk_meta_svn_prop(self):
        self.assertEqual(self.diff.parse_hunk_meta('## -0,0 +1 ##'),
                         ((0, 0), (1, 1)))

    def test_is_old(self):
        self.assertTrue(self.diff.is_old('-hello world'))
        self.assertTrue(self.diff.is_old('----'))            # yaml

    def test_is_old_neg(self):
        self.assertFalse(self.diff.is_old('--- considered as old path'))
        self.assertFalse(self.diff.is_old('-' * 72))         # svn log --diff

    def test_is_new(self):
        self.assertTrue(self.diff.is_new('+hello world'))
        self.assertTrue(self.diff.is_new('++++hello world'))

    def test_is_new_neg(self):
        self.assertFalse(self.diff.is_new('+++ considered as new path'))


class DiffParserTest(unittest.TestCase):

    def test_parse_invalid_hunk_meta(self):
        patch = b"""\
spam
--- a
+++ b
spam
@@ -a,a +0 @@
"""
        items = patch.splitlines(True)
        stream = iter(items)
        parser = ydiff.DiffParser(stream)
        self.assertRaises(RuntimeError, list, parser.parse())

    def test_parse_dangling_header(self):
        patch = b"""\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
spam
"""
        items = patch.splitlines(True)
        stream = iter(items)
        parser = ydiff.DiffParser(stream)

        out = list(parser.parse())
        self.assertEqual(len(out), 2)
        self.assertEqual(len(out[1]._headers), 1)
        self.assertEqual(out[1]._headers[0], 'spam\n')
        self.assertEqual(out[1]._old_path, '')
        self.assertEqual(out[1]._new_path, '')
        self.assertEqual(len(out[1]._hunks), 0)

    def test_parse_missing_new_path(self):
        patch = b"""\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
--- c
"""
        items = patch.splitlines(True)
        stream = iter(items)
        parser = ydiff.DiffParser(stream)
        self.assertRaises(AssertionError, list, parser.parse())

    def test_parse_missing_hunk_meta(self):
        patch = b"""\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
--- c
+++ d
"""
        items = patch.splitlines(True)
        stream = iter(items)
        parser = ydiff.DiffParser(stream)

        out = list(parser.parse())
        self.assertEqual(len(out), 2)
        self.assertEqual(len(out[1]._headers), 0)
        self.assertEqual(out[1]._old_path, '--- c\n')
        self.assertEqual(out[1]._new_path, '+++ d\n')
        self.assertEqual(len(out[1]._hunks), 0)

    def test_parse_missing_hunk_list(self):
        patch = b"""\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
--- c
+++ d
@@ -1,2 +1,2 @@
"""
        items = patch.splitlines(True)
        stream = iter(items)
        parser = ydiff.DiffParser(stream)
        self.assertRaises(AssertionError, list, parser.parse())

    def test_parse_only_in_dir(self):
        patch = b"""\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
Only in foo: foo
--- c
+++ d
@@ -1,2 +1,2 @@
-foo
+bar
 common
"""
        items = patch.splitlines(True)
        stream = iter(items)
        parser = ydiff.DiffParser(stream)

        out = list(parser.parse())
        self.assertEqual(len(out), 3)
        self.assertEqual(len(out[1]._hunks), 0)
        self.assertEqual(out[1]._headers, ['Only in foo: foo\n'])
        self.assertEqual(len(out[2]._hunks), 1)
        self.assertEqual(len(out[2]._hunks[0]._hunk_list), 3)

    def test_parse_only_in_dir_at_last(self):
        patch = b"""\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
Only in foo: foo
"""
        items = patch.splitlines(True)
        stream = iter(items)
        parser = ydiff.DiffParser(stream)

        out = list(parser.parse())
        self.assertEqual(len(out), 2)
        self.assertEqual(len(out[1]._hunks), 0)
        self.assertEqual(out[1]._headers, ['Only in foo: foo\n'])

    def test_parse_binary_differ_diff_ru(self):
        patch = b"""\
--- a
+++ b
@@ -1,2 +1,2 @@
-foo
+bar
 common
Binary files a/1.pdf and b/1.pdf differ
--- c
+++ d
@@ -1,2 +1,2 @@
-foo
+bar
 common
"""
        items = patch.splitlines(True)
        stream = iter(items)
        parser = ydiff.DiffParser(stream)

        out = list(parser.parse())
        self.assertEqual(len(out), 3)
        self.assertEqual(len(out[1]._hunks), 0)
        self.assertEqual(out[1]._old_path, '')
        self.assertEqual(out[1]._new_path, '')
        self.assertEqual(len(out[1]._headers), 1)
        self.assertTrue(out[1]._headers[0].startswith('Binary files'))
        self.assertEqual(len(out[2]._hunks), 1)
        self.assertEqual(len(out[2]._hunks[0]._hunk_list), 3)

    def test_parse_binary_differ_git(self):
        patch = b"""\
diff --git a/foo b/foo
index 529d8a3..ad71911 100755
--- a/foo
+++ b/foo
@@ -1,2 +1,2 @@
-foo
+bar
 common
diff --git a/example.pdf b/example.pdf
index 1eacfd8..3696851 100644
Binary files a/example.pdf and b/example.pdf differ
diff --git a/bar b/bar
index 529e8a3..ad71921 100755
--- a/bar
+++ b/bar
@@ -1,2 +1,2 @@
-foo
+bar
 common
"""
        items = patch.splitlines(True)
        stream = iter(items)
        parser = ydiff.DiffParser(stream)

        out = list(parser.parse())
        self.assertEqual(len(out), 3)
        self.assertEqual(len(out[1]._hunks), 0)
        self.assertEqual(out[1]._old_path, '')
        self.assertEqual(out[1]._new_path, '')
        self.assertEqual(len(out[1]._headers), 3)
        self.assertTrue(out[1]._headers[2].startswith('Binary files'))
        self.assertEqual(len(out[2]._hunks), 1)
        self.assertEqual(len(out[2]._hunks[0]._hunk_list), 3)

    def test_parse_svn_prop(self):
        patch = b"""\
--- a
+++ b
Added: svn:executable
## -0,0 +1 ##
+*
\\ No newline at end of property
Added: svn:keywords
## -0,0 +1 ##
+Id
"""
        items = patch.splitlines(True)
        stream = iter(items)
        parser = ydiff.DiffParser(stream)
        out = list(parser.parse())
        self.assertEqual(len(out), 1)
        self.assertEqual(len(out[0]._hunks), 2)

        hunk = out[0]._hunks[1]
        self.assertEqual(hunk._hunk_headers, ['Added: svn:keywords\n'])
        self.assertEqual(hunk._hunk_list, [('+', 'Id\n')])


@unittest.skipIf(os.name == 'nt', 'Travis CI Windows not ready for shell cmds')
class MainTest(unittest.TestCase):

    def setUp(self):
        self._cwd = os.getcwd()
        self._ws = tempfile.mkdtemp(prefix='test_ydiff')
        self._non_ws = tempfile.mkdtemp(prefix='test_ydiff')
        cmd = ('set -o errexit; cd %s; git init; git config user.name me; '
               'git config user.email me@example.org') % self._ws
        subprocess.call(cmd, shell=True, stdout=subprocess.PIPE)
        self._change_file('init')

    def tearDown(self):
        os.chdir(self._cwd)
        cmd = ['/bin/rm', '-rf', self._ws, self._non_ws]
        subprocess.call(cmd)

    def _change_file(self, text):
        cmd = ['/bin/sh', '-ec',
               'cd %s; echo "%s" > foo' % (self._ws, text)]
        subprocess.call(cmd)

    def _commit_file(self):
        cmd = ['/bin/sh', '-ec',
               'cd %s; git add foo; git commit foo -m update' % self._ws]
        subprocess.call(cmd, stdout=subprocess.PIPE)

    def test_preset_options(self):
        os.environ['YDIFF_OPTIONS'] = '--help'
        self.assertRaises(SystemExit, ydiff._main)
        os.environ.pop('YDIFF_OPTIONS', None)

    def test_read_diff(self):
        sys.argv = sys.argv[:1]
        self._change_file('read_diff')

        os.chdir(self._ws)
        ret = ydiff._main()
        os.chdir(self._cwd)
        self.assertEqual(ret, 0)

    # Following 3 tests does not pass on Travis anymore due to tty problem

    def _test_read_log(self):
        sys.argv = [sys.argv[0], '--log']
        self._change_file('read_log')
        self._commit_file()

        os.chdir(self._ws)
        ret = ydiff._main()
        os.chdir(self._cwd)
        self.assertEqual(ret, 0)

    def _test_read_diff_neg(self):
        sys.argv = sys.argv[:1]
        os.chdir(self._non_ws)
        ret = ydiff._main()
        os.chdir(self._cwd)
        self.assertNotEqual(ret, 0)

    def _test_read_log_neg(self):
        sys.argv = [sys.argv[0], '--log']
        os.chdir(self._non_ws)
        ret = ydiff._main()
        os.chdir(self._cwd)
        self.assertNotEqual(ret, 0)


if __name__ == '__main__':
    unittest.main()

# vim:set et sts=4 sw=4 tw=80:
