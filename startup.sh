#!/bin/bash

if [ ! -d "venv" ] 
then
    rm -rf venv
    python3 --version
    python3 -m venv venv
    source ./venv/bin/activate 
    pip install --upgrade pip 
    pip install -r requirements.txt 
fi
./venv/bin/python scripts/test_db_tunnel.py int ugc-cleaner 5432 mr1qf4ez7ls7xfn.c66kz9sr8urn.eu-west-2.rds.amazonaws.com



