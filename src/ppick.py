#!/usr/bin/env python3
"""
There are several general approaches to the drawing-an-outline problem. This
program supports the following operations:

   - Navigate items using pre-order traversal, with arrow keys, Vi or Emacs
     bindings.
   - Expand or collapse children, one at time or all at once.
   - Toggle marking of items, for use in selection mechanism for another module.
   - Toggling display of toggle disk usage of an item, using size.py module.

It runs over the filesystem, so it is somewhat lazy about expanding children.

It doesn't really bother to worry about someone else changing the outline behind
its back.

So the strategy is to store our current linear position in the inorder
traversal, and defer operations on the current node until the next time we're
traversing.
"""

import argparse
import cgitb
import curses
import random
import os
import pdb
import readline
import size
import sys

# Get more detailed traceback reports
cgitb.enable(format="text")  # https://pymotw.com/2/cgitb/


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
        self.paths = None
        self.expanded = False
        self.marked = False
        self.getsize = False
        self.size = None

    def listdir(self, path):
        for f in os.listdir(path):
            if not f.startswith('.'):
                yield f

    def drawline(self, depth, width):
        pad = ' ' * 4 * depth
        mark = self.mark()
        size = self.du()
        node = self.getnode()
        nodestr = '{}{}{}{}'.format(pad, node, size, mark)
        return nodestr + ' ' * (width - len(nodestr))

    def drawlines(self, scr, depth, curline, line):
        offset = max(0, curline - curses.LINES + 10)
        if 0 <= line - offset < curses.LINES - 1:
            scr.addstr(line - offset, 0,
                       self.drawline(depth - 1, curses.COLS))

    def getpaths(self):
        if self.children is None:
            return
        if self.paths is None:
            self.paths = [Paths(os.path.join(self.name, child), self.hidden)
                          for child in self.children]
        return self.paths

    def getnode(self):
        if not os.path.isdir(self.name):
            return '    ' + os.path.basename(self.name)
        elif self.expanded:
            return '[-] ' + os.path.basename(self.name) + '/'
        elif self.getpaths():
            return '[+] ' + os.path.basename(self.name) + '/'
        elif self.children is None:
            return '[?] ' + os.path.basename(self.name) + '/'
        else:
            return '[ ] ' + os.path.basename(self.name) + '/'

    def mark(self):
        if self.marked:
            return ' *'
        else:
            return ''

    def du(self):
        if self.getsize:
            bytes_ = size.totalsize(self.name)
            size_ = size.convert(bytes_)
            # save state as object attribute
            self.size = " (" + size_ + ")"
            return self.size
        else:
            if self.size:
                return self.size
            else:
                return ''

    def expand(self):
        if os.path.isdir(self.name):
            self.expanded = True

    def collapse(self):
        if os.path.isdir(self.name):
            self.expanded = False

    def nextparent(self, colors, parent, path, curline, depth, selected):
        line = 0
        count = 0
        if depth > 1:
            curpar = os.path.dirname(os.path.dirname(path))
            cpaths = Paths(curpar, hidden)
            curdir = os.path.basename(os.path.dirname(path))
            curidx = cpaths.children.index(curdir)
            nextdir = cpaths.children[curidx + 1]
            for c, d in parent.traverse():
                if os.path.basename(c.name) == nextdir:
                    break
                if line > curline:
                    colors.default(path, selected)
                    count += 1
                line += 1
        else:
            # if we're in root then skip to next dir
            for c, d in self.traverse():
                if line > curline + 1:
                    colors.default(path, selected)
                    count += 1
                    if os.path.isdir(c.name):
                        break
                line += 1
        return count

    def prevparent(self, colors, parent, path, selected):
        count = 0
        p = os.path.dirname(path)
        # once we hit the parent directory, break, and set the
        # curline to the line number we got to.
        for c, d in parent.traverse():
            if c.name == p:
                break
            count += 1
        colors.default(path, selected)
        return count

    def traverse(self):
        yield self, 0

        if not self.expanded:
            return

        for child in self.getpaths():
            for c, depth in child.traverse():
                yield c, depth + 1


class Colors:
    def __init__(self, stdscr):
        self.scr = stdscr
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_YELLOW)

    def reset(self):
        self.scr.attrset(curses.color_pair(0))

    def white_blue(self):
        self.scr.attrset(curses.color_pair(1) | curses.A_BOLD)

    def blue_black(self):
        self.scr.attrset(curses.color_pair(2) | curses.A_BOLD)

    def yellow_black(self):
        self.scr.attrset(curses.color_pair(3))

    def black_yellow(self):
        self.scr.attrset(curses.color_pair(4))

    def selected(self, path, selected):
        if path in selected:
            self.black_yellow()
        else:
            self.white_blue()

    def default(self, path, selected):
        # restore color to marked
        if path in selected:
            self.yellow_black()
        elif os.path.isdir(path):
            self.blue_black()
        else:
            self.reset()


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
    colors = Colors(stdscr)
    curline = 0
    action = None
    selected = []
    parent.expand()

    while True:
        # offset = max(0, curline - curses.LINES + 10)
        line = 0

        # to reset or toggle view of dotfiles we need to create a new Path
        # object before, erasing the screen & descending into draw loop.
        if action == 'reset':
            parent = Paths(root, hidden)
            parent.expand()
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
                # selected line needs to be different than default
                colors.selected(child.name, selected)

                cl = curline  # for use in parent jump actions
                lc = 0  # for use in parent jump actions

                if action == 'expand':
                    child.expand()
                    colors.default(child.name, selected)
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
                        child.marked = False
                        selected.remove(child.name)
                        colors.default(child.name, selected)
                    else:
                        child.marked = True
                        selected.append(child.name)
                        colors.yellow_black()
                    curline += 1
                elif action == 'next_parent':
                    curline += child.nextparent(
                        colors, parent, child.name, curline, depth, selected)
                elif action == 'prev_parent':
                    curline = child.prevparent(
                        colors, parent, child.name, selected)
                elif action == 'get_size':
                    child.getsize = True
                    colors.default(child.name, selected)
                    curline += 1
                elif action == 'get_size_all':
                    for c, d in parent.traverse():
                        c.getsize = True
                action = None  # reset action

            else:
                colors.default(child.name, selected)

            child.drawlines(stdscr, depth, curline, line)

            child.getsize = False  # stop computing sizes!
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
