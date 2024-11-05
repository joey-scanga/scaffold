#!/bin/bash

if [[ -z $NIBABIES_SCAFFOLD_SHARE ]]; then
  export NIBABIES_SCAFFOLD_SHARE="$(realpath ~/.local/share/nibabies-scaffold)"
  mkdir -p $NIBABIES_SCAFFOLD_SHARE
  export NIBABIES_SCAFFOLD_HISTORY="${NIBABIES_SCAFFOLD_SHARE}/history.txt"
  touch $NIBABIES_SCAFFOLD_HISTORY
fi

PARAMS=""

read -r -d '' usage <<- EOM
	usage: $0 [-h] [ --hist | --history ] [ --clear_history ]

	-h: display help
	--hist, --history: display nibabies call history
    --clear_history: clears history file
EOM

while (( "$#" )); do
  case "$1" in
    -h|--help)
      echo "$usage"
      exit 0
      shift
      ;;
    --hist|--history)
      less +G $NIBABIES_SCAFFOLD_HISTORY
      exit 0
      shift
      ;;
    --clear_history)
      rm $NIBABIES_SCAFFOLD_HISTORY
      touch $NIBABIES_SCAFFOLD_HISTORY
      echo "History file at $NIBABIES_SCAFFOLD_HISTORY cleared."
      exit 0
      shift
      ;;
    -*|--*=) # unsupported flags
      echo "Error: Unsupported flag $1" >&2
      exit 1
      ;;
    *) # preserve positional arguments
      PARAMS="$PARAMS $1"
      shift
      ;;
  esac
done # set positional arguments in their proper place
eval set -- "$PARAMS"


if [[ -z $NIBABIES_SCAFFOLD_SHARE ]]; then
    export NIBABIES_SCAFFOLD_SHARE="$(realpath ~/.local/share/nibabies-scaffold)"
    mkdir -p $NIBABIES_SCAFFOLD_SHARE
    export NIBABIES_SCAFFOLD_HISTORY="${NIBABIES_SCAFFOLD_SHARE}/history.txt"
    touch $NIBABIES_SCAFFOLD_HISTORY
fi

if [[ -z $NIBABIES_SCAFFOLD_TXT ]]; then
    export NIBABIES_SCAFFOLD_TXT="${NIBABIES_SCAFFOLD_SHARE}/nibabies-scaffold.txt"
    if [ ! -f $NIBABIES_SCAFFOLD_TXT ]; then
        cp "$(pwd)/nibabies-scaffold.txt" $NIBABIES_SCAFFOLD_TXT
        chmod 777 $NIBABIES_SCAFFOLD_TXT
    fi
fi

if [[ -z $NIBABIES_SCAFFOLD_STATE ]]; then
    export NIBABIES_SCAFFOLD_STATE="$(realpath ~/.local/state/nibabies-scaffold)"
    mkdir -p ${NIBABIES_SCAFFOLD_STATE}
fi

command_file="${NIBABIES_SCAFFOLD_STATE}/command_$(date +%s)"
cp $NIBABIES_SCAFFOLD_TXT $command_file
nano $command_file
if [[ ! -f $command_file ]]; then
    echo "ERROR: $command_file doesn't exist (this shouldn't happen)"
    exit 1
fi

shell_command=""
while IFS= read -r line; do
    # Skip empty lines and lines starting with '#'
    [[ -z "$line" || "$line" == '#'* ]] && continue

    # Print the line with a backslash at the end, except for the last line
    if [[ "$line" != *"$"* ]]; then
        shell_command+="${line%\\} "
    else
        shell_command+="$line "
    fi
done < "$command_file"

shell_command="${shell_command//[[:space:]]+/ }"
echo "$shell_command"
eval "$shell_command"

d=$(date)
echo $d >> $NIBABIES_SCAFFOLD_HISTORY
printf "%$((${#d}))s\n" | tr ' ' '-' >> $NIBABIES_SCAFFOLD_HISTORY
echo -e "$shell_command\n" >> $NIBABIES_SCAFFOLD_HISTORY
