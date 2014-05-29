# -*- coding: utf-8 -*-
""" formatting.py - handy functions for formatting text
    this file contains code from the following URL:
    <http://code.djangoproject.com/svn/django/trunk/django/utils/text.py>
"""

import re

from html.parser import HTMLParser
import html.entities


from enum import Enum

class Color(Enum):
    default = 'default'

    black = 'black'
    blue = 'blue'
    cyan = 'cyan'
    green = 'green'
    purple = 'purple'
    red = 'red'
    white = 'white'
    yellow = 'yellow'

    def to_style(self):
        return Style(fg=self)

    def __call__(self, *chunks):
        return FormattedString(*chunks, fg=self)


class Bold(Enum):
    off = False
    on = True

    def to_style(self):
        return Style(bold=self)

    def __call__(self, *chunks):
        return FormattedString(*chunks, bold=self)

FOREGROUND_CODES = {
    Color.white: '\x0300',
    Color.black: '\x0301',
    Color.blue: '\x0302',
    Color.green: '\x0303',
    Color.red: '\x0304',
    Color.yellow: '\x0305',
    Color.purple: '\x0306',
    Color.cyan: '\x0310',
}

BOLD_CODES = {
    Bold.on: '\x02',
    Bold.off: '\x02',
}


def format_transition(current_style, new_style):
    if new_style == Style.default():
        # Just use the reset sequence
        return '\x1b[0m'

    ret = ''
    if new_style.fg != current_style.fg:
        ret += FOREGROUND_CODES[new_style.fg]

    if new_style.bold != current_style.bold:
        ret += BOLD_CODES[new_style.bold]

    return ret


class Style:
    __slots__ = ('fg', 'bg', 'bold', 'inverse')

    def __init__(self, *, fg=None, bg=None, bold=None, inverse=None):
        # XXX clarify that `None` means "inherit", versus meaning the default
        self.fg = fg
        self.bg = bg
        self.bold = bold
        self.inverse = inverse

    @classmethod
    def default(cls):
        return cls(
            fg=Color.default,
            bold=Bold.off,
        )

    def __repr__(self):
        return "<{}{}>".format(
            type(self).__qualname__,
            repr(self.to_kwargs()),
        )

    def __eq__(self, other):
        if not isinstance(other, Style):
            return NotImplemented

        return self.to_kwargs() == other.to_kwargs()

    def __ne__(self, other):
        return not (self == other)

    def with_(self, *other_styles, **override_kwargs):
        kwargs = self.to_kwargs()

        # TODO i don't like having to skip Nones here...
        for style in other_styles:
            for k, v in style.to_kwargs().items():
                if v is not None:
                    kwargs[k] = v

        for k, v in override_kwargs.items():
            if v is not None:
                kwargs[k] = v

        return type(self)(**kwargs)

    def to_kwargs(self):
        return {
            key: getattr(self, key)
            for key in self.__slots__
        }


class FormattedString():
    def __init__(self, *chunks, **styles):
        self.chunks = []
        current_style = Style(**styles)
        for chunk in chunks:
            if isinstance(chunk, FormattedString):
                for subchunk, style in chunk.chunks:
                    self.chunks.append((subchunk, current_style.with_(style)))
            elif isinstance(chunk, Color):
                current_style = current_style.with_(chunk.to_style())
            elif isinstance(chunk, Style):
                current_style = current_style.with_(chunk)
            else:
                self.chunks.append((chunk, current_style))

    @classmethod
    def parse(cls, string, formats):
        raise NotImplementedError

    def __add__(self, other):
        return type(self)(self, other)

    def render(self):
        buf = []
        current_style = Style.default()
        for chunk, style in self.chunks + [('', Style.default())]:
            style = Style.default().with_(style)
            if current_style != style:
                buf.append(format_transition(current_style, style))
            buf.append(chunk)
            current_style = style

        buf.append(format_transition(current_style, Style.default()))

        return ''.join(buf)


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.result = []

    def handle_data(self, d):
        self.result.append(d)

    def handle_charref(self, number):
        codepoint = int(number[1:], 16) if number[0] in ('x', 'X') else int(number)
        self.result.append(chr(codepoint))

    def handle_entityref(self, name):
        codepoint = html.entities.name2codepoint[name]
        self.result.append(chr(codepoint))

    def get_text(self):
        return ''.join(self.result)


def strip_html(html):
    s = HTMLTextExtractor()
    s.feed(html)
    return s.get_text()


def munge(text, munge_count=0):
    """munges up text."""
    reps = 0
    for n in range(len(text)):
        rep = character_replacements.get(text[n])
        if rep:
            text = text[:n] + rep + text[n + 1:]
            reps += 1
            if reps == munge_count:
                break
    return text


