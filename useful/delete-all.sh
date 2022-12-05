#!/bin/bash
lxc delete $(lxc list -c n --format csv) --force --verbose
