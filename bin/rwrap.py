#!/usr/bin/env python3

###############################################################################
#                               IMPORT LIBRARIES                              #
###############################################################################

import argparse
import fnmatch
import os
import pwd
import re
import readline
import subprocess
import time

###############################################################################
#                              DECLARE CONSTANTS                              #
###############################################################################

RSYNC_OPTS = [
    '--archive',
    '--human-readable'
]

DEFAULT_EXCLUDES = [
    '--exclude="desktop.ini"',
    '--exclude="*.ost"',
    '--exclude="*.pst"',
    '--exclude="*spotify*"',
    '--exclude="*Spotify*"'
]

###############################################################################
#                          USEFUL PORTABLE FUNCTIONS                          #
###############################################################################

# check if a directory exists and if not try to create it.


def check_dir(path):
    if (not(os.isdir(path))):
        try:
            os.makedirs(path)
        except OSError:
            print("Could not create directory.")


# infinite loop to get yes or no answer or quit the script
def ask(question):
    while True:
        ans = input(question)
        ans = ans.lower()
        if re.match('^y(es)?$', ans):
            return True
        elif re.match('^n(o)?$', ans):
            return False
        elif re.match('^q(uit)?$', ans):
            quit()
        else:
            print("%s is invalid. Enter (y)es, (n)o or (q)uit." % ans)


# takes a list of options and selections as an argument and presents a checkbox
# menu with previously selected items still selected.
def show_menu(options, choices):
    pad = 0
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')
        print("\nEnter the option's name (wildcards accepted), or number, to toggle\
    a selection.\nEnter a to toggle all, r to reset or q to quit.\n")
    for option in options:
        if len(option[0]) > pad:
            pad = len(option[0])
    for option in options:
        index = options.index(option)
        print("{0:>1} {1:>2}) {2:{pad}} {3:>10}"
              .format(choices[index], index+1,  option[0], option[1], pad=pad))


# takes a list of options as an argument and returns a list of selected options
# from that list.
def get_selections(options):
    choices = [""] * len(options)
    selected = []
    selectall, invalid = (False,)*2
    fmt, msg = ("",)*2

    while True:
        show_menu(options, choices)
        if fmt and msg:
            print(fmt.format(msg))
            choice = input("\n----> ")

        if re.match('^a(ll)?$', choice):
            invalid = False
            if selectall:
                for o in options:
                    choices[options.index(o)] = ""
                    selectall = False
            else:
                for o in options:
                    choices[options.index(o)] = "+"
                    selectall = True
        elif re.match('r(eset)?$', choice):
            invalid = False
            for o in options:
                choices[options.index(o)] = ""
        elif re.match('q(uit)?$', choice):
            invalid = False
            print()
            break
        else:
            count = 0
            total = len(options)
            for o in options:
                i = options.index(o)
                n = i+1
                number = str(n)
                regex = fnmatch.translate(choice)
                if re.match(regex, o[0]) or re.match(regex, number):
                    invalid = False
                    if choices[i]:
                        choices[i] = ""
                    else:
                        choices[i] = "+"
                else:
                    count += 1

            if count == total:
                invalid = True

            for o in options:
                if choices[options.index(o)]:
                    selectall = True
                else:
                    selectall = False
                    break

        if invalid:
            fmt = "\n{0:>5} not found. Maybe try {0}* or *{0}..."
            msg = choice
        else:
            fmt, msg = ("",)*2

    for o in options:
        if choices[options.index(o)]:
            selected.append(o)

    return selected


# takes a number of bytes as an argument and returns the most suitable human
# readable unit conversion.
def convert(size):
    if size > 1024**3:
        hr = round(size/1024**3)
        unit = "GB"
    elif size > 1024**2:
        hr = round(size/1024**2)
        unit = "MB"
    else:
        hr = round(size/1024)
        unit = "KB"

    hr = str(hr)
    result = hr + " " + unit
    return result


# takes a path as an argument and returns the total size in bytes of the file or
# directory. If the path is a directory the size will be calculated recursively.
def get_size(path):
    total = 0

    if os.path.isdir(path):
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                total += get_size(entry.path)
            else:
                total += entry.stat(follow_symlinks=False).st_size
    else:
        total += os.path.getsize(path)

    return total


