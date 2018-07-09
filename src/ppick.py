#!/usr/bin/python
"""
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


class Paths:
    def __init__(self, name, hidden):
        self.name = name
        self.hidden = hidden
        try:
            if self.hidden:
                self.children = sorted(self.listdir(name))
            else:
                self.children = sorted(os.listdir(name))
        except:
            self.children = None  # probably permission denied
        self.childpaths = None
        self.expanded = False
        self.marked = False

    def listdir(self, path):
        for f in os.listdir(path):
            if not f.startswith('.'):
                yield f

    def draw_line(self, depth, width):
        pad = ' ' * 4 * depth
        icon1 = self.icon1()
        icon2 = self.icon2()
        node = os.path.basename(self.name)
        nodestr = '{}{} {}{}'.format(pad, icon1, node, icon2)
        return nodestr + ' ' * (width - len(nodestr))

    def get_childpaths(self):
        if self.children is None:
            return
        if self.childpaths is None:
            self.childpaths = [Paths(os.path.join(self.name, child), self.hidden)
                               for child in self.children]
        return self.childpaths

    def icon1(self):
        if not os.path.isdir(self.name):
            return '   '
        elif self.expanded:
            return '[-]'
        elif self.get_childpaths():
            return '[+]'
        elif self.children is None:
            return '[?]'
        else:
            return '[ ]'

    def icon2(self):
        if self.marked:
            return ' * '
        else:
            return ''

    def expand(self):
        if os.path.isdir(self.name):
            self.expanded = True
        else:
            pass

    def collapse(self):
        if os.path.isdir(self.name):
            self.expanded = False
        else:
            pass

    def mark(self): self.marked = True

    def unmark(self): self.marked = False

    def traverse(self):
        yield self, 0

        if not self.expanded:
            return

        for child in self.get_childpaths():
            for c, depth in child.traverse():
                yield c, depth + 1


def parse_keys(stdscr, curline, line):
    ESC = 27
    action = None
    ch = stdscr.getch()
    if ch == ord('e') or ch == ord('q') or ch == ESC:
        return
    elif ch == ord('r'):
        action = 'reset'
    elif ch == ord('.'):
        action = 'toggle_hidden'
    elif ch == curses.KEY_RIGHT or ch == ord('l') or ch == ord('f'):
        action = 'expand'
    elif ch == curses.KEY_LEFT or ch == ord('h') or ch == ord('b'):
        action = 'collapse'
    elif ch == ord('L') or ch == ord('F'):
        action = 'expand_all'
    elif ch == ord('H') or ch == ord('B'):
        action = 'collapse_all'
    elif ch == ord('\t') or ch == ord('\n'):
        action = 'toggle_expand'
    elif ch == ord('m') or ch == ord(' '):
        action = 'toggle_mark'
    elif ch == ord('J') or ch == ord('N'):
        action = 'next_parent'
    elif ch == ord('K') or ch == ord('P'):
        action = 'prev_parent'
    elif ch == ord('s') or ch == ord('?'):
        action = 'get_size'
    elif ch == ord('S'):
        action = 'get_size_all'
    elif ch == curses.KEY_UP or ch == ord('k') or ch == ord('p'):
        curline -= 1
    elif ch == curses.KEY_DOWN or ch == ord('j') or ch == ord('n'):
        curline += 1
    elif ch == curses.KEY_UP or ch == ord('k') or ch == ord('p'):
        curline -= 1
    elif ch == curses.KEY_DOWN or ch == ord('j') or ch == ord('n'):
        curline += 1
    elif ch == curses.KEY_PPAGE or ch == ord('u') or ch == ord('V'):
        curline -= curses.LINES
        if curline < 0:
            curline = 0
    elif ch == curses.KEY_NPAGE or ch == ord('d') or ch == ord('v'):
        curline += curses.LINES
        if curline >= line:
            curline = line - 1
    elif ch == curses.KEY_HOME or ch == ord('g') or ch == ord('<'):
        curline = 0
    elif ch == curses.KEY_END or ch == ord('G') or ch == ord('>'):
        curline = line - 1
    curline %= line
    return action, curline


def select(stdscr, root, hidden):
    parent = Paths(root, hidden)
    parent.expand()
    curline = 0
    action = None
    selected = []

    while True:
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        offset = max(0, curline - curses.LINES + 10)
        line = 0

        oldline = curline
        # to reset or toggle view of dotfiles we need to create a new Path
        # object before, erasing the screen & descending into draw loop.
        if action == 'reset':
            parent = Paths(root, hidden)
            parent.expand()
            curline = oldline  # restore old position
            action = None
            selected = []
        elif action == 'toggle_hidden':
            if hidden:
                hidden = False
            else:
                hidden = True
            parent = Paths(root, hidden)
            parent.expand()
            action = None
            # restore marked state
            for child, depth in parent.traverse():
                if child.name in selected:
                    child.mark()

        stdscr.erase()  # https://stackoverflow.com/a/24966639 - prevent flashes

        for child, depth in parent.traverse():
            if depth == 0:
                continue  # don't draw root node
            if line == curline:
                # change color of current line depending on whether or not it's
                # been selected.
                if child.name in selected:
                    stdscr.attrset(curses.color_pair(3))
                else:
                    stdscr.attrset(curses.color_pair(1) | curses.A_BOLD)

                if action == 'expand':
                    child.expand()
                    stdscr.attrset(curses.color_pair(0))
                    curline += 1
                elif action == 'collapse':
                    child.collapse()
                elif action == 'expand_all':
                    for c, d in child.traverse():
                        # only expand one level at a time
                        if d > 1:
                            continue
                        c.expand()
                elif action == 'collapse_all':
                    pass
                elif action == 'toggle_expand':
                    if child.expanded:
                        child.collapse()
                    else:
                        child.expand()
                elif action == 'toggle_mark':
                    if child.marked:
                        child.unmark()
                        selected.remove(child.name)
                        stdscr.attrset(curses.color_pair(0))
                    else:
                        child.mark()
                        selected.append(child.name)
                        stdscr.attrset(curses.color_pair(2))
                    curline += 1
                elif action == 'next_parent':
                    pass
                elif action == 'prev_parent':
                    pass
                elif action == 'get_size':
                    pass
                elif action == 'get_size_all':
                    pass
                action = None  # reset action
            else:
                stdscr.attrset(curses.color_pair(0))
                # restore color to marked
                if child.name in selected:
                    stdscr.attrset(curses.color_pair(2))

            if 0 <= line - offset < curses.LINES - 1:
                stdscr.addstr(line - offset, 0,
                              child.draw_line(depth - 1, curses.COLS))

            line += 1  # keep scrolling!

        stdscr.refresh()

        results = parse_keys(stdscr, curline, line)
        if results:
            action = results[0]
            curline = results[1]
        else:
            return selected


def get_args():
    """
    Return a list of valid arguments.
    """
    parser = argparse.ArgumentParser(description='\
    Select paths from a directory tree.')
    parser.add_argument("-a", "--hidden", action="store_false",
                        help="Show all hidden paths too.")
    parser.add_argument("path", type=str, nargs='?',
                        default=".", help="A valid path.")
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    root = args.path
    hidden = args.hidden
    paths = curses.wrapper(select, root, hidden)
    print("\n".join(paths))
