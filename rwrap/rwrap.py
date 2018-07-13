import argparse
import curses
import os
import pwd
import re
import subprocess
import time

from ui import ask
from ppick import select
os.environ.setdefault('ESCDELAY', '12')  # otherwise it takes an age!

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


def check_dir(path):
    """
    Check if a directory exists and if not try to create it.
    """
    if (not(os.path.isdir(path))):
        try:
            os.makedirs(path)
        except OSError:
            print("Could not create directory.")


def get_excludes(path, hidden):
    """
    Takes a path as an argument and returns a list of child paths that the user
    has selected.
    """
    excludes = curses.wrapper(select, path, hidden)
    if len(excludes) > 0:
        print("\nSelected excludes:\n"+('\n'.join(excludes)))
        if ask("\nAccept and use excludes? "):
            return excludes
        else:
            excludes = get_excludes(path, hidden)
    else:
        if not(ask("\nNo excludes selected. Continue? ")):
            excludes = get_excludes(path, hidden)
    return excludes


def get_users():
    """
    Return a dictionary of users. User name is the key, home directory path is
    the value.
    """
    users = {}
    for p in pwd.getpwall():
        user = p[0]
        home = p[5]
        regex = "^_|admin|daemon|guest|local|nobody|root"
        if not(re.match(regex, user, re.IGNORECASE)):
            users[user] = home

    return users


def get_args():
    """
    Return a list of valid arguments.
    """
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
    hidden = True
    if automate_excludes:
        cmd = "rsync " + " ".join(RSYNC_OPTS) + \
            " ".join(DEFAULT_EXCLUDES) + " " + src + " " + dest
        subprocess.call(cmd, shell=True)
    else:
        excludes = get_excludes(src, hidden)
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
