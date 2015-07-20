__author__ = 'mcygglez'

import os
import time

import common_tools as common


def install_ntp(time_server, is_controller_node = False):
    if not time_server or len(str(time_server)) == 0:
        raise Exception("Unable to install/configure NTP, no Time Server specified")

    print ''
    common.log('Installing NTP Server')
    common.run_command("apt-get install -y ntp", True)

    common.log('Configuring NTP Server')
    common.run_command("sed -i 's/^server 0.ubuntu.pool.ntp.org/#server 0.ubuntu.pool.ntp.org/g' /etc/ntp.conf")
    common.run_command("sed -i 's/^server 1.ubuntu.pool.ntp.org/#server 1.ubuntu.pool.ntp.org/g' /etc/ntp.conf")
    common.run_command("sed -i 's/^server 2.ubuntu.pool.ntp.org/#server 2.ubuntu.pool.ntp.org/g' /etc/ntp.conf")
    common.run_command("sed -i 's/^server 3.ubuntu.pool.ntp.org/#server 3.ubuntu.pool.ntp.org/g' /etc/ntp.conf")
    common.run_command("sed -i 's/^server .*/server %s iburst/g' /etc/ntp.conf" %time_server)

    if is_controller_node:
        common.run_command("sed -i 's/^restrict -4 default kod notrap nomodify nopeer noquery/restrict -4 default kod notrap nomodify/g' /etc/ntp.conf")
        common.run_command("sed -i 's/^restrict -6 default kod notrap nomodify nopeer noquery/restrict -6 default kod notrap nomodify/g' /etc/ntp.conf")

    common.delete_file("/var/lib/ntp/ntp.conf.dhcp")
    common.run_command("service ntp restart", True)
    time.sleep(10)
    common.log('Completed NTP Server')


def install_mysql(root_password):
    if not root_password or len(str(root_password)) == 0:
        raise Exception("Unable to install/configure MySQL, no root password specified")

    common.log('Installing MySQL Server in Controller Node')
    os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
    common.run_command("apt-get install -y mysql-server python-mysqldb", True)

    common.log('Configuring MySQL')
    common.run_command("service mysql stop || true", True)
    time.sleep(10)

    pre_configured_mysql_conf_file = os.path.join(os.path.dirname(__file__), '../mysql/my.cnf')
    mysql_conf_file = '/etc/mysql/my.cnf'
    common.run_command("cp -f " + pre_configured_mysql_conf_file + " " + mysql_conf_file)
    common.run_command("service mysql restart", True)
    time.sleep(10)

    try:
        common.run_command("mysqladmin -u root password %s" %root_password)
    except:
        common.log('MySQL root password was already set ... verifying')

    common.run_db_command(root_password, 'show databases;')
    common.log('Verified MySQL root password')
    common.log('Completed MySQL')

def install_rabbitmq(openstack_rabbitmq_password):
    if not openstack_rabbitmq_password or len(str(openstack_rabbitmq_password)) == 0:
        raise("Unable to install/configure RabbitMQ Server, no password specified for rabbitmq user")

    print ''
    common.log('Installing RabbitMQ Server in Controller Node')
    common.run_command("apt-get install -y rabbitmq-server", True)

    common.log('Configuring RabbitMQ Server')
    common.run_command("rabbitmqctl add_user openstack %s" %openstack_rabbitmq_password)
    common.run_command("rabbitmqctl set_user_tags openstack administrator")
    common.run_command("rabbitmqctl set_permissions -p / openstack '.*' '.*' '.*'")

    common.run_command("rabbitmq-plugins enable rabbitmq_management", True)
    common.run_command("service rabbitmq-server restart", True)
    time.sleep(10)
    common.log('Completed RabbitMQ')

