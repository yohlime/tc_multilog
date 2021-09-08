#!/usr/bin/bash

cd $MAIN_DIR

mkdir -p $QGIS_DATA_DIR

$PYTHON $MAIN_DIR/scripts/cron_multi.py

# Copy to QGIS directory
echo "Copying files to QGIS directory..."
cp -rp ${OUT_SHP_DIR} ${QGIS_DATA_DIR}