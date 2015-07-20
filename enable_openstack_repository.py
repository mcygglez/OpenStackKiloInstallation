#!/usr/bin/env python

__author__ = 'mcygglez'

import os
import sys

sys.path.append(os.path.dirname(__file__))

from utils import common_tools as common
from utils import kilo_services as kilo

if not os.geteuid() == 0:
    sys.exit('This script must be run as root')

def enable_openstack_repository():
    common.log('Updating and Upgrading Operating System')
    common.run_command("apt-get -y update", True)
    common.run_command("apt-get install -y python-setuptools python-iniparse python-psutil python-software-properties")
    common.run_command("apt-get install -y ubuntu-cloud-keyring", True)
    common.delete_file("/etc/apt/sources.list.d/cloudarchive-kilo.list")
    common.run_command("echo 'deb http://ubuntu-cloud.archive.canonical.com/ubuntu trusty-updates/kilo main' >> /etc/apt/sources.list.d/cloudarchive-kilo.list")
    common.run_command("apt-get -y update", True)
    common.run_command("apt-get -y dist-upgrade", True)


if __name__ == "__main__":
    enable_openstack_repository()