# takes a path as an argument and returns a list of child paths that the user
# has selected.
def get_excludes(path):
    options = []
    paths = []

    ls = sorted(listdir(path))
    for i in ls:
        # ignore dotfiles
        if i.startswith("."):
            continue
        lsp = path + "/" + i
        size = get_size(lsp)
        size = convert(size)
        size = " ["+size+"]"
        options.append(tuple((i, size)))

    excludes = get_selections(options)

    for e in excludes:
        p = path + "/" + e[0]
        paths.append(p)
        if os.isdir(p):
            question = "Exclude all of "+p+"? "
            if not(ask(question)):
                paths += get_excludes(p)

    return paths


# takes a list of excluded directories & parent path as an argument and checks
# if the user is happy with the selections. Returns unchanged list if so, or
# re-gets excludes if not.
def check_excludes(excludes, path):
    if len(excludes) > 0:
        print("\nSelected excludes:\n")
        for e in excludes:
            print("\t{}".format(e))
            if ask("\nAccept and use excludes? "):
                return excludes
            else:
                excludes = get_excludes(path)
                check_excludes(excludes, path)
    else:
        if not(ask("\nNo excludes selected. Continue? ")):
            excludes = get_excludes(path)
            check_excludes(excludes, path)


# returns a list of local users on the current machine.
def get_users():
    users = {}
    for p in pwd.getpwall():
        user = p[0]
        home = p[5]
        regex = "^_|admin|daemon|guest|local|nobody|root"
        if not(re.match(regex, user, re.IGNORECASE)):
            users[user] = home

    return users


# return a list of valid arguments
def get_args():
    parser = argparse.ArgumentParser(description='\
    Backup or restore users to an rsync server.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-b", "--backup", action="store_true",
                       help="Backup users to rsync server or path.")
    group.add_argument("-r", "--restore", action="store_true",
                       help="Restore users on from last backup.")
    parser.add_argument("-u", "--users", action="store_true",
                        help="Automate user selection.")
    parser.add_argument("-x", "--excludes", action="store_true",
                        help="Automate excludes selection.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", action="store_true",
                       help="Increase output verbosity.")
    group.add_argument("-q", "--quiet", action="store_true",
                       help="Run silently.")
    parser.add_argument("url", type=str, help="A valid rsync url.")
    return parser.parse_args()


def copy_skel(date, user, url):
    parent = "/tmp"
    skel = parent + "/Users/" + user + "/" + date
    check_dir(skel)
    cmd = "rsync " + ' '.join(RSYNC_OPTS) + " --quiet " + skel + " " + url
    subprocess.call(cmd, shell=True)


def rwrap(src, dest, automate_excludes):
    if automate_excludes:
        cmd = "rsync " + " ".join(RSYNC_OPTS) + \
            " ".join(DEFAULT_EXCLUDES) + " " + src + " " + dest
        subprocess.call(cmd, shell=True)
    else:
        excludes = get_selections(src)
        # list + set removes duplicates.
        excludes = excludes + list(set(excludes + DEFAULT_EXCLUDES))
        cmd = "rsync " + " ".join(RSYNC_OPTS) + \
            " ".join(excludes) + src + " " + dest
        subprocess.call(cmd, shell=True)


def main():
    users = get_users()
    args = get_args()

    if len(users) > 0:
        print("Users: "+(', '.join(users.keys())))
        for user, home in users.items():
            if args.backup:
                copytype = "backup"
                date = time.strftime("%Y-%m-%d")
                src = home + "/"
                dest = args.url + "/Users/" + user + "/" + date
                copy_skel(date, user, args.url)
            elif args.restore:
                copytype = "restore"
                upath = (args.url + "/Users/" + user)
                date = sorted(os.listdir(upath), reverse=True)[0]
                src = upath + "/" + date + "/"
                dest = home

            if args.users:
                rwrap(src, dest, args.excludes)
            else:
                question = "\n" + copytype.title() + " " + user + "? "
                if ask(question):
                    rwrap(src, dest, args.excludes)
    else:
        print("No users to %s" % copytype)


main()
