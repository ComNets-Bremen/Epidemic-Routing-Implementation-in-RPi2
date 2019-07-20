#Funtions to exchange messages between 2 devices
import parameters as p;
import cmd_functions as c;
from pathlib import Path;
import socket;
import select;
import time;
import debug as d;
import math;
#Build a summary of the message s in the memory of the device
def get_my_summary_vector():
    efilespath=p.pathe+'/efiles';
    myfilespath=p.pathe+'/myfiles';
    mysummary1=c.write_read_cmd(['ls', efilespath,'-t']);
    mysummary1=mysummary1.splitlines();
    mysummary2=c.write_read_cmd(['ls', myfilespath,'-t']);
    mysummary2=mysummary2.splitlines();
    return mysummary1+mysummary2
#Decode a TCP message
def extract_data(data):
    if data[:len(p.summaryCode)]==p.summaryCode:
        dType=p.SUMMARY;
        data=data[len(p.summaryCode):];
        data=data.split(p.breakName);
    elif data[:len(p.requestCode)]==p.requestCode:
        dType=p.REQUEST;
        data=data[len(p.requestCode):];
        data=data.split(p.breakName);
    elif data[:len(p.messagesCode)]==p.messagesCode:
        dType=p.MESSAGES;
        data=data[len(p.messagesCode):];
        data=data.split(p.breakMessage);
    else:
        return p.ERROR,[];
    if data[-1][-len(p.endCode):]==p.endCode:
        data[-1]=data[-1][:-len(p.endCode)];
    else:
        data=data[:-1];
    if len(data)==1:
        if data[0]==bytes(0):
            data=[];
    return dType,data;
#Get the paramaters of a message based on its name
#Input: Message's name
def decode_name(neighborPacket):
    ind=neighborPacket.find(bytes('i','utf8'));
    realname=neighborPacket[0:ind];
    indd=neighborPacket.find(bytes('d','utf8'));
    dest=int(neighborPacket[0:indd]);
    indj=neighborPacket.find(bytes('j','utf8'));
    jump=int(neighborPacket[ind+1:indj]);
    return realname,dest,jump;
#Returns true if a message should be requested to the connected neighbor
#Input:
#    mySummary: summary of the message s in the memory of the device
#    neighborPacket: Message's name
#    myID: Device's identifier
#    neighborID: Neighbors identifier
def should_request_packet(mySummary,neighborPacket,myID,neighborID):
    realname,dest,jump=decode_name(neighborPacket);
    if (jump>1 and dest != neighborID) or dest==myID:
        for text in mySummary:
            if realname in text:
                return False;
        return True;
    return False;
#Build a vector with the names of the messages to be requested
def get_request_vector(mySummary,neighborSummary,myID,neighborID):
    request=[];
    for neighborPacket in neighborSummary:
        if should_request_packet(mySummary,neighborPacket,myID,neighborID):
            request.append(neighborPacket);
    return request;
#Returns an epidemic packet with a vector of names of messages
#Input: Names of messages
def build_names(names):
    mNames=bytes("",'utf8');
    for name in names:
        if name is names[-1]:
            mNames+=name;
        else:
            mNames+=name+p.breakName;
    return mNames;
#Returns an epidemic packet with a vector of messages
#Input: Names of messages
def build_messages(request):
    efilespath=p.pathe+'/efiles';
    messages=bytes("",'utf8');
    for rPacket in request:
        file=Path(efilespath+"/"+rPacket.decode("utf-8"));
        if file.is_file():
            F=open(file,"r");
            B=bytes(F.read(),'utf8');
        else:
            B=p.nullCode;
        if rPacket is request[-1]:
            messages+=B;
        else:
            messages+=B+p.breakMessage;
    return messages;
#It decreases the number of jumps left of a message
#Input:
#    oldname: Message's name
#    myID: Device's identifier
#Output:
#    newName: new message's name
#    myPacket: True if the device is the messge's final destination
def get_new_name(oldName,myID):
    realname,dest,jump=decode_name(oldName);
    newName=realname.decode("utf-8")+'i'+str(jump-1)+'j';
    myPacket=dest==myID;
    return newName,myPacket;
