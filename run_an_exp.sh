#!/bin/bash

source /opt/conda/etc/profile.d/conda.sh
conda activate spotlight-ae
./run-ae.sh single --model RESNET --target EDP --technique Spotlight --scale Edge