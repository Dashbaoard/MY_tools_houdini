#!/bin/bash

for filename in C:/baidunetdiskdownload/Land Rover Defender Works V8 Trophy 2021/test_car/*.obj; do
  hython script.py "C:/chajian/python/houdini/MY_tools_houdini/scripts/python/main_basic_template.hip" "$filename"

done 