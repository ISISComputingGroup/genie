#!/bin/sh
set -o errexit

source ../package_builder/build-genie-python/venv/bin/activate
python3 -m pip install -r requirements.txt
make html

deactivate
