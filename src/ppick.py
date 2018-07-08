#!/usr/bin/python
"""
Yet another curses-based directory tree browser, in Python.

I thought I could use something like this for filename entry, kind of like the
old 4DOS 'select' command --- cd $(cursoutline.py).  So you navigate and hit
Enter, and it exits and spits out the file you're on.

Originally from: http://lists.canonical.org/pipermail/kragen-hacks/2005-December/000424.html
Originally by: Kragen Sitaker

There are several general approaches to the drawing-an-outline problem. This
program supports the following operations:

   - move cursor to previous item (in preorder traversal)
   - move cursor to next item (likewise)
   - hide descendants
   - reveal children

And because it runs over the filesystem, it must be at least somewhat lazy
about expanding children.

And it doesn't really bother to worry about someone else changing the outline
behind its back.

So the strategy is to store our current linear position in the inorder
traversal, and defer operations on the current node until the next time we're
traversing.
"""

import argparse
import curses
import random
import os
import sys
import readline


def pad(data, width):
    # XXX this won't work with UTF-8
    return data + ' ' * (width - len(data))


def listdir_nohidden(path):
    for f in os.listdir(path):
        if not f.startswith('.'):
            yield f


class File:
    def __init__(self, name, hidden):
        self.name = name
        self.hidden = hidden
        self.marked = False
        self.expanded = False

    def render(self, depth, width):
        return pad('%s%s %s%s' % (' ' * 4 * depth, self.icon1(),
                                  os.path.basename(self.name), self.icon2()), width)

    def icon1(self): return '   '

    def icon2(self):
        if self.marked:
            return ' * '
        else:
            return ''

    def traverse(self): yield self, 0

    def expand(self): pass

    def collapse(self): pass

    def mark(self): self.marked = True

    def unmark(self): self.marked = False


class Dir(File):
    def __init__(self, name, hidden):
        File.__init__(self, name, hidden)
        self.hidden = hidden
        try:
            if self.hidden:
                self.kidnames = sorted(listdir_nohidden(name))
            else:
                self.kidnames = sorted(os.listdir(name))
        except:
            self.kidnames = None  # probably permission denied
        self.kids = None
        self.expanded = False
        self.marked = False

    def children(self):
        if self.kidnames is None:
            return []
        if self.kids is None:
            # for kid in self.kidnames:
            #     self.kids = mknode(os.path.join(self.name, kid), self.hidden)
            self.kids = [mknode(os.path.join(self.name, kid), self.hidden)
                         for kid in self.kidnames]
        return self.kids

    def icon1(self):
        if self.expanded:
            return '[-]'
        elif self.children():
            return '[+]'
        elif self.kidnames is None:
            return '[?]'
        else:
            return '[ ]'

    def icon2(self):
        if self.marked:
            return ' * '
        else:
            return ''

    def expand(self): self.expanded = True

    def collapse(self): self.expanded = False

    def mark(self): self.marked = True

    def unmark(self): self.marked = False

    def traverse(self):
        yield (self, 0)
        if not self.expanded:
            return

        for child in self.children():
            for kid, depth in child.traverse():
                yield kid, depth + 1


def parse_keys(ch, curidx):
    action = None
    if ch == curses.KEY_UP or ch == ord('k') or ch == ord('p'):
        curidx -= 1
    elif ch == curses.KEY_DOWN or ch == ord('j') or ch == ord('n'):
        curidx += 1
    elif ch == curses.KEY_RIGHT or ch == ord('l') or ch == ord('f'):
        action = 'expand'
    elif ch == curses.KEY_LEFT or ch == ord('h') or ch == ord('b'):
        action = 'collapse'
    elif ch == curses.KEY_HOME or ch == ord('g') or ch == ord('<'):
        curidx = 0
    elif ch == curses.KEY_END or ch == ord('G') or ch == ord('>'):
        curidx = line - 1
    elif ch == ord('\t') or ch == ord('\n'):
        action = 'toggle_expand'
    elif ch == ord('m') or ch == ord(' '):
        action = 'toggle_mark'
    elif ch == ord('.'):
        action = 'toggle_hidden'
    elif ch == ord('r'):
        action = 'reset'
    return (action, curidx)


def mknode(path, hidden):
    if os.path.isdir(path):
        return Dir(path, hidden)
    else:
        return File(path, hidden)


def select(stdscr, root, hidden):
    node = mknode(root, hidden)
    node.expand()
    curidx = 1
    action = None
    ESC = 27
    selected = []

    while True:
        stdscr.erase()  # https://stackoverflow.com/a/24966639
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        line = 0
        offset = max(0, curidx - curses.LINES + 10)

        for data, depth in node.traverse():
            if line == curidx:
                stdscr.attrset(curses.color_pair(1) | curses.A_BOLD)
                if action == 'toggle_mark':
                    if data.marked:
                        data.unmark()
                        selected.remove(data.name)
                    else:
                        data.mark()
                        selected.append(data.name)
                    stdscr.attrset(curses.color_pair(0))
                    curidx += 1
                elif action == 'toggle_expand':
                    if data.expanded:
                        data.collapse()
                    else:
                        data.expand()
                elif action == 'toggle_hidden':
                    # such a terrible hack!
                    if hidden:
                        hidden = False
                        selected = select(stdscr, root, hidden)
                        return selected
                    else:
                        hidden = True
                        selected = select(stdscr, root, hidden)
                        return selected
                elif action == 'reset':
                    # such a terrible hack!
                    selected = select(stdscr, root)
                    return selected
                elif action:
                    getattr(data, action)()
                action = None
            else:
                stdscr.attrset(curses.color_pair(0))
            if 0 <= line - offset < curses.LINES - 1:
                stdscr.addstr(line - offset, 0,
                              data.render(depth, curses.COLS))
            line += 1

        stdscr.refresh()
        ch = stdscr.getch()
        if ch == ord('e') or ch == ord('q') or ch == ESC:
            return selected
        else:
            keyresult = parse_keys(ch, curidx)
            action = keyresult[0]
            curidx = keyresult[1]
        curidx %= line


def open_tty():
    saved_stdin = os.dup(0)
    saved_stdout = os.dup(1)
    os.close(0)
    os.close(1)
    stdin = os.open('/dev/tty', os.O_RDONLY)
    stdout = os.open('/dev/tty', os.O_RDWR)
    return (saved_stdin, saved_stdout)


def restore_stdio(saved_fds):
    saved_stdin = saved_fds[0]
    saved_stdout = saved_fds[1]
    os.close(0)
    os.close(1)
    os.dup(saved_stdin)
    os.dup(saved_stdout)


def get_args():
    """
    Return a list of valid arguments.
    """
    parser = argparse.ArgumentParser(description='\
    Select paths from a directory tree.')
    parser.add_argument("-a", "--hidden", action="store_true",
                        help="Show all hidden paths too.")
    parser.add_argument("path", type=str, default='.', help="A valid path.")
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    root = args.path
    hidden = args.hidden
    saved_fds = open_tty()
    try:
        paths = curses.wrapper(select, root, hidden)
    finally:
        restore_stdio(saved_fds)

    print(paths)