#It saves the messages in the file system of the device
#Input:
#    request: Vector of the names of the requested messages
#    messages: Vector with the messages
#    myID: Device's identifier
def save_messages(request,messages,myID):
    efilespath=p.pathe+'/efiles';
    myfilespath=p.pathe+'/myfiles';
    lim=len(messages) if len(messages)<len(request) else len(request);
    for i in range(0,lim):
        if messages[i]!=p.nullCode:
            newName,myPacket=get_new_name(request[i],myID);
            if myPacket:
                file = open(myfilespath+"/"+newName,"w");
            else:
                file = open(efilespath+"/"+newName,"w");
            file.write(messages[i].decode("utf-8"));
            file.close();
#It waits for a TCP packet and it returns its content
#Input:
#    sc: Channel (socket if it is a server or connection if it is a client)
#Output:
#    data: Content of a TCP packet
def receive_packet(sc):
    data=bytes(0);
    sc.settimeout(p.timeout);
    try:
        ready = select.select([sc], [], [], p.timeout);
        if ready[0]:
            data=sc.recv(p.bufferSize);
    except:
        pass;
    return data;
#It waits for a complete epidemic packet
#Input:
#    sc: Channel (socket if it is a client or connection if it is a server)
#    neighborID: Nighbor's identifier
#    intended_mac: MAC used by the neighbor's p2p interface
#    p2pInterface: Neighbor's p2p interface
#    eventLog_ref: Container of the log of the protocol's events
#Output:
#    data: Content of an epidemic packet
#    state: Condition to continue or break the TCP service
def receive_data(sc,neighborID,intended_mac,p2pInterface,eventLog_ref):
    data=bytes("",'utf-8');
    portion=bytes("",'utf-8');
    if p.recordEvents: #Execute only in debug mode
        d.save_rssi(neighborID,intended_mac,p2pInterface,eventLog_ref);
    while portion[-len(p.endCode):]!=p.endCode:
        portion=receive_packet(sc);
        if len(portion)==0:
            return data;
        data+=portion;
    return data;
#It sends an epidemic packet
#Input:
#    data: Content of an epidemic packet
#    sc: Channel (socket if it is a client or connection if it is a server)
#    startCode: epidemic header
#    endCode: epidemic footer
#    state: Internal state (CONTINUE,BREAK)
#Output: Return condition to continue or break the TCP service
def send_data(data,sc,startCode,endCode,state):
    data=startCode+data+endCode;
    timeout=math.ceil(len(data)/p.bufferSize)+p.timeout;
    sc.settimeout(timeout);
    try:
        sc.sendall(data);
    except:
        return p.BREAK;
    return state;
#It closses the TCP service
#Input:
#    s: TCP socket
#    sc: TCP connection if the device is a server otherwise TCP socket
def close_connection(s):
    try:
        s.shutdown(1);
    except:
        pass;
    try:
        s.close();
    except:
        pass;
    try:
        s.close();
    except:
        pass;
#It starts a TCP Server
#Input: Device's IP address
#Output:
#    s: TCP socket
#    sc: TCP connection
def start_server(serverAddress):
    s=None;
    sc=None;
    try:
        s = socket.socket();
        s.settimeout(p.timeout);
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1);
        s.bind((serverAddress,p.serverPort));
        s.listen(1);
        sc, address = s.accept();
        sc.settimeout(p.timeout);
        return s,sc;
    except Exception as e: 
        print(e);
        close_connection(s);
        return None,None;
#It connects to a TCP service
#Input: Neighbor's IP address
#Output:
#    s: TCP socket
def start_client(serverAddress):
    s=None;
    stop=time.time()+p.timeout;
    while time.time()<stop:
        try:
            s = socket.socket();
            s.settimeout(p.timeout);
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1);
            s.connect((serverAddress,p.serverPort));
        except:
            close_connection(s);
            time.sleep(p.ClientDelay);
            continue;
        return s;
    close_connection(s);
    return None;
#It starts a TCP service
#Input
#    role: TCP role (SERVER,CLIENT)
#    myAdress: Device's IP address
#    neighborAdress: Neighbor's IP address
#Output:
#    s: TCP socket
#    sc: TCP connection if the device is a server otherwise TCP socket
def start_transport(role,myAdress,neighborAdress):
    if role==p.SERVER:
        s,sc=start_server(myAdress);
    else:
        s=start_client(neighborAdress);
        sc=s;
    return s,sc;
