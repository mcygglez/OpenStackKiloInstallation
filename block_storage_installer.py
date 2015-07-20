__author__ = 'mercygglez'

import os
import sys

sys.path.append(os.path.dirname(__file__))

from utils import common_tools as common
from utils import kilo_services as kilo

#Checking the script is run as the root user
if not os.getuid() == 0:
    sys.exit('This script must be run as root')

print '#######################################################################'
print '# OpenStack Kilo Block Storage Node Installation'
print '#######################################################################'
common.log('Starting installation')
print ''

#OpenStack Kilo Configuration File
kilo_conf = os.path.join(os.path.dirname(__file__), 'kilo.conf')

controller_server_name = common.get_file_option(kilo_conf, 'controller', 'controller_server_name')

cinder_db_password = common.get_file_option(kilo_conf, 'cinder', 'cinder_db_password')
cinder_usr_password = common.get_file_option(kilo_conf, 'cinder', 'cinder_usr_password')

openstack_rabbitmq_password = common.get_file_option(kilo_conf, 'rabbitmq', 'openstack_rabbitmq_password')

bs_mgmt_ntw_interface = common.get_file_option(kilo_conf, 'block_storage', 'management_network_interface')
bs_mgmt_ntw_interface_addr = common.get_network_address(bs_mgmt_ntw_interface)

kilo.install_cinder_block_storage_node(cinder_db_password, controller_server_name, cinder_usr_password, openstack_rabbitmq_password, bs_mgmt_ntw_interface_addr)
