#!/usr/bin/env python3

import fnmatch
import os
import re
import readline


''' Infinite loop to get yes or no answer or quit the script '''


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


''' Takes a list of options and selections as an argument and presents a
checkbox menu with previously selected items still selected.  '''


def menu(options, chosen):
    pad = 0
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

    print("\nEnter option names (wildcards accepted), or numbers, to toggle " +
          "selections.\n" +
          "Enter t to toggle all, r to reset, a to accept selections, or q to" +
          " quit.\n")

    for option in options:
        if len(option[0]) > pad:
            pad = len(option[0])

    for option in options:
        index = options.index(option)
        print("{0:>1} {1:>2}) {2:{pad}} {3:>10}"
              .format(chosen[index], index+1,  option[0], option[1], pad=pad))


'''Takes two lists and compares them, for each item in the first list we see
how many items in the second list it matches with globbing or with explicit
number selection (based on the human readable, not 0 indexing!).

Returns a tuple:

The first element of which is a list of indexes of the second list that the
first list matches.

The second of which is a boolean that indicates whether or not any items in the
first list failed to match with any items in the second.

The Third element of which is the item of the first list that didn't match
against any items in the second list.'''


def get_matches(list1, list2):
    boolean = False
    matches = []

    for items1 in list1:
        count = 0
        total = len(list2)
        for items2 in list2:
            index = list2.index(items2)
            number = index + 1
            number = str(number)
            regex = fnmatch.translate(items1)  # convert globs to regex
            if re.match(regex, items2[0]) or re.match(regex, number):
                boolean = False
                matches.append(index)
            else:
                invalid = items1
                count += 1

        if count == total:
            boolean = True

    return (matches, boolean, invalid)


''' takes a list of options as an argument and returns a list of selected
options from that list.'''


def choose(options):
    # initialize chosen to be same length as options but with empty items
    chosen = [""] * len(options)
    selected = []
    selectall = False
    fmt, msg = ("",)*2

    while True:

        menu(options, chosen)

        if fmt and msg:
            print(fmt.format(msg))

        # get list of inputs split on spaces
        inputs = input("\n----> ").split(" ")

        if re.match('^t(oggle)?$', inputs[0]):
            invalid = False
            if selectall:
                for o in options:
                    chosen[options.index(o)] = ""
                    selectall = False
            else:
                for o in options:
                    chosen[options.index(o)] = "+"
                    selectall = True
        elif re.match('r(eset)?$', inputs[0]):
            invalid = False
            for o in options:
                chosen[options.index(o)] = ""
        elif re.match('a(ccept)?$', inputs[0]):
            invalid = False
            print()
            break
        elif re.match('q(uit)?$', inputs[0]):
            invalid = False
            print()
            quit()
        else:
            matches = get_matches(inputs, options)
            matched = matches[0]
            invalid = matches[1]
            invalid_input = matches[2]

            for m in matched:
                if chosen[m]:
                    chosen[m] = ""
                else:
                    chosen[m] = "+"

            # check if all options are selected or not
            for o in options:
                if chosen[options.index(o)]:
                    selectall = True
                else:
                    selectall = False
                    break

        if invalid:
            fmt = "\n{0:>5} not found."
            msg = invalid_input
        else:
            fmt, msg = ("",)*2

    for o in options:
        if chosen[options.index(o)]:
            selected.append(o)

    return selected


def main():
    import argparse

    parser = argparse.ArgumentParser(description='\Create a checkbox menu\
    from a list of options.')
    parser.add_argument("options", nargs='+', help="Options for the menu.")
    args = parser.parse_args()

    options = args.options
    selected = choose(options)
    if len(selected) > 0:
        print("Selected items: "+(", ".join(map(str, selected)))+"\n")


# this means that if this script is executed, then  main() will be executed
if __name__ == '__main__':
    main()
