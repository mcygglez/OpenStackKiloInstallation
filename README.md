# OpenStackKiloInstallation

This repository contains Python script that automate the installation of an OpenStack Kilo multi-node deployment.

In case you are trying this in VirtualBox, make sure you configure the virtual machines as follow.

CONTROLLER NODE:

Virtual Machine Network Cards

-vNIC (eth0) in Host Only Network (138.4.19.0/4) Adapter Type: Paravirtualized Promiscuous Mode: Allow All

-vNIC (eth1) in NAT Network 

Virtual Machine Partition Table

-1 HDD (16GB)

-1GB /boot ext4

-4GB swap

-11GB physical Volume(LVM) -> volume group (vgroot) -> logical volume (volroot)


Execute the following scripts on the Controller Node and then reboot.
python enable_openstack_repository.py
python controller_installer.py

NETWORK NODE:
Virtual Machine Network Cards
-vNIC (eth0) in Host Only Network2 (138.4.19.0/4) Adapter Type: Paravirtualized Promiscuous Mode: Allow All
-vNIC (eth1) in Host Only Network3 (192.168.82.0/4) Adapter Type: Paravirtualized Promiscuous Mode: Allow All
-vNIC (eth2) in Host Only Network4 (138.4.20.0/4) Adapter Type: Paravirtualized Promiscuous Mode: Allow All
-vNIC (eth3) in NAT Network

Virtual Machine Partition Table
1 HDD (16GB)
	-1GB /boot ext4
	-4GB swap
	-11GB physical Volume(LVM) -> volume group (vgroot) -> logical volume (volroot)

Execute the following scripts on the Controller Node and then reboot.
python enable_openstack_repository.py
python network_installer.py


COMPUTE NODES:
Virtual Machine Network Cards
-vNIC (eth0) in Host Only Network2 (138.4.19.0/4) Adapter Type: Paravirtualized Promiscuous Mode: Allow All
-vNIC (eth1) in Host Only Network3 (192.168.82.0/4) Adapter Type: Paravirtualized Promiscuous Mode: Allow All
-vNIC (eth2) in NAT Network

Virtual Machine Partition Table
1 HDD (16GB)
	-1GB /boot ext4
	-4GB swap
	-11GB physical Volume(LVM) -> volume group (vgroot) -> logical volume (volroot)

Execute the following scripts on the Controller Node and then reboot.
python enable_openstack_repository.py
python compute_installer.py [hypervisor_type]