def install_keystone(keystone_db_password, mysql_root_password, admin_token, controller_server_name, admin_usr_password, demo_usr_password):
    if not keystone_db_password or len(str(keystone_db_password)) == 0:
        raise Exception("Unable to install/configure Keystone Identity Service, no keystone database password specified")
    if not mysql_root_password or len(str(mysql_root_password)) == 0:
        raise Exception("Unable to install/configure Keystone Identity Service, no MySQL password specified")
    if not admin_token or len(str(admin_token)) == 0:
        raise Exception("Unable to install/configure Keystone Identity Service, no admin token specified")
    if not controller_server_name or len(str(controller_server_name)) == 0:
        raise Exception("Unable to install/configure Keystone Identity Service, no controller server name specified")
    if not admin_usr_password or len(str(admin_usr_password)) == 0:
        raise Exception("Unable to install/configure Keystone Identity Service, no admin user password specified")
    if not demo_usr_password or len(str(demo_usr_password)) == 0:
        raise Exception("Unable to install/configure Keystone Identity Service, no demo user password specified")

    print ''
    common.log('Installing Keystone Service in Controller Node')
    common.run_db_command(mysql_root_password, "CREATE DATABASE IF NOT EXISTS keystone CHARACTER SET utf8 COLLATE utf8_general_ci;")
    common.run_db_command(mysql_root_password, "GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'localhost' IDENTIFIED BY '" + keystone_db_password + "';")
    common.run_db_command(mysql_root_password, "GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'%' IDENTIFIED BY '" + keystone_db_password + "';")

    #Disabling Keystone from starting automatically after installation (Apache is going to be configure to listen on ports 5000 and 35357, not Keystone)
    common.run_command("echo 'manual' > /etc/init/keystone.override")
    common.run_command("apt-get install -y keystone python-openstackclient apache2 libapache2-mod-wsgi memcached python-memcache", True)

    common.log('Configuring Keystone Service in Controller Node')
    keystone_conf_file = '/etc/keystone/keystone.conf'
    common.set_file_option(keystone_conf_file, 'DEFAULT', 'admin_token', admin_token)
    common.set_file_option(keystone_conf_file, 'DEFAULT', 'verbose', 'true')
    common.set_file_option(keystone_conf_file, 'database', 'connection', "mysql://keystone:%s@%s/keystone" %(keystone_db_password, controller_server_name))
    common.set_file_option(keystone_conf_file, 'memcache', 'servers', 'localhost:11211')
    common.set_file_option(keystone_conf_file, 'token', 'provider', 'keystone.token.providers.uuid.Provider')
    common.set_file_option(keystone_conf_file, 'token', 'driver', 'keystone.token.persistence.backends.memcache.Token')
    common.set_file_option(keystone_conf_file, 'revoke', 'driver', 'keystone.contrib.revoke.backends.sql.Revoke')

    common.run_command("su -s /bin/sh -c 'keystone-manage db_sync' keystone", True)

    #Configuring Apache Server
    common.run_command("echo 'ServerName %s' >> /etc/apache2/apache2.conf" %controller_server_name)
    wsgi_keystone_conf_file = ' /etc/apache2/sites-available/wsgi-keystone.conf'
    pre_configured_wsgi_keystone_conf_file = os.path.join(os.path.dirname(__file__), '../apache2/wsgi-keystone.conf')
    common.run_command("cp -f " + pre_configured_wsgi_keystone_conf_file + " " + wsgi_keystone_conf_file)
    common.delete_file("/etc/apache2/sites-enabled/000-default.conf")
    common.run_command("ln -s /etc/apache2/sites-available/wsgi-keystone.conf /etc/apache2/sites-enabled")
    common.run_command("mkdir -p /var/www/cgi-bin/keystone")
    common.run_command("curl http://git.openstack.org/cgit/openstack/keystone/plain/httpd/keystone.py?h=stable/kilo | tee /var/www/cgi-bin/keystone/main /var/www/cgi-bin/keystone/admin", True)
    common.run_command("chown -R keystone:keystone /var/www/cgi-bin/keystone")
    common.run_command("chmod 755 /var/www/cgi-bin/keystone/*")

    common.run_command("service apache2 restart")
    time.sleep(10)
    common.delete_file('/var/lib/keystone/keystone.db')

    os.environ['OS_TOKEN'] = admin_token
    os.environ['OS_URL'] = 'http://%s:35357/v2.0' %controller_server_name

    adminrc = '/root/admin-openrc.sh'
    common.run_command("echo 'export OS_PROJECT_DOMAIN_ID=default' > %s" %adminrc)
    common.run_command("echo 'export OS_USER_DOMAIN_ID=default' >> %s" %adminrc)
    common.run_command("echo 'export OS_PROJECT_NAME=admin' >> %s" %adminrc)
    common.run_command("echo 'export OS_TENANT_NAME=admin' >> %s" %adminrc)
    common.run_command("echo 'export OS_USERNAME=admin' >> %s" %adminrc)
    common.run_command("echo 'export OS_PASSWORD=%s' >> %s" %(admin_usr_password, adminrc))
    common.run_command("echo 'export OS_AUTH_URL=http://%s:35357/v3' >> %s" % (controller_server_name, adminrc))

    demorc = '/root/demo-openrc.sh'
    common.run_command("echo 'export OS_PROJECT_DOMAIN_ID=default' > %s" %demorc)
    common.run_command("echo 'export OS_USER_DOMAIN_ID=default' >> %s" %demorc)
    common.run_command("echo 'export OS_PROJECT_NAME=demo' >> %s" %demorc)
    common.run_command("echo 'export OS_TENANT_NAME=demo' >> %s" %demorc)
    common.run_command("echo 'export OS_USERNAME=demo' >> %s" %demorc)
    common.run_command("echo 'export OS_PASSWORD=%s' >> %s" %(demo_usr_password, demorc))
    common.run_command("echo 'export OS_AUTH_URL=http://%s:5000/v3' >> %s" % (controller_server_name, demorc))

    # Creating admin Project, admin User, admin Role and mapping admin User to admin Project and admin Role
    common.run_command("openstack project create --description 'Admin Project' admin")
    common.run_command("openstack user create --password %s admin" %admin_usr_password)
    common.run_command("openstack role create admin")
    common.run_command("openstack role add --project admin --user admin admin")

    # Creating demo Project, demo User, user Role and mapping demo User to demo Project and user Role
    common.run_command("openstack project create --description 'Demo Project' demo")
    common.run_command("openstack user create --password %s demo" %demo_usr_password)
    common.run_command("openstack role create user")
    common.run_command("openstack role add --project demo --user demo user")

    # Creating service Project
    common.run_command("openstack project create --description 'Service Project' service")

    # Creating Keystone Service and Keystone Endpoints
    common.run_command("openstack service create --name keystone --description 'OpenStack Identity Service' identity")
    common.run_command("openstack endpoint create --publicurl http://%s:5000/v2.0 --internalurl http://%s:5000/v2.0 --adminurl http://%s:35357/v2.0 --region Westeros identity" %(controller_server_name, controller_server_name, controller_server_name))

    common.log('Completed Keystone Identity Service')

def install_glance(glance_db_password, mysql_root_password, admin_token, controller_server_name, glance_usr_password):
    if not glance_db_password or len(str(glance_db_password)) == 0:
        raise Exception("Unable to install/configure Glance Image Service, no glance database password specified")
    if not mysql_root_password or len(str(mysql_root_password)) == 0:
        raise Exception("Unable to install/configure Glance Image Service, no MySQL password specified")
    if not admin_token or len(str(admin_token)) == 0:
        raise Exception("Unable to install/configure Keystone Identity Service, no admin token specified")
    if not controller_server_name or len(str(controller_server_name)) == 0:
        raise Exception("Unable to install/configure Glance Image Service, no controller server name specified")
    if not glance_usr_password or len(str(glance_usr_password)) == 0:
        raise Exception("Unable to install/configure Glance Image Service, no glance user password specified")

    print ''
    common.log('Installing Glance Image Service in Controller Node')

    common.run_db_command(mysql_root_password, "CREATE DATABASE IF NOT EXISTS glance CHARACTER SET utf8 COLLATE utf8_general_ci;")
    common.run_db_command(mysql_root_password, "GRANT ALL PRIVILEGES ON glance.* TO 'glance'@'localhost' IDENTIFIED BY '" + glance_db_password + "';")
    common.run_db_command(mysql_root_password, "GRANT ALL PRIVILEGES ON glance.* TO 'glance'@'%' IDENTIFIED BY '" + glance_db_password + "';")

    common.log('Registering Glance Image Service in Keystone')
    os.environ['OS_TOKEN'] = admin_token
    os.environ['OS_URL'] = 'http://%s:35357/v2.0' %controller_server_name

    common.run_command("openstack user create --password %s glance" %glance_usr_password)
    common.run_command("openstack role add --project service --user glance admin")
    common.run_command("openstack service create --name glance --description 'OpenStack Image Service' image")
    common.run_command("openstack endpoint create --publicurl http://%s:9292 --internalurl http://%s:9292 --adminurl http://%s:9292 --region Westeros image" %(controller_server_name, controller_server_name, controller_server_name))

    common.run_command("apt-get install -y glance python-glanceclient", True)

    common.log('Configuring Glance Image Service')

    glance_api_conf_file = '/etc/glance/glance-api.conf'
    common.set_file_option(glance_api_conf_file, 'database', 'connection', "mysql://glance:%s@%s/glance" %(glance_db_password, controller_server_name))
    common.set_file_option(glance_api_conf_file, 'keystone_authtoken', 'auth_uri', "http://%s:5000" %controller_server_name)
    common.set_file_option(glance_api_conf_file, 'keystone_authtoken', 'auth_url', "http://%s:35357" %controller_server_name)
    common.set_file_option(glance_api_conf_file, 'keystone_authtoken', 'auth_plugin', 'password')
    common.set_file_option(glance_api_conf_file, 'keystone_authtoken', 'project_domain_id', 'default')
    common.set_file_option(glance_api_conf_file, 'keystone_authtoken', 'user_domain_id', 'default')
    common.set_file_option(glance_api_conf_file, 'keystone_authtoken', 'project_name', 'service')
    common.set_file_option(glance_api_conf_file, 'keystone_authtoken', 'username', 'glance')
    common.set_file_option(glance_api_conf_file, 'keystone_authtoken', 'password', glance_usr_password)
    common.set_file_option(glance_api_conf_file, 'paste_deploy', 'flavor', 'keystone')
    common.set_file_option(glance_api_conf_file, 'glance_store', 'default_store', 'file')
    common.set_file_option(glance_api_conf_file, 'glance_store', 'filesystem_store_datadir', '/var/lib/glance/images/')
    common.set_file_option(glance_api_conf_file, 'DEFAULT', 'notification_driver', 'noop')
    common.set_file_option(glance_api_conf_file, 'DEFAULT', 'verbose', 'True')
    common.set_file_option(glance_api_conf_file, 'DEFAULT', 'container_formats', 'ami,ari,aki,bare,ovf,docker')

    common.remove_file_option(glance_api_conf_file, 'database', 'sqlite_db')
    common.remove_file_option(glance_api_conf_file, 'keystone_authtoken', 'identity_uri')
    common.remove_file_option(glance_api_conf_file, 'keystone_authtoken', 'admin_tenant_name')
    common.remove_file_option(glance_api_conf_file, 'keystone_authtoken', 'admin_user')
    common.remove_file_option(glance_api_conf_file, 'keystone_authtoken', 'admin_password')


    glance_registry_conf_file = '/etc/glance/glance-registry.conf'
    common.set_file_option(glance_registry_conf_file, 'database', 'connection', "mysql://glance:%s@%s/glance" %(glance_db_password, controller_server_name))
    common.set_file_option(glance_registry_conf_file, 'keystone_authtoken', 'auth_uri', "http://%s:5000" %controller_server_name)
    common.set_file_option(glance_registry_conf_file, 'keystone_authtoken', 'auth_url', "http://%s:35357" %controller_server_name)
    common.set_file_option(glance_registry_conf_file, 'keystone_authtoken', 'auth_plugin', 'password')
    common.set_file_option(glance_registry_conf_file, 'keystone_authtoken', 'project_domain_id', 'default')
    common.set_file_option(glance_registry_conf_file, 'keystone_authtoken', 'user_domain_id', 'default')
    common.set_file_option(glance_registry_conf_file, 'keystone_authtoken', 'project_name', 'service')
    common.set_file_option(glance_registry_conf_file, 'keystone_authtoken', 'username', 'glance')
    common.set_file_option(glance_registry_conf_file, 'keystone_authtoken', 'password', glance_usr_password)
    common.set_file_option(glance_registry_conf_file, 'paste_deploy', 'flavor', 'keystone')
    common.set_file_option(glance_registry_conf_file, 'DEFAULT', 'notification_driver', 'noop')
    common.set_file_option(glance_registry_conf_file, 'DEFAULT', 'verbose', 'True')

    common.remove_file_option(glance_registry_conf_file, 'database', 'sqlite_db')
    common.remove_file_option(glance_registry_conf_file, 'keystone_authtoken', 'identity_uri')
    common.remove_file_option(glance_registry_conf_file, 'keystone_authtoken', 'admin_tenant_name')
    common.remove_file_option(glance_registry_conf_file, 'keystone_authtoken', 'admin_user')
    common.remove_file_option(glance_registry_conf_file, 'keystone_authtoken', 'admin_password')

    common.run_command("su -s /bin/sh -c 'glance-manage db_sync' glance", True)

    common.run_command("service glance-registry restart", True)
    common.run_command("service glance-api restart", True)
    time.sleep(10)
    common.delete_file('/var/lib/glance/glance.sqlite')
    common.run_command("echo 'export OS_IMAGE_API_VERSION=2' | tee -a admin-openrc.sh demo-openrc.sh")

    common.log('Completed Glance Image Service')

