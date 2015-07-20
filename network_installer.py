#!/usr/bin/env python

__author__ = 'mcygglez'

import os
import sys

sys.path.append(os.path.dirname(__file__))

from utils import common_tools as common
from utils import kilo_services as kilo

#Checking the script is run as the root user
if not os.getuid() == 0:
    sys.exit('This script must be run as root')

print '#######################################################################'
print '# OpenStack Kilo Network Node Installation'
print '#######################################################################'
common.log('Starting installation')
print ''

#Configuring Kernel Networking Parameters
common.set_sysctl('net.ipv4.ip_forward', '1')
common.set_sysctl('net.ipv4.conf.all.rp_filter', '0')
common.set_sysctl('net.ipv4.conf.default.rp_filter', '0')

#Installing vlan and bridge-utils
kilo.install_vlan()
kilo.install_bridgeutils()

#OpenStack Kilo Configuration File
kilo_conf = os.path.join(os.path.dirname(__file__), 'kilo.conf')

network_mgmt_ntw_interface = common.get_file_option(kilo_conf, 'network', 'management_network_interface')
network_mgmt_ntw_interface_addr = common.get_network_address(network_mgmt_ntw_interface)
network_vm_traffic_ntw_interface = common.get_file_option(kilo_conf, 'network', 'vm_traffic_network_interface')
network_vm_traffic_ntw_interface_addr = common.get_network_address(network_vm_traffic_ntw_interface)
external_network_interface = common.get_file_option(kilo_conf, 'network', 'external_network_interface')

controller_server_name = common.get_file_option(kilo_conf, 'controller', 'controller_server_name')

print ''
common.log('Using network addresses:')
print '    Network Node VM Traffic Network IP Address: ' + str(network_vm_traffic_ntw_interface_addr)


#Installing NTP Server in Network Node
kilo.install_ntp(controller_server_name, False)

#Install Neutron Network Service in Network Node
neutron_usr_password = common.get_file_option(kilo_conf, 'neutron', 'neutron_usr_password')
openstack_rabbitmq_password = common.get_file_option(kilo_conf, 'rabbitmq', 'openstack_rabbitmq_password')
metadata_secret = common.get_file_option(kilo_conf, 'neutron', 'metadata_secret')
kilo.install_neutron_network_node(controller_server_name, neutron_usr_password, openstack_rabbitmq_password, network_vm_traffic_ntw_interface_addr, metadata_secret, external_network_interface)




