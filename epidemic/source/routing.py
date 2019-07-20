#Functions used for the neighbor discovery algorithim and for the formation of wi-fi networks between 2 devices
import parameters as p;
import time
import transport as t;
import cmd_functions as c;
import debug as d;
import random;
#It returns the device identifier used for the epidemic protocol
def get_myID():
    f=open(p.pathe+"/p2p.conf");
    fout=f.read();
    inde=fout.find('EPI');
    indd=fout.find('DEMIC');
    return int(fout[inde+3:indd]);
#It returns the names of the wifi interface and the gps interface
def get_interfaces():
    f=open(p.pathe+"/interfaces");
    fout=f.read();
    fout=fout.splitlines();
    wifiPort=fout[0];
    if len(fout)>1:
        gnssPort=fout[1];
    else:
        gnssPort="";
    return wifiPort,gnssPort;
#It returns the virtual interface used for wifi-direct
def get_direct_interface():
    out = c.write_read_cmd(['sudo', 'wpa_cli','interface']);
    if bytes("Selected interface",'utf8') in out:
        out=out.splitlines();
        out=out[0].split(bytes([39]));
        out=out[1].decode('utf-8');
        return out;
    return None;
#Input:
#    Neighbor detailed information (sudo wpa_cli p2p_peer <neighbor MAC>)
#Output:
#    Identifier of the neighbor
def find_neighborID(cmdout):
    inde=cmdout.find(bytes('EPI','utf8')); 
    if inde != -1: #same kind?
        indd=cmdout.find(bytes('DEMIC','utf8')); 
        return int(cmdout[inde+3:indd]);
    return None;
#Input:
#    Neighbor detailed information (sudo wpa_cli p2p_peer <neighbor MAC>)
#Output:
#    MAC used by a neighbor when a wi-fi network is already formed
def find_neighbor_intended_addr(cmdout):
    bstart=bytes('intended_addr=','utf8');
    inde=cmdout.find(bstart); 
    if inde != -1:
        cmdout=cmdout[inde+len(bstart):];
        indd=cmdout.find(bytes('\n','utf8'));
        return cmdout[:indd].decode('utf-8');
    return None;
#Input:
#    Neighbor detailed information (sudo wpa_cli p2p_peer <neighbor MAC>)
#Output:
#    RSSI of the neighbor discovery beacon received from the neighbor
def find_neighbor_RSSI(cmdout):
    bstart=bytes('level=','utf8');
    inde=cmdout.find(bstart); 
    if inde != -1:
        cmdout=cmdout[inde+len(bstart):];
        indd=cmdout.find(bytes('\n','utf8'));
        return int(cmdout[:indd]);
    return None;
#Input:
#    Device identifier
#Output:
#    IP address of the device
def build_ip(iD):
    subNet=iD.to_bytes(3, byteorder='big');
    ipAdd=p.netIp;
    for b in subNet:
        ipAdd+="."+str(b);
    return ipAdd;
#It reboots the epidemic protocol cycle if a timeout is reached
#Input:
#    state: Current state of the device
#    wdTimer: Time when the whatch dog mechanisim started
#    neighborID: Nighbor's identifier
#    eventLog_ref: Container of the log of the protocol's events
#Output:
#    new state of the device
#    Time when the whatch dog mechanisim started
def checkWDT(state,wdTimer,neighborID,eventLog_ref):
    if state!=p.TRANSPORT:
        currentTime=time.time();
        if currentTime>=wdTimer+p.timeout:
            cmdout=c.write_read_cmd(['sudo','wpa_cli','p2p_flush']);
            cmdout=c.write_read_cmd(['sudo','wpa_cli','p2p_find']);
            if p.recordEvents and state==p.CONNECT:  #Execute only in debug mode
                d.save_fail("Time-out",neighborID,eventLog_ref);
            return p.SEARCH,currentTime+random.random()*p.backoff;
    return state,wdTimer;
#It removes old neighbor from the epidemic neighbor list
#Input: List with recent visited neighbors
def update_neighbor_list(neighborList):
    currentTime=time.time();
    oldNeighbors=[];
    for neighbor in neighborList:
        if currentTime>=neighborList[neighbor]+p.timeCaducity:
            oldNeighbors.append(neighbor);
    for neighbor in oldNeighbors:
        del neighborList[neighbor];

#It starts the neighbor discovery mechanisim
#Input: Wifi interface name
def start_protocol(wifiPort):
    cmdout=c.write_read_cmd(['sudo','ifconfig',wifiPort,'up']);
    cmdout=c.write_read_cmd(['sudo','rm','/var/run/wpa_supplicant/"','wifiPort','-f']);
    cmdout=c.write_read_cmd(['sudo','killall','wpa_supplicant']);
    time.sleep(p.sleepStart);
    cmdout=c.write_read_cmd(['sudo','wpa_supplicant','-i',wifiPort,'-c',p.pathe+'/p2p.conf','-Dnl80211','-B','-u']);
    print(cmdout);
    cmdout=c.write_read_cmd(['sudo','wpa_cli','p2p_flush']);
    cmdout=c.write_read_cmd(['sudo','wpa_cli','p2p_find']);
