#!/bin/bash
export SCRIPTDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export RSYNC_VERSION="$(rsync --version | head -n 1 | awk '{print $6}')"

declare -a OPTS=()

clear

ask () {
    local question="$1" ans

    while :; do
	# -n 1 to exit after first letter
	# -r to keep backslashes in tact
	# -e for readline bindings
	read -n 1 -rep "$question" ans;
	case "$ans" in
	    y|Y)
		return 0
		;;
	    n|N)
		return 1
		;;
	    q|Q)
		exit 1
		;;
	    *)
		echo "($ans) is invalid. Enter (y)es, (n)o or (q)uit.";
		;;
	esac;
    done
}

get_opts () {
    echo
    echo "Running with elevated privileges (sudo)..."
    echo
    if ((RSYNC_VERSION<31)); then
	sudo cp "$SCRIPTDIR"/bin/rsync /usr/local/bin/
    fi
    sudo cp "$SCRIPTDIR"/src/rwrap /usr/local/bin/
    sudo chmod 755 /usr/local/bin/{rsync,rwrap}

    PATH=/usr/local/bin:$PATH:

    echo
    while :; do
	read -n 1 -rep "Do you want to (b)ackup or (r)estore? " type;
	case "$type" in
	    b|B)
		OPTS+=(-b)
		TYPE="backup"
		break
		;;
	    r|R)
		OPTS+=(-r)
		TYPE="restore"
		break
		;;
	    q|Q)
		echo
		exit 1
		;;
	    *)
		echo
		echo "($type) is invalid. Enter (b)ackup, (r)estore or (q)uit."
		echo
		;;
	esac
    done

    echo
    if ask "Automate user selection? "; then
	OPTS+=(-u)
    fi

    if [[ "${OPTS[0]}" == "-b" ]]; then
	echo
	if ask "Automate excludes selection? "; then
	    OPTS+=(-x)
	fi
    fi

    echo
    if ask "Run with increased verbosity? "; then
	OPTS+=(-v)
    fi

    echo
    read -rep "Enter mountpoint of backup drive: " drive

    if [[ -d "$drive" ]]; then
	sudo rwrap "${OPTS[@]}" "$drive"
    else
	echo
	echo "Invalid Path. Aborting."
	exit 1
    fi

    echo "Finished running $TYPE script."
    echo
}

export -f ask
export -f get_opts

# check if admin account exists
if id admin &> /dev/null; then
    if [[ $(whoami) == "admin" ]]; then
	get_opts
    else
	echo
	echo "Logging in as admin..."
	echo
	su admin -c 'get_opts'
    fi
else
    get_opts
fi
