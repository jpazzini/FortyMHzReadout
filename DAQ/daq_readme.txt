### HOW TO LAUNCH A DAQ
'''$ sudo python daqstart.py'''

Data will be temporarily sent to RAMDISK /mnt/rammo/ and automatically moved under data/RunXXXXXX/

data_xxxxxx.dat --> binary format (64 bit words as from DMA transfer from the KCU1500)
data_xxxxxx.txt --> unpacked format, in csv format

### HOW	TO STOP A DAQ         
'''$ [Ctrl+C]'''

The script will empty the RAMDISK and move all the remaining files to the data/RunXXXXXX/ location.

### MASKING CHANNELS

A script for masking channels on the Virtex7s is available in pc1502 under /home/xdaq/bitstreams/mask.sh

'''sh /home/xdaq/bitstreams/mask.sh 0000000000000FFFFFFFFFFFFFFFFFFFF 1'''

The masking is done via the HEX bit mask, where 1 means MASKED, and 0 means UNMASKED. Bits are ordered 132->1.

fully masked:
FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

fully unmasked:
000000000000000000000000000000000

SL 0 unmasked (channels from 1 to 64)
FFFFFFFFFFFFFFFFF0000000000000000

SL 1 unmasked (channels from 65 to 128)
F0000000000000000FFFFFFFFFFFFFFFF

The second argument selects which Virtex to apply the masking to.

### SOURCE CODE

DAQ is only managed by daqstart.py and the exectuable created by compiling the C code streamed_daq.c (to be named 'streamed_daq.out')

### BACKUP

A backup version of the code is (and have to be) mantained under the bkp/ folder

### INSTRUCTION TO COMPILE THE C CODE

The -lpthread option must be used to allow C to link to the pthread libray used for threading:

'''$ sudo gcc streamed_daq.c -lpthread -o streamed_daq.out'''

### RUNNING THE OFFLINE ANALYSIS

A script used to assign the t0 via the meantimer technique and for monitoring the data taking is available offline_analysis.py

'''$ sudo pyhton offline_analysis.py -i data/RunXXXXXX/data_yyyyyy.txt -n 1000'''

This will produce 4 csv files out_df_0/1/2/3.csv (one per chamber) with the corrected time and position within cell, together with a summary plot html file offline_plots.html

### HOW TO RECOVER FROM A PC SHUTDOWN
1. check if ramdisk is available

'''$ df -Th'''
Filesystem                    Type      Size  Used Avail Use% Mounted on
/dev/mapper/cc_dtsx5--03-root xfs        50G   27G   24G  53% /
devtmpfs                      devtmpfs   32G     0   32G   0% /dev
tmpfs                         tmpfs      32G     0   32G   0% /dev/shm
tmpfs                         tmpfs      32G   27M   32G   1% /run
tmpfs                         tmpfs      32G     0   32G   0% /sys/fs/cgroup
/dev/sda3                     xfs      1014M  389M  626M  39% /boot
/dev/mapper/cc_dtsx5--03-home xfs       475G  5.1G  470G   2% /home
AFS                           afs       2.0T     0  2.0T   0% /afs
tmpfs                         tmpfs     6.3G   12K  6.3G   1% /run/user/42
tmpfs                         tmpfs     8.0G     0  8.0G   0% /mnt/rammo       <-------
tmpfs                         tmpfs     6.3G     0  6.3G   0% /run/user/1000

if not, create one:
'''$ sudo mount -t tmpfs -o size=8G tmpfs /mnt/rammo/'''

2. ensure to have the drivers properly loaded

'''$ sudo sh ./load_driver.sh'''

3. ensure to have killed all the daqstart.py and streamed_daq.out processes

'''$ sudo pkill daqstart.py
$ sudo pkill streamed_daq.out'''

