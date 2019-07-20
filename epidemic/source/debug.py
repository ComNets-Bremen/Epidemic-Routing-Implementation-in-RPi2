import time;
import parameters as p;
import cmd_functions as c;
import serial;
import os;
#Save fail-connect logs
#Input:
#    eventType: String with even description
#    neighborID: Nighbor's identifier
#    eventLog_ref: Container of the log of the protocol's events
def save_fail(typeEvent,neighborID,eventLog_ref):
    rtime="Time-stamp(seconds):"+str(time.time());
    rneighbor="neighbor:"+str(neighborID);
    revent=rtime+","+typeEvent+","+rneighbor;
    eventLog_ref[0]=eventLog_ref[0]+revent+'\n'
    print(typeEvent+","+rneighbor);    
#Save start-comunication event's logs
#Input:
#    neighborID: Nighbor's identifier
#    eventLog_ref: Container of the log of the protocol's events
def save_start(neighborID,eventLog_ref):
    stime="Time-stamp(seconds):"+str(time.time());
    sneighbor="neighbor:"+str(neighborID);
    tevent=stime+","+"Start-Comunication"+","+sneighbor;
    eventLog_ref[0]=eventLog_ref[0]+tevent+'\n'
    print("Start-Comunication"+","+sneighbor);
#Save close-comunication event's logs
#Input:
#    neighborID: Nighbor's identifier
#    eventLog_ref: Container of the log of the protocol's events
def save_close(neighborID,eventLog_ref):
    stime="Time-stamp(seconds):"+str(time.time());
    sneighbor="neighbor:"+str(neighborID);
    tevent=stime+","+"Close-Comunication"+","+sneighbor;
    eventLog_ref[0]=eventLog_ref[0]+tevent+'\n'
    print("Close-Comunication"+","+sneighbor);
#Save routing events logs
#Input:
#    eventType: String with even description
#    neighborID: Nighbor's identifier
#    rssi: Incoming signal in dBm
#    eventLog_ref: Container of the log of the protocol's events
def save_routing_events(eventType,neighborID,rssi,eventLog_ref):
    stime="Time-stamp(seconds):"+str(time.time());
    sneighbor="neighbor:"+str(neighborID);
    if rssi!=0:
        slevel=",Level(dBm):"+str(rssi);
    else:
        slevel="";
    tevent=stime+","+eventType+","+sneighbor+","+slevel;
    eventLog_ref[0]=eventLog_ref[0]+tevent+'\n'
    print(eventType+","+sneighbor+slevel);
#Save transport events logs
#Input:
#    eventType: String with even description
#    neighborID: Nighbor's identifier
#    lenBytes: Size of packet
#    eventLog_ref: Container of the log of the protocol's events
def save_transport_event(eventType,neighborID,lenBytes,eventLog_ref):
    if lenBytes>0:
        stime="Time-stamp(seconds):"+str(time.time());
        sneighbor="neighbor:"+str(neighborID);
        tevent=stime+","+eventType+","+sneighbor+","+"total-size(Bytes):"+str(lenBytes);
        eventLog_ref[0]=eventLog_ref[0]+tevent+'\n'
        print(eventType+","+sneighbor+","+"total-size(Bytes):"+str(lenBytes));
#Get RSSI when 2 devices are comunicating and save it as a log
#Input:
#    neighborID: Nighbor's identifier
#    intended_mac: MAC used by the neighbor's p2p interface
#    p2pInterface: Neighbor's p2p interface
#    eventLog_ref: Container of the log of the protocol's events
def save_rssi(neighborID,intended_mac,p2pInterface,eventLog_ref):
    if intended_mac!=None:
        cmdout=c.write_read_cmd(['sudo', 'iw','dev',p2pInterface,'station','get',intended_mac]);
        ind=cmdout.find(bytes('signal:','utf-8'));
        if ind!=-1:
            inst=cmdout[ind:];
            ind=inst.find(bytes('\n','utf-8'));
            inst=inst[:ind].decode('utf-8');
        else:
            inst=""; 
        ind=cmdout.find(bytes('signal avg:','utf-8'));
        if ind!=-1:
            avg=cmdout[ind:];
            ind=avg.find(bytes('\n','utf-8'));
            avg=avg[:ind].decode('utf-8');
        else:
            avg="";
        if inst!="" or avg!="":
            rssi="Time-stamp(seconds):"+str(time.time())+","+"RSSI,neighbor:"+str(neighborID)+","+inst+","+avg;
            eventLog_ref[0]=eventLog_ref[0]+rssi+'\n'
            print("RSSI,neighbor:"+str(neighborID)+","+inst+","+avg);
