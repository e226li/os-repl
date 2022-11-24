#!/bin/bash
set -e

export DEBIAN_FRONTEND=noninteractive

sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install snapd
sudo snap install lxd

yes '' | lxd init

sudo apt-get install python3-pip
python3 -m pip install paramiko pylxd sshim
