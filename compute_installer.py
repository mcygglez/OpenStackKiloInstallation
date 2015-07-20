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
print '# OpenStack Kilo Compute Node Installation'
print '#######################################################################'
common.log('Starting installation')
print ''


#Configuring Kernel Networking Parameters
common.set_sysctl('net.ipv4.ip_forward', '1')
common.set_sysctl('net.ipv4.conf.all.rp_filter', '0')
common.set_sysctl('net.ipv4.conf.default.rp_filter', '0')
#common.set_sysctl('net.bridge.bridge-nf-call-iptables', '1')
#common.set_sysctl('net.bridge.bridge-nf-call-ip6tables', '1')

#Installing vlan and bridge-utils
kilo.install_vlan()
kilo.install_bridgeutils()

#OpenStack Kilo Configuration File
kilo_conf = os.path.join(os.path.dirname(__file__), 'kilo.conf')

comp_mgmt_ntw_interface = common.get_file_option(kilo_conf, 'compute', 'management_network_interface')
comp_mgmt_ntw_interface_addr = common.get_network_address(comp_mgmt_ntw_interface)
comp_vm_traffic_ntw_interface = common.get_file_option(kilo_conf, 'compute', 'vm_traffic_network_interface')
comp_vm_traffic_ntw_interface_addr = common.get_network_address(comp_vm_traffic_ntw_interface)

ctrl_mgmt_ntw_interface_addr = common.get_file_option(kilo_conf, 'controller', 'management_network_ip')
controller_server_name = common.get_file_option(kilo_conf, 'controller', 'controller_server_name')

print ''
common.log('Using network addresses:')
print '    Compute Node Management Network IP Address: ' + str(comp_mgmt_ntw_interface_addr)
print '    Compute Node VM Traffic Network IP Address: ' + str(comp_vm_traffic_ntw_interface_addr)

#Installing NTP Server in Compute Node
kilo.install_ntp(controller_server_name, False)

#Installing Nova Compute Service in Compute Node
virt_type = 'qemu'
compute_driver = 'libvirt.LibvirtDriver'

if len(sys.argv) == 2:
    if sys.argv[1] in ['qemu', 'kvm', 'lxc']:
        virt_type = sys.argv[1]
    if sys.argv[1] == 'docker':
        virt_type = 'lxc'
        compute_driver = 'novadocker.virt.docker.DockerDriver'


openstack_rabbitmq_password = common.get_file_option(kilo_conf, 'rabbitmq', 'openstack_rabbitmq_password')
nova_usr_password = common.get_file_option(kilo_conf, 'nova', 'nova_usr_password')
kilo.install_nova_compute_node(controller_server_name, openstack_rabbitmq_password, nova_usr_password, comp_mgmt_ntw_interface_addr, virt_type, compute_driver)

#Install Neutron Network Service in Controller Node
neutron_usr_password = common.get_file_option(kilo_conf, 'neutron', 'neutron_usr_password')
openstack_rabbitmq_password = common.get_file_option(kilo_conf, 'rabbitmq', 'openstack_rabbitmq_password')
kilo.install_neutron_compute_node(controller_server_name, openstack_rabbitmq_password, neutron_usr_password, comp_vm_traffic_ntw_interface_addr)