def install_nova_controller_node(nova_db_password, mysql_root_password, admin_token, controller_server_name, nova_usr_password, openstack_rabbitmq_password, ctrl_mgmt_ntw_interface_addr, neutron_usr_password, metadata_secret):
    if not nova_db_password or len(str(nova_db_password)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no nova database password specified")
    if not mysql_root_password or len(str(mysql_root_password)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no MySQL password specified")
    if not admin_token or len(str(admin_token)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no admin token specified")
    if not controller_server_name or len(str(controller_server_name)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no controller server name specified")
    if not nova_usr_password or len(str(nova_usr_password)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no nova user password specified")
    if not openstack_rabbitmq_password or len(str(openstack_rabbitmq_password)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no openstack rabbit password specified")
    if not ctrl_mgmt_ntw_interface_addr or len(str(ctrl_mgmt_ntw_interface_addr)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no controller management interface ip address specified")
    if not neutron_usr_password or len(str(neutron_usr_password)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no neutron user password specified")
    if not metadata_secret or len(str(metadata_secret)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no metadata secret specified")

    print ''
    common.log('Installing Nova Compute Service in Controller Node')

    common.run_db_command(mysql_root_password, "CREATE DATABASE IF NOT EXISTS nova CHARACTER SET utf8 COLLATE utf8_general_ci;")
    common.run_db_command(mysql_root_password, "GRANT ALL PRIVILEGES ON nova.* TO 'nova'@'localhost' IDENTIFIED BY '" + nova_db_password + "';")
    common.run_db_command(mysql_root_password, "GRANT ALL PRIVILEGES ON nova.* TO 'nova'@'%' IDENTIFIED BY '" + nova_db_password + "';")

    common.log('Registering Nova Compute Service in Keystone')
    os.environ['OS_TOKEN'] = admin_token
    os.environ['OS_URL'] = 'http://%s:35357/v2.0' %controller_server_name

    common.run_command("openstack user create --password %s nova" %nova_usr_password)
    common.run_command("openstack role add --project service --user nova admin")
    common.run_command("openstack service create --name nova --description 'OpenStack Compute Service' compute")
    common.run_command("openstack endpoint create --publicurl http://" + controller_server_name + ":8774/v2/%\(tenant_id\)s --internalurl http://" + controller_server_name + ":8774/v2/%\(tenant_id\)s --adminurl http://" + controller_server_name + ":8774/v2/%\(tenant_id\)s --region Westeros compute")

    common.run_command("apt-get install -y nova-api nova-cert nova-conductor nova-consoleauth nova-novncproxy nova-scheduler python-novaclient", True)

    common.log('Configuring Nova Compute Service in Controller Node')
    nova_conf_file = '/etc/nova/nova.conf'
    common.set_file_option(nova_conf_file, 'database', 'connection', "mysql://nova:%s@%s/nova" %(nova_db_password, controller_server_name))
    common.set_file_option(nova_conf_file, 'DEFAULT', 'rpc_backend', 'rabbit')
    common.set_file_option(nova_conf_file, 'oslo_messaging_rabbit', 'rabbit_host', controller_server_name)
    common.set_file_option(nova_conf_file, 'oslo_messaging_rabbit', 'rabbit_userid', 'openstack')
    common.set_file_option(nova_conf_file, 'oslo_messaging_rabbit', 'rabbit_password', openstack_rabbitmq_password)
    common.set_file_option(nova_conf_file, 'DEFAULT', 'auth_strategy', 'keystone')
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'auth_uri', "http://%s:5000" %controller_server_name)
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'auth_url', "http://%s:35357" %controller_server_name)
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'auth_plugin', 'password')
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'project_domain_id', 'default')
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'user_domain_id', 'default')
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'project_name', 'service')
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'username', 'nova')
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'password', nova_usr_password)
    common.set_file_option(nova_conf_file, 'DEFAULT', 'my_ip', ctrl_mgmt_ntw_interface_addr)
    common.set_file_option(nova_conf_file, 'DEFAULT', 'vncserver_listen', ctrl_mgmt_ntw_interface_addr)
    common.set_file_option(nova_conf_file, 'DEFAULT', 'vncserver_proxyclient_address', ctrl_mgmt_ntw_interface_addr)
    common.set_file_option(nova_conf_file, 'glance', 'host', controller_server_name)
    common.set_file_option(nova_conf_file, 'oslo_concurrency', 'lock_path', '/var/lib/nova/tmp')
    common.set_file_option(nova_conf_file, 'DEFAULT', 'verbose', True)
    # Configuring Nova to use Neutron Networking
    common.set_file_option(nova_conf_file, 'DEFAULT', 'network_api_class', 'nova.network.neutronv2.api.API')
    common.set_file_option(nova_conf_file, 'DEFAULT', 'security_group_api', 'neutron')
    common.set_file_option(nova_conf_file, 'DEFAULT', 'linuxnet_interface_driver', 'nova.network.linux_net.LinuxOVSInterfaceDriver')
    common.set_file_option(nova_conf_file, 'DEFAULT', 'firewall_driver', 'nova.virt.firewall.NoopFirewallDriver')
    common.set_file_option(nova_conf_file, 'neutron', 'url', "http://%s:9696" %controller_server_name)
    common.set_file_option(nova_conf_file, 'neutron', 'auth_strategy', 'keystone')
    common.set_file_option(nova_conf_file, 'neutron', 'admin_auth_url', "http://%s:35357/v2.0" %controller_server_name)
    common.set_file_option(nova_conf_file, 'neutron', 'admin_tenant_name', 'service')
    common.set_file_option(nova_conf_file, 'neutron', 'admin_username', 'neutron')
    common.set_file_option(nova_conf_file, 'neutron', 'admin_password', neutron_usr_password)
    # Configuring Metadata Service
    common.set_file_option(nova_conf_file, 'neutron', 'service_metadata_proxy', True)
    common.set_file_option(nova_conf_file, 'neutron', 'metadata_proxy_shared_secret', metadata_secret)

    common.run_command("su -s /bin/sh -c 'nova-manage db sync' nova", True)

    common.run_command("service nova-api restart", True)
    common.run_command("service nova-cert restart", True)
    common.run_command("service nova-consoleauth restart", True)
    common.run_command("service nova-scheduler restart", True)
    common.run_command("service nova-conductor restart", True)
    common.run_command("service nova-novncproxy restart", True)
    time.sleep(10)

    common.delete_file("/var/lib/nova/nova.sqlite")

    common.log('Completed Nova Compute Service in Controller Node')

def install_nova_compute_node(controller_server_name, openstack_rabbitmq_password, nova_usr_password, comp_mgmt_ntw_interface_addr, virt_type, compute_driver):
    if not controller_server_name or len(str(controller_server_name)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no controller server name specified")
    if not openstack_rabbitmq_password or len(str(openstack_rabbitmq_password)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no openstack rabbit password specified")
    if not nova_usr_password or len(str(nova_usr_password)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no nova user password specified")
    if not comp_mgmt_ntw_interface_addr or len(str(comp_mgmt_ntw_interface_addr)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no controller management interface ip address specified")
    if not virt_type or len(str(virt_type)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no hypervisor type specified")
    if not compute_driver or len(str(compute_driver)) == 0:
        raise Exception("Unable to install/configure Nova Compute Service, no compute driver specified")


    print ''
    common.log('Installing Nova Compute Service on Compute Node')

    os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
    common.run_command("apt-get install -y nova-compute sysfsutils", True)
    common.run_command("apt-get install -y qemu qemu-kvm libvirt-bin", True)
    common.run_command("apt-get install -y libguestfs-tools", True)
    common.run_command("apt-get install -y git git-review python-pip python-dev", True)

    if virt_type == 'lxc':
        common.run_command("apt-get install -y lxc nova-compute-lxc", True)

    if compute_driver == 'novadocker.virt.docker.DockerDriver':
        common.run_command("wget -qO- https://get.docker.com/ | sh", True)
        common.run_command("usermod -G docker nova", True)
        common.run_command("git clone -b stable/kilo https://github.com/stackforge/nova-docker.git", True)
        old_dir = os.getcwd()
        os.chdir("./nova-docker")
        common.run_command("python setup.py install", True)
        os.chdir(old_dir)
        common.run_command("chmod 666 /var/run/docker.sock")
        common.run_command("chmod 777 /var/run/libvirt/libvirt-sock")

    common.log('Configuring Nova Compute Service on Compute Node')
    nova_conf_file = '/etc/nova/nova.conf'
    common.set_file_option(nova_conf_file, 'DEFAULT', 'rpc_backend', 'rabbit')
    common.set_file_option(nova_conf_file, 'oslo_messaging_rabbit', 'rabbit_host', controller_server_name)
    common.set_file_option(nova_conf_file, 'oslo_messaging_rabbit', 'rabbit_userid', 'openstack')
    common.set_file_option(nova_conf_file, 'oslo_messaging_rabbit', 'rabbit_password', openstack_rabbitmq_password)
    common.set_file_option(nova_conf_file, 'DEFAULT', 'auth_strategy', 'keystone')
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'auth_uri', "http://%s:5000" %controller_server_name)
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'auth_url', "http://%s:35357" %controller_server_name)
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'auth_plugin', 'password')
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'project_domain_id', 'default')
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'user_domain_id', 'default')
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'project_name', 'service')
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'username', 'nova')
    common.set_file_option(nova_conf_file, 'keystone_authtoken', 'password', nova_usr_password)
    common.set_file_option(nova_conf_file, 'DEFAULT', 'my_ip', comp_mgmt_ntw_interface_addr)
    common.set_file_option(nova_conf_file, 'DEFAULT', 'vnc_enabled', True)
    common.set_file_option(nova_conf_file, 'DEFAULT', 'vncserver_listen', '0.0.0.0')
    common.set_file_option(nova_conf_file, 'DEFAULT', 'vncserver_proxyclient_address', comp_mgmt_ntw_interface_addr)
    common.set_file_option(nova_conf_file, 'DEFAULT', 'novncproxy_base_url', "http://%s:6080/vnc_auto.html" %controller_server_name)
    common.set_file_option(nova_conf_file, 'glance', 'host', controller_server_name)
    common.set_file_option(nova_conf_file, 'oslo_concurrency', 'lock_path', '/var/lib/nova/tmp')
    common.set_file_option(nova_conf_file, 'DEFAULT', 'verbose', True)
    common.set_file_option(nova_conf_file, 'DEFAULT', 'compute_driver', compute_driver)
    common.set_file_option(nova_conf_file, 'libvirt', 'virt_type', virt_type)

    nova_compute_conf_file = '/etc/nova/nova-compute.conf'
    common.set_file_option(nova_compute_conf_file, 'DEFAULT', 'compute_driver', compute_driver)
    common.set_file_option(nova_compute_conf_file, 'libvirt', 'virt_type', virt_type)

    if virt_type == 'qemu':
        driver_file = '/usr/lib/python2.7/dist-packages/nova/virt/libvirt/driver.py'
        my_driver_file = os.path.join(os.path.dirname(__file__), '../qemu/driver.py')
        common.run_command("cp -f " + my_driver_file + " " + driver_file)
    elif virt_type == 'lxc' and compute_driver == 'libvirt.LibvirtDriver':
        virt_disk_api_file = '/usr/lib/python2.7/dist-packages/nova/virt/disk/api.py'
        my_virt_disk_api_file = os.path.join(os.path.dirname(__file__), '../lxc/api.py')
        common.run_command("cp -f " + my_virt_disk_api_file + " " + virt_disk_api_file)
    elif compute_driver == 'novadocker.virt.docker.DockerDriver':
        common.run_command("cp nova-docker/etc/nova/rootwrap.d/docker.filters /etc/nova/rootwrap.d/")

    common.run_command("sed -i 's/^filter = [ \"a/.*/\" ]/filter = [ \"a/sda/\", \"r/.*/\"]/g' /etc/lvm/lvm.conf")

    common.run_command("service nova-compute restart", True)
    time.sleep(10)

    common.delete_file('/var/lib/nova/nova.sqlite')
    common.log('Completed Nova Compute Service on Compute Node')

