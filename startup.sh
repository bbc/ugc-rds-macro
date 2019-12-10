#!/bin/bash

if [ ! -d "mvenv" ] 
then
    rm -rf mvenv
    python3 --version
    python3 -m venv mvenv
    source ./mvenv/bin/activate 
    pip install --upgrade pip 
    pip install -r requirements.txt 
fi
./mvenv/bin/python scripts/test_db_tunnel.py int ugc-manager 5432 ou1v70ll9f9f8sf.c66kz9sr8urn.eu-west-2.rds.amazonaws.com



