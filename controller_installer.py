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
print '# OpenStack Kilo Controller Node Installation'
print '#######################################################################'
common.log('Starting installation')
print ''

#OpenStack Kilo Configuration File
kilo_conf = os.path.join(os.path.dirname(__file__), 'kilo.conf')

#Getting and updating Controller Node's Interface connected to Management Network/VLAN
ctrl_mgmt_ntw_interface = common.get_file_option(kilo_conf, 'controller', 'management_network_interface')
ctrl_mgmt_ntw_interface_addr = common.get_network_address(ctrl_mgmt_ntw_interface)
common.set_file_option(kilo_conf, 'controller', 'management_network_ip', ctrl_mgmt_ntw_interface_addr)

print ''
common.log('Using network addresses:')
print "    Controller Node's Interface at Management Network has IP Address: " + str(ctrl_mgmt_ntw_interface_addr)

#Installing NTP Server in Controller Node
time_server = common.get_file_option(kilo_conf, 'controller', 'time_server')
kilo.install_ntp(time_server, True)

#Installing MySQL
mysql_root_password = common.get_file_option(kilo_conf, 'mysql', 'root_password')
kilo.install_mysql(mysql_root_password)

#Installing RabbitMQ
openstack_rabbitmq_password = common.get_file_option(kilo_conf, 'rabbitmq', 'openstack_rabbitmq_password')
kilo.install_rabbitmq(openstack_rabbitmq_password)

controller_server_name = common.get_file_option(kilo_conf, 'controller', 'controller_server_name')

#Install Keystone Identity Service
keystone_db_password = common.get_file_option(kilo_conf, 'keystone', 'keystone_db_password')
admin_token = common.run_command('openssl rand -hex 10')
admin_usr_password = common.get_file_option(kilo_conf, 'keystone', 'admin_usr_password')
demo_usr_password = common.get_file_option(kilo_conf, 'keystone', 'demo_usr_password')
kilo.install_keystone(keystone_db_password, mysql_root_password, admin_token, controller_server_name, admin_usr_password, demo_usr_password)

#Install Glance Image Service
glance_db_password = common.get_file_option(kilo_conf, 'glance', 'glance_db_password')
glance_usr_password = common.get_file_option(kilo_conf, 'glance', 'glance_usr_password')
kilo.install_glance(glance_db_password, mysql_root_password, admin_token, controller_server_name, glance_usr_password)

#Install Nova Compute Service in Controller Node
nova_db_password = common.get_file_option(kilo_conf, 'nova', 'nova_db_password')
nova_usr_password = common.get_file_option(kilo_conf, 'nova', 'nova_usr_password')
neutron_usr_password = common.get_file_option(kilo_conf, 'neutron', 'neutron_usr_password')
metadata_secret = common.get_file_option(kilo_conf, 'neutron', 'metadata_secret')
kilo.install_nova_controller_node(nova_db_password, mysql_root_password, admin_token, controller_server_name, nova_usr_password, openstack_rabbitmq_password, ctrl_mgmt_ntw_interface_addr, neutron_usr_password, metadata_secret)

#Install Neutron Network Service in Controller Node
neutron_db_password = common.get_file_option(kilo_conf, 'neutron', 'neutron_db_password')
kilo.install_neutron_controller_node(neutron_db_password, mysql_root_password, admin_token, controller_server_name, neutron_usr_password, openstack_rabbitmq_password, nova_usr_password)

#Install Horizon Dashboard Service in Controller Node
kilo.install_horizon(controller_server_name)

#Install Cinder Block Storage Service in Controller Node
cinder_db_password = common.get_file_option(kilo_conf, 'cinder', 'cinder_db_password')
cinder_usr_password = common.get_file_option(kilo_conf, 'cinder', 'cinder_usr_password')
kilo.install_cinder_controller_node(cinder_db_password, mysql_root_password, admin_token, controller_server_name, cinder_usr_password, openstack_rabbitmq_password, ctrl_mgmt_ntw_interface_addr)