def install_neutron_controller_node(neutron_db_password, mysql_root_password, admin_token, controller_server_name, neutron_usr_password, openstack_rabbitmq_password, nova_usr_password):
    if not neutron_db_password or len(str(neutron_db_password)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no neutron database password specified")
    if not mysql_root_password or len(str(mysql_root_password)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no MySQL password specified")
    if not admin_token or len(str(admin_token)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no admin token specified")
    if not controller_server_name or len(str(controller_server_name)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no controller server name specified")
    if not neutron_usr_password or len(str(neutron_usr_password)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no neutron user password specified")
    if not openstack_rabbitmq_password or len(str(openstack_rabbitmq_password)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no openstack rabbit password specified")
    if not nova_usr_password or len(str(nova_usr_password)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no nova user password specified")

    print ''
    common.log('Installing Neutron Networking Service in Controller Node')

    common.run_db_command(mysql_root_password, "CREATE DATABASE IF NOT EXISTS neutron CHARACTER SET utf8 COLLATE utf8_general_ci;")
    common.run_db_command(mysql_root_password, "GRANT ALL PRIVILEGES ON neutron.* TO 'neutron'@'localhost' IDENTIFIED BY '" + neutron_db_password + "';")
    common.run_db_command(mysql_root_password, "GRANT ALL PRIVILEGES ON neutron.* TO 'neutron'@'%' IDENTIFIED BY '" + neutron_db_password + "';")

    common.log('Registering Neutron Networking Service in Keystone')
    os.environ['OS_TOKEN'] = admin_token
    os.environ['OS_URL'] = 'http://%s:35357/v2.0' %controller_server_name

    common.run_command("openstack user create --password %s neutron" %neutron_usr_password)
    common.run_command("openstack role add --project service --user neutron admin")
    common.run_command("openstack service create --name neutron --description 'OpenStack Networking Service' network")
    common.run_command("openstack endpoint create --publicurl http://%s:9696 --adminurl http://%s:9696 --internalurl http://%s:9696 --region Westeros network" %(controller_server_name, controller_server_name, controller_server_name))

    common.run_command("apt-get install -y neutron-server neutron-plugin-ml2 python-neutronclient", True)

    common.log('Configuring Neutron Networking Service in Controller Node')
    neutron_conf_file = '/etc/neutron/neutron.conf'
    common.set_file_option(neutron_conf_file, 'database', 'connection', "mysql://neutron:%s@%s/neutron" %(neutron_db_password, controller_server_name))
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'rpc_backend', 'rabbit')
    common.set_file_option(neutron_conf_file, 'oslo_messaging_rabbit', 'rabbit_host', controller_server_name)
    common.set_file_option(neutron_conf_file, 'oslo_messaging_rabbit', 'rabbit_userid', 'openstack')
    common.set_file_option(neutron_conf_file, 'oslo_messaging_rabbit', 'rabbit_password', openstack_rabbitmq_password)
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'auth_strategy', 'keystone')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'auth_uri', "http://%s:5000" %controller_server_name)
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'auth_url', "http://%s:35357" %controller_server_name)
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'auth_plugin', 'password')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'project_domain_id', 'default')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'user_domain_id', 'default')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'project_name', 'service')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'username', 'neutron')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'password', neutron_usr_password)
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'core_plugin', 'ml2')
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'service_plugins', 'router')
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'allow_overlapping_ips', True)
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'notify_nova_on_port_status_changes', True)
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'notify_nova_on_port_data_changes', True)
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'nova_url', "http://%s:8774/v2" %controller_server_name)
    common.set_file_option(neutron_conf_file, 'nova', 'auth_url', "http://%s:35357" %controller_server_name)
    common.set_file_option(neutron_conf_file, 'nova', 'auth_plugin', 'password')
    common.set_file_option(neutron_conf_file, 'nova', 'project_domain_id', 'default')
    common.set_file_option(neutron_conf_file, 'nova', 'user_domain_id', 'default')
    common.set_file_option(neutron_conf_file, 'nova', 'region_name', 'Westeros')
    common.set_file_option(neutron_conf_file, 'nova', 'project_name', 'service')
    common.set_file_option(neutron_conf_file, 'nova', 'username', 'nova')
    common.set_file_option(neutron_conf_file, 'nova', 'password', nova_usr_password)
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'verbose', True)

    ml2_plugin_conf_file = '/etc/neutron/plugins/ml2/ml2_conf.ini'
    common.set_file_option(ml2_plugin_conf_file, 'ml2', 'type_drivers', 'flat,vlan,gre,vxlan')
    common.set_file_option(ml2_plugin_conf_file, 'ml2', 'tenant_network_types', 'gre')
    common.set_file_option(ml2_plugin_conf_file, 'ml2', 'mechanism_drivers', 'openvswitch')
    common.set_file_option(ml2_plugin_conf_file, 'ml2_type_gre', 'tunnel_id_ranges', '1:1000')
    common.set_file_option(ml2_plugin_conf_file, 'securitygroup', 'enable_security_group', True)
    common.set_file_option(ml2_plugin_conf_file, 'securitygroup', 'enable_ipset', True)
    common.set_file_option(ml2_plugin_conf_file, 'securitygroup', 'firewall_driver', 'neutron.agent.linux.iptables_firewall.OVSHybridIptablesFirewallDriver')

    common.run_command("su -s /bin/sh -c 'neutron-db-manage --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/ml2/ml2_conf.ini upgrade head' neutron", True)

    common.run_command("service neutron-server restart", True)
    time.sleep(10)

    common.log('Completed Neutron Networking Service in Controller Node')

