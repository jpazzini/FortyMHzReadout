#!/bin/env python
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import sys
import getopt, optparse
import subprocess 
import shutil

datafolder = 'data/'
ramdisk = '/mnt/rammo/'
brokers = "10.64.22.40:9092,10.64.22.41:9092,10.64.22.42:9092"
topic = "topic_matteo"

usage = "usage: %prog [options]"
parser = optparse.OptionParser(usage)
parser.add_option("-c", "--count", action="store", type="string", dest="count", default="-1")
parser.add_option("-v", "--verbose", action="store_true", dest="verbose")
(options, args) = parser.parse_args()


class Animator:

    iterator = 0

    def __init__(self):
        self.animation = "|/-\\"

    def update(self):
        sys.stdout.write("\r" + self.animation[Animator.iterator % len(self.animation)])
        sys.stdout.flush()
        Animator.iterator+=1

class Watcher:
    def __init__(self, dirtowatch_):
        self.observer = Observer()
        self.dirtowatch = dirtowatch_

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.dirtowatch, recursive=False)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()


class Handler(FileSystemEventHandler):

    @staticmethod
    def on_created(event):
        # Take any action here when a file is first created.
        newfile = str(event.src_path)
        pathtofile = newfile.replace(newfile.split('/')[-1],'')
        extension = newfile.split('/')[-1].split('.')[-1]
        basename = newfile.split('/')[-1].split('.')[0].split('_')[0]
        filenumber = int(newfile.split('/')[-1].split('.')[0].split('_')[-1])
        oldfile = '%s%s_%06d.%s' % (pathtofile, basename, filenumber-1, extension)
        newfile = '%s%s_%06d.%s' % (datafolder, basename, filenumber-1, extension)
        if filenumber>0:
            shutil.move(oldfile, newfile)

class cleaner:

    def cleanup(self):
        if os.listdir(ramdisk) != []: 
            os.system('sudo rm -r %s/*' % ramdisk)

    def emptydir(self):
        files = os.listdir(ramdisk)
        for f in files:
            shutil.move(ramdisk+'/'+f, datafolder)

def stoprun(p_, w_, c_):
    print ''
    print '--- Stopping run'
    p_.kill()
    print '    Shutting off DAQ...'
    time.sleep(5)
    w_.stop()
    print '    Stopping watcher...'
    time.sleep(2)
    print '    Cleaning up ramdisk...'
    c_.emptydir()
    time.sleep(3)
    
if __name__ == '__main__':

    if not os.path.exists(ramdisk):
        print 'ERROR! --- Ramdisk \'%s\' does not exist!' % ramdisk
        print '       --- Create one via \'sudo mount -t tmpfs -o size=8G tmpfs /mnt/rammo/\''
        exit()
    
    if not os.path.exists(datafolder):
        os.makedirs(datafolder)

    subfolders = [x for x in os.listdir(datafolder) if 'Run' in x]
    lastrun = -1 if subfolders == [] else int(max(subfolders).split('Run')[-1])
    thisrun = lastrun+1
    runfold = '%s%06d' % ('Run', thisrun)

    if not os.path.exists(datafolder+runfold):
        os.makedirs(datafolder+runfold)
        print '--- Starting %s' % runfold
        print '    Stop run by [Ctrl+C]'
    else:
        print 'WARNING! --- Run folder %s was already found into the folder' % runfold
        print '         --- This should not happen!'
        print '         --- To avoid overwriting isssues, run number has been changed to 999999!'
	thisrun = 999999
	runfold = '%s%06d' % ('Run', thisrun)
        os.makedirs(datafolder+runfold)

    c = cleaner()
    c.cleanup()

    p_list = ['sudo', './run_DMA_kafka_fullDMA', '-c %s' % options.count, '-b', '%s' % brokers, '-t', '%s' % topic, '-r %d' % thisrun]
    
    if options.verbose: 
        p_list.append('-v')

    p = subprocess.Popen(p_list)

    w = Watcher(ramdisk)
    w.run()

    a = Animator()

    while True:
        try:
            time.sleep(0.75)
            a.update()
        except (KeyboardInterrupt, SystemExit, AssertionError):
            stoprun(p, w, c)
            break

    print '--- All done'
