#!/bin/bash

if [[ "$0" = "$BASH_SOURCE" ]]; then
    echo "Needs to be run using source: . install-dev.sh"

else
    rm -rf _virtualenv
    virtualenv _virtualenv -p /usr/local/bin/python3.8
    VENVPATH="_virtualenv/bin/activate"
    if [[ $# -eq 1 ]]; then 
        if [ -d $1 ]; then
            VENVPATH="$1/bin/activate"
        else
            echo "Virtual environment $1 not found"
            return
        fi

    elif [ -d "_virtualenv" ]; then 
        VENVPATH="_virtualenv/bin/activate"

    elif [-d "env"]; then 
        VENVPATH="env/bin/activate"
    fi

    echo "Activating virtual environment $VENVPATH"
    source "$VENVPATH"
fi

python --version
pip3 install -r requirements.txt
pip3 install -r requirements-dev.txt