def install_bridgeutils():
    print ''
    common.log('Installing bridge-utils')
    common.run_command("apt-get install -y bridge-utils", True)
    common.log('Completed bridge-utils')

def install_vlan():
    print ''
    common.log('Installing vlan')
    common.run_command("apt-get install -y vlan", True)
    common.log('Completed vlan')

def install_neutron_network_node(controller_server_name, neutron_usr_password, openstack_rabbitmq_password, network_vm_traffic_ntw_interface_addr, metadata_secret, external_network_interface):
    if not controller_server_name or len(str(controller_server_name)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no controller server name specified")
    if not neutron_usr_password or len(str(neutron_usr_password)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no neutron user password specified")
    if not openstack_rabbitmq_password or len(str(openstack_rabbitmq_password)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no openstack rabbit password specified")
    if not network_vm_traffic_ntw_interface_addr or len(str(network_vm_traffic_ntw_interface_addr)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no network vm traffic interface ip address specified")
    if not metadata_secret or len(str(metadata_secret)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no metadata secret specified")
    if not external_network_interface or len(str(external_network_interface)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no external network interface specified")


    print ''
    common.log('Installing Neutron Networking Service in Network Node')

    common.run_command('apt-get install -y neutron-plugin-ml2 neutron-plugin-openvswitch-agent neutron-l3-agent neutron-dhcp-agent neutron-metadata-agent', True)

    common.log('Configuring Neutron Networking Service in Controller Node')
    neutron_conf_file = '/etc/neutron/neutron.conf'
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'rpc_backend', 'rabbit')
    common.set_file_option(neutron_conf_file, 'oslo_messaging_rabbit', 'rabbit_host', controller_server_name)
    common.set_file_option(neutron_conf_file, 'oslo_messaging_rabbit', 'rabbit_userid', 'openstack')
    common.set_file_option(neutron_conf_file, 'oslo_messaging_rabbit', 'rabbit_password', openstack_rabbitmq_password)
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'auth_strategy', 'keystone')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'auth_uri', "http://%s:5000" %controller_server_name)
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'auth_url', "http://%s:35357" %controller_server_name)
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'auth_plugin', 'password')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'project_domain_id', 'default')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'user_domain_id', 'default')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'project_name', 'service')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'username', 'neutron')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'password', neutron_usr_password)
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'core_plugin', 'ml2')
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'service_plugins', 'router')
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'allow_overlapping_ips', True)
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'verbose', True)

    ml2_plugin_conf_file = '/etc/neutron/plugins/ml2/ml2_conf.ini'
    common.set_file_option(ml2_plugin_conf_file, 'ml2', 'type_drivers', 'flat,vlan,gre,vxlan')
    common.set_file_option(ml2_plugin_conf_file, 'ml2', 'tenant_network_types', 'gre')
    common.set_file_option(ml2_plugin_conf_file, 'ml2', 'mechanism_drivers', 'openvswitch')
    common.set_file_option(ml2_plugin_conf_file, 'ml2_type_flat', 'flat_networks', 'external')
    common.set_file_option(ml2_plugin_conf_file, 'ml2_type_gre', 'tunnel_id_ranges', '1:1000')
    common.set_file_option(ml2_plugin_conf_file, 'securitygroup', 'enable_security_group', True)
    common.set_file_option(ml2_plugin_conf_file, 'securitygroup', 'enable_ipset', True)
    common.set_file_option(ml2_plugin_conf_file, 'securitygroup', 'firewall_driver', 'neutron.agent.linux.iptables_firewall.OVSHybridIptablesFirewallDriver')
    common.set_file_option(ml2_plugin_conf_file, 'ovs', 'local_ip', network_vm_traffic_ntw_interface_addr)
    common.set_file_option(ml2_plugin_conf_file, 'ovs', 'bridge_mappings', 'external:br-ex')
    common.set_file_option(ml2_plugin_conf_file, 'agent', 'tunnel_types', 'gre')

    l3_agent_conf_file = '/etc/neutron/l3_agent.ini'
    common.set_file_option(l3_agent_conf_file, 'DEFAULT', 'interface_driver', 'neutron.agent.linux.interface.OVSInterfaceDriver')
    common.set_file_option(l3_agent_conf_file, 'DEFAULT', 'use_namespaces', True)
    common.set_file_option(l3_agent_conf_file, 'DEFAULT', 'external_network_bridge', 'br-ex')
    common.set_file_option(l3_agent_conf_file, 'DEFAULT', 'router_delete_namespaces', True)
    common.set_file_option(l3_agent_conf_file, 'DEFAULT', 'verbose', True)

    dhcp_agent_conf_file = '/etc/neutron/dhcp_agent.ini'
    common.set_file_option(dhcp_agent_conf_file, 'DEFAULT', 'interface_driver', 'neutron.agent.linux.interface.OVSInterfaceDriver')
    common.set_file_option(dhcp_agent_conf_file, 'DEFAULT', 'dhcp_driver', 'neutron.agent.linux.dhcp.Dnsmasq')
    common.set_file_option(dhcp_agent_conf_file, 'DEFAULT', 'dhcp_delete_namespaces', True)
    common.set_file_option(dhcp_agent_conf_file, 'DEFAULT', 'verbose', True)

    #Adjusting MTU
    common.set_file_option(dhcp_agent_conf_file, 'DEFAULT', 'dnsmasq_config_file', '/etc/neutron/dnsmasq-neutron.conf')
    common.run_command('touch /etc/neutron/dnsmasq-neutron.conf')
    common.run_command("echo 'dhcp-option-force=26,1454' >> /etc/neutron/dnsmasq-neutron.conf")
    #common.run_command('pkill dnsmasq')

    metadata_agent_conf_file = '/etc/neutron/metadata_agent.ini'
    common.set_file_option(metadata_agent_conf_file, 'DEFAULT', 'auth_uri', "http://%s:5000" %controller_server_name)
    common.set_file_option(metadata_agent_conf_file, 'DEFAULT', 'auth_url', "http://%s:35357" %controller_server_name)
    common.set_file_option(metadata_agent_conf_file, 'DEFAULT', 'auth_region', 'Westeros')
    common.set_file_option(metadata_agent_conf_file, 'DEFAULT', 'auth_plugin', 'password')
    common.set_file_option(metadata_agent_conf_file, 'DEFAULT', 'project_domain_id', 'default')
    common.set_file_option(metadata_agent_conf_file, 'DEFAULT', 'user_domain_id', 'default')
    common.set_file_option(metadata_agent_conf_file, 'DEFAULT', 'project_name', 'service')
    common.set_file_option(metadata_agent_conf_file, 'DEFAULT', 'username', 'neutron')
    common.set_file_option(metadata_agent_conf_file, 'DEFAULT', 'password', neutron_usr_password)
    common.set_file_option(metadata_agent_conf_file, 'DEFAULT', 'nova_metadata_ip', controller_server_name)
    common.set_file_option(metadata_agent_conf_file, 'DEFAULT', 'metadata_proxy_shared_secret', metadata_secret)
    common.set_file_option(metadata_agent_conf_file, 'DEFAULT', 'verbose', True)

    common.run_command('service openvswitch-switch restart', True)
    common.run_command('ovs-vsctl add-br br-ex')
    common.run_command('ovs-vsctl add-port br-ex %s' %external_network_interface)

    common.run_command('service neutron-plugin-openvswitch-agent restart', True)
    common.run_command('service neutron-l3-agent restart', True)
    common.run_command('service neutron-dhcp-agent restart', True)
    common.run_command('service neutron-metadata-agent restart', True)

    common.log('Completed Neutron Networking Service in Network Node')


