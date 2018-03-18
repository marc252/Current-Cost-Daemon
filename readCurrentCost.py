from __future__ import with_statement
import serial
import time
from xml.dom import minidom
from optparse import OptionParser
import daemon
import lockfile.pidlockfile
import sys
from shutil import copyfile
import os

def readCurrentCost(port,interval,outname,channel,rotate,baudrate=57600):

    if outname==None:
        outfile = sys.stdout
        rotate = 0
    else:
        outfile = open(outname,'w',buffering=1)

    #open serial port
    ser = serial.Serial(port=port, baudrate=baudrate,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS,timeout=5)

    # get current time
    startTime = time.time()
    startHour = time.time()
    # and initialise data
    temp = 0.
    power = 0.
    count = 0
    
    while True:
        line = ser.readline()
        print line
        thisTime = time.time()
        if len(line)>0:
            xmldoc = minidom.parseString(line)
            # parse the xml
            try:
                temperature_nodes = xmldoc.getElementsByTagName('tmpr')
                if channel!=0:
                    watts_nodes = xmldoc.getElementsByTagName('ch'+`channel`)[0].getElementsByTagName('watts')
                else:
                    watts_nodes = xmldoc.getElementsByTagName('ch1')[0].getElementsByTagName('watts')
                    watts_nodes += xmldoc.getElementsByTagName('ch2')[0].getElementsByTagName('watts')
                    watts_nodes += xmldoc.getElementsByTagName('ch3')[0].getElementsByTagName('watts')
            except:
                continue
            # accumulate data
            temp  += float(temperature_nodes[0].childNodes[0].nodeValue)
            for node in watts_nodes:
                power += float(node.childNodes[0].nodeValue)
            count += 1
            # check if we should write out data
            if thisTime-startTime >= interval:
                outfile.write("%s; %.2f; %.2f\n"%(time.strftime("%d-%m-%Y %H:%M:%S",time.localtime(startTime+(thisTime-startTime)/2.)),temp/count, power/count))
                if rotate > 0:
                    if thisTime - startHour > rotate*3600*24:
                        outfile.flush()
                        outfile.close()
                        rotationFileName = "%s" % time.strftime("%d%m%Y.csv",time.gmtime(thisTime))
                        newname=os.path.dirname(outname)+'/'+rotationFileName
                        print newname
                        copyfile(outname,newname)
                        outfile = open(outname,'a',buffering=1)
                        startHour=thisTime
                # reset counters
                count = 0
                temp = 0.
                power = 0.
                startTime = thisTime

if __name__ == "__main__":
    usage = "usage: %prog [options]\n\nParse data coming from a CurrentCost device."
    
    parser = OptionParser(usage=usage)
    parser.add_option("-f", "--file", dest="filename",help="write output to FILE (default: stdout)", metavar="FILE")
    parser.add_option("-s", "--serial-device", default='/dev/ttyUSB0',metavar="DEV",help="serial device to read from")
    parser.add_option("-i", "--interval",metavar="INT",type="int",default=300,help="interval in seconds over which data should be averaged (default:300)")
    parser.add_option("-d", "--daemon",action="store_true",default=False,help="run in daemon mode")
    parser.add_option("-p", "--pid-file",metavar="FILE",help="store PID in FILE")
    parser.add_option("-c", "--channel",metavar="INT",type="int",default=1,help="EnviR Channel, 0 for all combined")
    parser.add_option("-r", "--rotate", metavar="INT",type="int",default=0,help="Rotate logs every n days, default 0 no rotation")
    (options, args) = parser.parse_args()
    if options.daemon:
        if options.pid_file == None:
            parser.error('no pid file specified')
        if options.filename == None:
            parser.error('must specify output file')
            
        #ourlockfile = lockfile.LockFile(options.pid_file)
        ourlockfile = lockfile.pidlockfile.PIDLockFile(options.pid_file, timeout=1)
        context = daemon.DaemonContext(
            working_directory='/tmp',
            umask=18 ,
            pidfile=ourlockfile
            )

        with context:
            readCurrentCost(options.serial_device,options.interval,options.filename,options.channel, options.rotate)
    else:
        readCurrentCost(options.serial_device,options.interval,options.filename,options.channel,options.rotate)