#Clean Serial port buffer
#Input
#    ser: Serial port
def cleanBuffer(ser):
    while ser.inWaiting()>0:
        ser.read();
#Read GPGGA codes from gnss device and save it as a log
def read_gnss(ser,gnssLog_ref,nmeaCode_ref):
    while ser.inWaiting()>0:
        sbyte=ser.read();
        nmeaCode_ref[0]=nmeaCode_ref[0]+sbyte;
        if sbyte==p.gnssEndCode:
            if p.gnssInstruction in nmeaCode_ref[0]:
                gnssLog_ref[0]=gnssLog_ref[0]+nmeaCode_ref[0].decode('utf-8');
            nmeaCode_ref[0]=bytes(0);
#Syncronize the device's clock with the gnss clock
#Input
#    ser: Serial port
def clockSincronize(ser):
    isGPGGA=False;
    while not isGPGGA:
        nmeaCode = ser.readline();
        isGPGGA=p.gnssInstruction in nmeaCode;
    line=nmeaCode.split(p.gnssDelimeter);
    time=str(int(line[1][0:2])+p.timeZone)+':'+line[1][2:4].decode('utf-8')+':'+line[1][4:].decode('utf-8');
    cmdout=c.write_read_cmd(['sudo','timedatectl','set-ntp','false']);
    cmdtime=c.write_read_cmd(['sudo','date','--set='+time]);
    cmdout=c.write_read_cmd(['sudo','hwclock','--systohc']);
    print(cmdtime)
#Open the serial port for the GNSS device
#Input
#    gnssPort: Name of serial interface
def start_gnss(gnssPort):
    ser = serial.Serial('/dev/'+gnssPort, p.gnssBaudrate, timeout=p.timeout);
    cleanBuffer(ser);
    return ser;
#Save the GNSS logs in a new file
#Input
#    fIndex_ref: Container of the number of GNSS log files
#    debugpath: Directory where log files are saved
#    gnssLog_ref: Container of GNSS logs
def save_gnss(fIndex_ref,debugPath,gnssLog_ref):
    if len(gnssLog_ref[0])>0:
        text_file = open(debugPath+"/gnss_"+str(fIndex_ref[0])+".log", "w");
        text_file.write(gnssLog_ref[0]);
        text_file.close();
        gnssLog_ref[0]=""
        fIndex_ref[0]+=1;
        print("Positions saved");
#Save the event logs in a new file
#Input
#    fIndex_ref: Container of the number of event log files
#    debugpath: Directory where log files are saved
#    eventLog_ref: Container of the log of the protocol's events 
def save_events(fIndex_ref,debugPath,eventLog_ref):
    if len(eventLog_ref[0])>0:
        text_file = open(debugPath+"/events_"+str(fIndex_ref[0])+".log", "w");
        text_file.write(eventLog_ref[0]);
        text_file.close();
        fIndex_ref[0]+=1;
        eventLog_ref[0]="";
        print("Events saved");
#Check the GNSS device periodically
#Input
#    ser: Serial port
#    debugpath: Directory where log files are saved
#    mutex: Lock sensitive functions
def run_gnss(ser,debugPath,mutex):
    nmeaCode=bytes(0);
    nmeaCode_ref=[nmeaCode];
    gnssLog="";
    gnssLog_ref=[gnssLog];
    fIndex=0;
    fIndex_ref=[fIndex];
    lastSave=time.time();
    while True:
        time.sleep(p.sleepMainLoop);
        mutex.acquire();
        try:
            read_gnss(ser,gnssLog_ref,nmeaCode_ref);
            currentTime=time.time();
            if currentTime>=lastSave+p.saveTime:
                save_gnss(fIndex_ref,debugPath,gnssLog_ref);
                lastSave=time.time();
        finally:
            mutex.release();
#Create new directory for log files
def create_debug_folder():
    folders = [f for f in os.listdir(p.pathe+"/Debug/LogFiles")];
    debugPath=p.pathe+"/Debug/LogFiles/"+str(len(folders));
    os.makedirs(debugPath);
    return debugPath;
#Clean epidemic messages and set initial messages
def reset_messages():
    cmdout=c.write_read_cmd(['sudo','rm','-r',p.pathe+"/myfiles"]);
    cmdout=c.write_read_cmd(['sudo','rm','-r',p.pathe+"/efiles"]);
    cmdout=c.write_read_cmd(['sudo','cp','-r',p.pathe+"/Debug/initialFiles/myfiles",p.pathe]);
    cmdout=c.write_read_cmd(['sudo','cp','-r',p.pathe+"/Debug/initialFiles/efiles",p.pathe]);