def install_neutron_compute_node(controller_server_name, openstack_rabbitmq_password, neutron_usr_password, comp_vm_traffic_ntw_interface_addr):
    if not controller_server_name or len(str(controller_server_name)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no controller server name specified")
    if not openstack_rabbitmq_password or len(str(openstack_rabbitmq_password)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no openstack rabbit password specified")
    if not neutron_usr_password or len(str(neutron_usr_password)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no neutron user password specified")
    if not comp_vm_traffic_ntw_interface_addr or len(str(comp_vm_traffic_ntw_interface_addr)) == 0:
        raise Exception("Unable to install/configure Neutron Networking Service, no compute vm traffic interface ip address specified")


    print ''
    common.log('Installing Neutron Networking Service in Compute Node')

    common.run_command('apt-get install -y neutron-plugin-ml2 neutron-plugin-openvswitch-agent', True)

    common.log('Configuring Neutron Networking Service in Compute Node')
    neutron_conf_file = '/etc/neutron/neutron.conf'
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'rpc_backend', 'rabbit')
    common.set_file_option(neutron_conf_file, 'oslo_messaging_rabbit', 'rabbit_host', controller_server_name)
    common.set_file_option(neutron_conf_file, 'oslo_messaging_rabbit', 'rabbit_userid', 'openstack')
    common.set_file_option(neutron_conf_file, 'oslo_messaging_rabbit', 'rabbit_password', openstack_rabbitmq_password)
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'auth_strategy', 'keystone')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'auth_uri', "http://%s:5000" %controller_server_name)
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'auth_url', "http://%s:35357" %controller_server_name)
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'auth_plugin', 'password')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'project_domain_id', 'default')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'user_domain_id', 'default')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'project_name', 'service')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'username', 'neutron')
    common.set_file_option(neutron_conf_file, 'keystone_authtoken', 'password', neutron_usr_password)
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'core_plugin', 'ml2')
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'service_plugins', 'router')
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'allow_overlapping_ips', True)
    common.set_file_option(neutron_conf_file, 'DEFAULT', 'verbose', True)

    ml2_plugin_conf_file = '/etc/neutron/plugins/ml2/ml2_conf.ini'
    common.set_file_option(ml2_plugin_conf_file, 'ml2', 'type_drivers', 'flat,vlan,gre,vxlan')
    common.set_file_option(ml2_plugin_conf_file, 'ml2', 'tenant_network_types', 'gre')
    common.set_file_option(ml2_plugin_conf_file, 'ml2', 'mechanism_drivers', 'openvswitch')
    common.set_file_option(ml2_plugin_conf_file, 'ml2_type_gre', 'tunnel_id_ranges', '1:1000')
    common.set_file_option(ml2_plugin_conf_file, 'securitygroup', 'enable_security_group', True)
    common.set_file_option(ml2_plugin_conf_file, 'securitygroup', 'enable_ipset', True)
    common.set_file_option(ml2_plugin_conf_file, 'securitygroup', 'firewall_driver', 'neutron.agent.linux.iptables_firewall.OVSHybridIptablesFirewallDriver')
    common.set_file_option(ml2_plugin_conf_file, 'ovs', 'local_ip', comp_vm_traffic_ntw_interface_addr)
    common.set_file_option(ml2_plugin_conf_file, 'agent', 'tunnel_types', 'gre')

    nova_conf_file = '/etc/nova/nova.conf'
    common.set_file_option(nova_conf_file, 'DEFAULT', 'network_api_class', 'nova.network.neutronv2.api.API')
    common.set_file_option(nova_conf_file, 'DEFAULT', 'security_group_api', 'neutron')
    common.set_file_option(nova_conf_file, 'DEFAULT', 'linuxnet_interface_driver', 'nova.network.linux_net.LinuxOVSInterfaceDriver')
    common.set_file_option(nova_conf_file, 'DEFAULT', 'firewall_driver', 'nova.virt.firewall.NoopFirewallDriver')
    common.set_file_option(nova_conf_file, 'neutron', 'url', "http://%s:9696" %controller_server_name)
    common.set_file_option(nova_conf_file, 'neutron', 'auth_strategy', 'keystone')
    common.set_file_option(nova_conf_file, 'neutron', 'admin_auth_url', "http://%s:35357/v2.0" %controller_server_name)
    common.set_file_option(nova_conf_file, 'neutron', 'admin_tenant_name', 'service')
    common.set_file_option(nova_conf_file, 'neutron', 'admin_username', 'neutron')
    common.set_file_option(nova_conf_file, 'neutron', 'admin_password', neutron_usr_password)

    common.run_command('service nova-compute restart', True)
    common.run_command('service neutron-plugin-openvswitch-agent restart', True)

    common.run_command('service openvswitch-switch restart', True)

    common.log('Completed Neutron Networking Service in Network Node')

