#！/bin/bash

MAIN_FOLDER=

for SUBFOLDER in '$/MAIN_FOLDER/*'; dp
  if [ -d "$SUBFOLDER" ]; then
      echo "Processing $SUBFOLDER"

      hython run_on_template.py ""

