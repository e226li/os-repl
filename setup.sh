#!/bin/bash
set -e

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get upgrade -y
apt-get install snapd
snap install lxd

yes '' | lxd init

apt-get install python3-pip
python3 -m pip install paramiko pylxd sshim