character_replacements = {
    'a': 'ä',
    'b': 'Б',
    'c': 'ċ',
    'd': 'đ',
    'e': 'ë',
    'f': 'ƒ',
    'g': 'ġ',
    'h': 'ħ',
    'i': 'í',
    'j': 'ĵ',
    'k': 'ķ',
    'l': 'ĺ',
    'm': 'ṁ',
    'n': 'ñ',
    'o': 'ö',
    'p': 'ρ',
    'q': 'ʠ',
    'r': 'ŗ',
    's': 'š',
    't': 'ţ',
    'u': 'ü',
    'v': '',
    'w': 'ω',
    'x': 'χ',
    'y': 'ÿ',
    'z': 'ź',
    'A': 'Å',
    'B': 'Β',
    'C': 'Ç',
    'D': 'Ď',
    'E': 'Ē',
    'F': 'Ḟ',
    'G': 'Ġ',
    'H': 'Ħ',
    'I': 'Í',
    'J': 'Ĵ',
    'K': 'Ķ',
    'L': 'Ĺ',
    'M': 'Μ',
    'N': 'Ν',
    'O': 'Ö',
    'P': 'Р',
    'Q': 'Ｑ',
    'R': 'Ŗ',
    'S': 'Š',
    'T': 'Ţ',
    'U': 'Ů',
    'V': 'Ṿ',
    'W': 'Ŵ',
    'X': 'Χ',
    'Y': 'Ỳ',
    'Z': 'Ż'
}


def capitalize_first(line):
    """
    capitalises the first letter of words
    (keeps other letters intact)
    """
    return ' '.join([s[0].upper() + s[1:] for s in line.split(' ')])


# TODO: rewrite to use a list of tuples
def multiword_replace(text, word_dic):
    """
    take a text and replace words that match a key in a dictionary with
    the associated value, return the changed text
    """
    rc = re.compile('|'.join(map(re.escape, word_dic)))

    def translate(match):
        return word_dic[match.group(0)]

    return rc.sub(translate, text)


def truncate_words(content, length=10, suffix='...'):
    """Truncates a string after a certain number of words."""
    nmsg = content.split(" ")
    out = None
    x = 0
    for i in nmsg:
        if x <= length:
            if out:
                out = out + " " + nmsg[x]
            else:
                out = nmsg[x]
        x += 1
    if x <= length:
        return out
    else:
        return out + suffix


# from <http://stackoverflow.com/questions/250357/smart-truncate-in-python>
def truncate_str(content, length=100, suffix='...'):
    """Truncates a string after a certain number of chars.
    @rtype : str
    """
    if len(content) <= length:
        return content
    else:
        return content[:length].rsplit(' ', 1)[0] + suffix

# ALL CODE BELOW THIS LINE IS COVERED BY THE FOLLOWING AGREEMENT:

# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
#  3. Neither the name of Django nor the names of its contributors may be used
#     to endorse or promote products derived from this software without
#     specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"AND
#ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED.IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
#ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Expression to match some_token and some_token="with spaces" (and similarly
# for single-quoted strings).

split_re = re.compile(r"""((?:[^\s'"]*(?:(?:"(?:[^"\\]|\\.)*" | '(?:["""
                      r"""^'\\]|\\.)*')[^\s'"]*)+) | \S+)""", re.VERBOSE)


def smart_split(text):
    r"""
    Generator that splits a string by spaces, leaving quoted phrases together.
    Supports both single and double quotes, and supports escaping quotes with
    backslashes. In the output, strings will keep their initial and trailing
    quote marks and escaped quotes will remain escaped (the results can then
    be further processed with unescape_string_literal()).

    >>> list(smart_split(r'This is "a person\'s" test.'))
    [u'This', u'is', u'"a person\\\'s"', u'test.']
    >>> list(smart_split(r"Another 'person\'s' test."))
    [u'Another', u"'person\\'s'", u'test.']
    >>> list(smart_split(r'A "\"funky\" style" test.'))
    [u'A', u'"\\"funky\\" style"', u'test.']
    """
    for bit in split_re.finditer(text):
        yield bit.group(0)


def get_text_list(list_, last_word='or'):
    """
    >>> get_text_list(['a', 'b', 'c', 'd'])
    u'a, b, c or d'
    >>> get_text_list(['a', 'b', 'c'], 'and')
    u'a, b and c'
    >>> get_text_list(['a', 'b'], 'and')
    u'a and b'
    >>> get_text_list(['a'])
    u'a'
    >>> get_text_list([])
    u''
    """
    if len(list_) == 0:
        return ''
    if len(list_) == 1:
        return list_[0]
    return '%s %s %s' % (
        # Translators: This string is used as a separator between list elements
        ', '.join([i for i in list_][:-1]),
        last_word, list_[-1])