def install_horizon(controller_server_name):
    if not controller_server_name or len(str(controller_server_name)) == 0:
        raise Exception("Unable to install/configure Horizon Dashboard Service, no controller server name specified")

    print ''
    common.log('Installing Horizon Dashboard Service in Controller Node')

    common.run_command('apt-get install -y openstack-dashboard', True)

    common.run_command("sed -i 's/^OPENSTACK_HOST = \"127.0.0.1\"/OPENSTACK_HOST = \"%s\"/g' /etc/openstack-dashboard/local_settings.py" %controller_server_name)
    common.run_command("sed -i 's/^OPENSTACK_KEYSTONE_DEFAULT_ROLE = \"_member_\"/OPENSTACK_KEYSTONE_DEFAULT_ROLE = \"user\"/g' /etc/openstack-dashboard/local_settings.py")

    common.run_command("service apache2 reload", True)

    common.log('Completed Horizon Dashboard Service in Controller Node')


def install_cinder_controller_node(cinder_db_password, mysql_root_password, admin_token, controller_server_name, cinder_usr_password, openstack_rabbitmq_password, ctrl_mgmt_ntw_interface_addr):
    if not cinder_db_password or len(str(cinder_db_password)) == 0:
        raise Exception("Unable to install/configure Cinder Block Storage Service, no cinder database password specified")
    if not mysql_root_password or len(str(mysql_root_password)) == 0:
        raise Exception("Unable to install/configure Cinder Block Storage Service, no MySQL password specified")
    if not admin_token or len(str(admin_token)) == 0:
        raise Exception("Unable to install/configure Cinder Block Storage Service, no admin token specified")
    if not controller_server_name or len(str(controller_server_name)) == 0:
        raise Exception("Unable to install/configure Cinder Block Storage Service, no controller server name specified")
    if not cinder_usr_password or len(str(cinder_usr_password)) == 0:
        raise Exception("Unable to install/configure Cinder Block Storage Service, no cinder user password specified")
    if not openstack_rabbitmq_password or len(str(openstack_rabbitmq_password)) == 0:
        raise Exception("Unable to install/configure Cinder Block Storage Service, no openstack rabbit password specified")
    if not ctrl_mgmt_ntw_interface_addr or len(str(ctrl_mgmt_ntw_interface_addr)) == 0:
        raise Exception("Unable to install/configure Cinder Block Storage Service, no controller management interface ip address specified")

    print ''
    common.log('Installing Cinder Block Storage Service in Controller Node')

    common.run_db_command(mysql_root_password, "CREATE DATABASE IF NOT EXISTS cinder CHARACTER SET utf8 COLLATE utf8_general_ci;")
    common.run_db_command(mysql_root_password, "GRANT ALL PRIVILEGES ON cinder.* TO 'cinder'@'localhost' IDENTIFIED BY '" + cinder_db_password + "';")
    common.run_db_command(mysql_root_password, "GRANT ALL PRIVILEGES ON cinder.* TO 'cinder'@'%' IDENTIFIED BY '" + cinder_db_password + "';")

    common.log('Registering Cinder Block Storage Service in Keystone')
    os.environ['OS_TOKEN'] = admin_token
    os.environ['OS_URL'] = 'http://%s:35357/v2.0' %controller_server_name

    common.run_command("openstack user create --password %s cinder" %cinder_usr_password)
    common.run_command("openstack role add --project service --user cinder admin")
    common.run_command("openstack service create --name cinder --description 'OpenStack Block Storage Service' volume")
    common.run_command("openstack service create --name cinderv2 --description 'OpenStack Block Storage Service' volumev2")
    common.run_command("openstack endpoint create --publicurl http://" + controller_server_name + ":8776/v2/%\(tenant_id\)s --internalurl http://" + controller_server_name + ":8776/v2/%\(tenant_id\)s --adminurl http://" + controller_server_name + ":8776/v2/%\(tenant_id\)s --region Westeros volume")
    common.run_command("openstack endpoint create --publicurl http://" + controller_server_name + ":8776/v2/%\(tenant_id\)s --internalurl http://" + controller_server_name + ":8776/v2/%\(tenant_id\)s --adminurl http://" + controller_server_name + ":8776/v2/%\(tenant_id\)s --region Westeros volumev2")

    common.run_command("apt-get install -y cinder-api cinder-scheduler python-cinderclient", True)

    cinder_conf_file = '/etc/cinder/cinder.conf'
    common.set_file_option(cinder_conf_file, 'database', 'connection', "mysql://cinder:%s@%s/cinder" %(cinder_db_password, controller_server_name))
    common.set_file_option(cinder_conf_file, 'DEFAULT', 'rpc_backend', 'rabbit')
    common.set_file_option(cinder_conf_file, 'oslo_messaging_rabbit', 'rabbit_host', controller_server_name)
    common.set_file_option(cinder_conf_file, 'oslo_messaging_rabbit', 'rabbit_userid', 'openstack')
    common.set_file_option(cinder_conf_file, 'oslo_messaging_rabbit', 'rabbit_password', openstack_rabbitmq_password)
    common.set_file_option(cinder_conf_file, 'DEFAULT', 'auth_strategy', 'keystone')
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'auth_uri', "http://%s:5000" %controller_server_name)
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'auth_url', "http://%s:35357" %controller_server_name)
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'auth_plugin', 'password')
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'project_domain_id', 'default')
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'user_domain_id', 'default')
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'project_name', 'service')
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'username', 'cinder')
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'password', cinder_usr_password)
    common.set_file_option(cinder_conf_file, 'DEFAULT', 'my_ip', ctrl_mgmt_ntw_interface_addr)
    common.set_file_option(cinder_conf_file, 'oslo_concurrency', 'lock_path', '/var/lock/cinder')
    common.set_file_option(cinder_conf_file, 'DEFAULT', 'verbose', 'True')

    common.run_command("su -s /bin/sh -c 'cinder-manage db sync' cinder", True)

    common.run_command("service cinder-scheduler restart", True)
    common.run_command("service cinder-api restart", True)

    common.delete_file("/var/lib/cinder/cinder.sqlite")
    common.log('Completed Cinder Block Storage Service in Controller Node')