#Algorithm to exchange messages between 2 devices
#Input
#    role: TCP role (SERVER,CLIENT)
#    myID: Device's identifier
#    neighborID: Nighbor's identifier
#    myAdress: Device's IP address
#    neighborAdress: Neighbor's IP address
#    neighborList: List with recent visited neighbors
#    intended_mac: MAC used by the neighbor's p2p interface
#    p2pInterface: Neighbor's p2p interface
#    eventLog_ref: Container of the log of the protocol's events
def transport_fsm(role,myID,neighborID,myAdress,neighborAdress,neighborList,intended_mac,p2pInterface,eventLog_ref):
    s,sc=start_transport(role,myAdress,neighborAdress);
    if s==None:
        if p.recordEvents: #Execute only in debug mode
            d.save_fail("Start-TCP-Failure",neighborID,eventLog_ref);
        return;
    if p.recordEvents: #Execute only in debug mode
        d.save_start(neighborID,eventLog_ref);    
    state=p.CONTINUE;
    mySummary=get_my_summary_vector();
    neighborSummary=None;
    myRequest=None;
    neighborRequest=None;
    #if role==p.SERVER:
    if role==p.CLIENT:
        data=build_names(mySummary);
        state=send_data(data,sc,p.summaryCode,p.endCode,state);
        if p.recordEvents: #Execute only in debug mode
            d.save_transport_event("Send-Summary",neighborID,len(p.summaryCode)+len(data)+len(p.endCode),eventLog_ref);
    #while True:
    while state==p.CONTINUE:
        data=receive_data(sc,neighborID,intended_mac,p2pInterface,eventLog_ref);
        if data[-len(p.endCode):]==p.endCode:
            state=p.CONTINUE;
        else:
            state=p.BREAK;
        dType,content=extract_data(data);
        if p.recordEvents: #Execute only in debug mode
            d.save_transport_event("Received-"+p.TYPES[dType],neighborID,len(data),eventLog_ref);
        if dType==p.SUMMARY:
            neighborSummary=content;
            myRequest=get_request_vector(mySummary,neighborSummary,myID,neighborID);
            if len(myRequest)>0:
                data=build_names(myRequest);
                state=send_data(data,sc,p.requestCode,p.endCode,state);
                if p.recordEvents: #Execute only in debug mode
                    d.save_transport_event("Send-Request",neighborID,len(p.requestCode)+len(data)+len(p.endCode),eventLog_ref);
            else:
                #if role==p.CLIENT:
                if role==p.SERVER:
                    data=build_names(mySummary);
                    state=send_data(data,sc,p.summaryCode,p.endCode,state);
                    if p.recordEvents: #Execute only in debug mode
                        d.save_transport_event("Send-Summary",neighborID,len(p.summaryCode)+len(data)+len(p.endCode),eventLog_ref);
                else:
                    if state==p.CONTINUE:
                        neighborList[neighborID]=time.time();
                    state=p.BREAK;
        elif dType==p.REQUEST:
            neighborRequest=content;
            data=build_messages(neighborRequest);
            state=send_data(data,sc,p.messagesCode,p.endCode,state);
            if p.recordEvents: #Execute only in debug mode
                d.save_transport_event("Send-Messages",neighborID,len(p.messagesCode)+len(data)+len(p.endCode),eventLog_ref);
        elif dType==p.MESSAGES:
            messages=content;
            save_messages(myRequest,messages,myID);
            #if role==p.CLIENT:
            if role==p.SERVER:
                data=build_names(mySummary);
                state=send_data(data,sc,p.summaryCode,p.endCode,state);
                if p.recordEvents: #Execute only in debug mode
                    d.save_transport_event("Send-Summary",neighborID,len(p.summaryCode)+len(data)+len(p.endCode),eventLog_ref);
            else:
                if state==p.CONTINUE:
                    neighborList[neighborID]=time.time();
                state=p.BREAK;
        else:
            state=p.BREAK;
    close_connection(s);
    if p.recordEvents: #Execute only in debug mode
        d.save_close(neighborID,eventLog_ref);