#It checks if the neighbor is a right candite to request a connection.
#Input:
#    devicepath: Information about the discovered neighbor
#    myID: Device's identifier
#    neighborList: List with recent visited neighbors
#    wdTimer: Time when the watch dog mechanisim started
#    eventLog_ref: Container of the log of the protocol's events
#Output:
#    new state of the device
#    Time when the whatch dog mechanisim started
def handle_deviceFound(devicepath,myID,neighborList,wdTimer,eventLog_ref):
        mac=devicepath[-12:];
        MAC=mac[0:2]+":"+mac[2:4]+":"+mac[4:6]+":"+mac[6:8]+":"+mac[8:10]+":"+mac[10:12]; #get mac address
        cmdout=c.write_read_cmd(['sudo', 'wpa_cli','p2p_peer',MAC]);
        neighborID=find_neighborID(cmdout);
        if neighborID != None:
            intended_mac=find_neighbor_intended_addr(cmdout);
            rssi=find_neighbor_RSSI(cmdout);
            if p.recordEvents: #Execute only in debug mode
                d.save_routing_events("Device-found",neighborID,rssi,eventLog_ref);
            if (myID<neighborID):
                if neighborID not in neighborList: #peer was not visted in a short time
                    if intended_mac==p.FREEINTENDED and rssi!=0:
                        if rssi>p.MINRSSI:
                            cmdout=c.write_read_cmd(['sudo','wpa_cli','p2p_connect',MAC,'pbc','go_intent=1']);
                            if p.recordEvents: #Execute only in debug mode
                                d.save_routing_events("Connection-request",neighborID,rssi,eventLog_ref);
                            return p.CONNECT,neighborID,MAC,time.time()+p.backoff;
                        else:
                            wdTimer=time.time()-p.timeout+p.retryTime;
        return p.SEARCH,None,None,wdTimer;
#It accepts the connection from a neighbor
#Input: 
#    devicepath: Information about the discovered neighbor
#    myID: Device's identifier
#    wdTimer: Time when the watch dog mechanisim started
#    eventLog_ref: Container of the log of the protocol's events
#Output:
#    new state of the device
#    Nighbor's identifier
#    Time when the whatch dog mechanisim started
def handle_goNegotiationRequest(devicepath,myID,wdTimer,eventLog_ref):
    mac=devicepath[-12:];
    MAC=mac[0:2]+":"+mac[2:4]+":"+mac[4:6]+":"+mac[6:8]+":"+mac[8:10]+":"+mac[10:12]; #get mac address
    cmdout=c.write_read_cmd(['sudo', 'wpa_cli','p2p_peer',MAC]);
    neighborID=find_neighborID(cmdout);
    rssi=find_neighbor_RSSI(cmdout);
    if neighborID!=None:
        if (myID>neighborID):
            cmdout=c.write_read_cmd(['sudo','wpa_cli','p2p_connect',MAC,'pbc','go_intent=15']);
            if p.recordEvents: #Execute only in debug mode
                d.save_routing_events("Connection-accept",neighborID,rssi,eventLog_ref);
            return p.CONNECT,neighborID,MAC,time.time();
    return p.SEARCH,None,None,wdTimer;
#Once 2 devices are connected it starts the algorithim for exchanging messages with TCP/IP
#Input:
#    proerties: Properties of the network
#    myID: Device's identifier
#    myAddress: Device's IP address
#    neighborID: Nighbor's identifier
#    neighborList: List with recent visited neighbors
#    eventLog_ref: Container of the log of the protocol's events
def handle_GroupStarted(properties,myID,myAddress,neighborID,neighborMAC,neighborList,eventLog_ref):
    if "group_object" in properties:
        p2pInterface=get_direct_interface();
        if p.recordEvents:  #Run only in debug mode
            if neighborMAC!=None:
                cmdout=c.write_read_cmd(['sudo', 'wpa_cli','p2p_peer',neighborMAC]);
                intended_mac=find_neighbor_intended_addr(cmdout);
        else:
            intended_mac=None;
        if (myID<neighborID):
            role=p.CLIENT;
        else:
            role=p.SERVER;
        neighborAdress=build_ip(neighborID);
        cmdout=c.write_read_cmd(['sudo','ifconfig',p2pInterface,myAddress,'netmask','255.0.0.0','up']);
        t.transport_fsm(role,myID,neighborID,myAddress,neighborAdress,neighborList,intended_mac,p2pInterface,eventLog_ref);