def install_cinder_block_storage_node(cinder_db_password, controller_server_name, cinder_usr_password, openstack_rabbitmq_password, bs_mgmt_ntw_interface_addr):
    print ''
    common.log('Installing Cinder Block Storage Service in Controller Node')

    common.run_command("apt-get install -y qemu lvm2", True)
    common.run_command("pvcreate /dev/sdb1", True)
    common.run_command("vgcreate cinder-volumes /dev/sdb1", True)

    common.run_command("sed -i 's/^filter = [ \"a/.*/\" ]/filter = [ \"a/sda/\", \"a/sdb/\", \"r/.*/\"]/g' /etc/lvm/lvm.conf")

    common.run_command("apt-get install -y cinder-volume python-mysqldb", True)

    cinder_conf_file = '/etc/cinder/cinder.conf'
    common.set_file_option(cinder_conf_file, 'database', 'connection', "mysql://cinder:%s@%s/cinder" %(cinder_db_password, controller_server_name))
    common.set_file_option(cinder_conf_file, 'DEFAULT', 'rpc_backend', 'rabbit')
    common.set_file_option(cinder_conf_file, 'oslo_messaging_rabbit', 'rabbit_host', controller_server_name)
    common.set_file_option(cinder_conf_file, 'oslo_messaging_rabbit', 'rabbit_userid', 'openstack')
    common.set_file_option(cinder_conf_file, 'oslo_messaging_rabbit', 'rabbit_password', openstack_rabbitmq_password)
    common.set_file_option(cinder_conf_file, 'DEFAULT', 'auth_strategy', 'keystone')
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'auth_uri', "http://%s:5000" %controller_server_name)
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'auth_url', "http://%s:35357" %controller_server_name)
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'auth_plugin', 'password')
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'project_domain_id', 'default')
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'user_domain_id', 'default')
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'project_name', 'service')
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'username', 'cinder')
    common.set_file_option(cinder_conf_file, 'keystone_authtoken', 'password', cinder_usr_password)
    common.set_file_option(cinder_conf_file, 'DEFAULT', 'my_ip', bs_mgmt_ntw_interface_addr)
    common.set_file_option(cinder_conf_file, 'lvm', 'volume_driver', 'cinder.volume.drivers.lvm.LVMVolumeDriver')
    common.set_file_option(cinder_conf_file, 'lvm', 'volume_group', 'cinder-volumes')
    common.set_file_option(cinder_conf_file, 'lvm', 'iscsi_protocol', 'iscsi')
    common.set_file_option(cinder_conf_file, 'lvm', 'iscsi_helper', 'tgtadm')
    common.set_file_option(cinder_conf_file, 'DEFAULT', 'enabled_backends', 'lvm')
    common.set_file_option(cinder_conf_file, 'DEFAULT', 'glance_host', controller_server_name)
    common.set_file_option(cinder_conf_file, 'oslo_concurrency', 'lock_path', '/var/lock/cinder')
    common.set_file_option(cinder_conf_file, 'DEFAULT', 'verbose', 'True')

    common.run_command("service tgt restart", True)
    common.run_command("service cinder-volume restart", True)
    common.delete_file("/var/lib/cinder/cinder.sqlite")