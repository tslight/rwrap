#!/usr/bin/env python3
import fnmatch
import os
import re
import readline


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
def menu(options, choices):
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
def choose(options):
    choices = [""] * len(options)
    selected = []
    selectall, invalid = (False,)*2
    fmt, msg = ("",)*2

    while True:
        
        menu(options, choices)
        
        if fmt and msg:
            print(fmt.format(msg))

        # get array of input split on spaces
        choice = input("\n----> ").split(" ")

        if re.match('^a(ll)?$', choice[0]):
            invalid = False
            if selectall:
                for o in options:
                    choices[options.index(o)] = ""
                    selectall = False
            else:
                for o in options:
                    choices[options.index(o)] = "+"
                    selectall = True
        elif re.match('r(eset)?$', choice[0]):
            invalid = False
            for o in options:
                choices[options.index(o)] = ""
        elif re.match('q(uit)?$', choice[0]):
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
                for c in choice:
                    regex = fnmatch.translate(c)
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
