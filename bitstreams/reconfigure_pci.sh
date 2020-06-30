sudo chmod 777 /sys/bus/pci/devices/0000\:03\:00.0/remove
echo 1 > /sys/bus/pci/devices/0000\:03\:00.0/remove
sudo chmod 777 /sys/bus/pci/rescan
echo 1 > /sys/bus/pci/rescan
