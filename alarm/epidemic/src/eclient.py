import socket;
#import os;
from subprocess import check_output
import event_record
import time

def write_read_cmd(list_command):
    out = check_output(list_command)
    return out  

def get_my_summary_vector(pathe):
    efilespath=pathe+'efiles/';
    cmdout=write_read_cmd(['ls', efilespath,'-t']);
    mysummary=cmdout.splitlines();
    return mysummary

def start_client(serveraddress,refreshTime):   
    s = socket.socket();
    s.settimeout(refreshTime);     
    s.connect((serveraddress,9999));
    return s; 

def receive_server_summary_vector(s,maxsize,refreshTime):
    s.settimeout(refreshTime);
    try:
        presummary = s.recv(maxsize);
    except:
        return True,"";      
    try:
        s.send('ACK0'.encode('utf-8'));
    except:
        return True,"";  
    s.settimeout(refreshTime);  
    try:
        ecommand = s.recv(maxsize);
    except:
        return True,"";  
    if len(ecommand)==0:
        return True,"";
    while ecommand!='1c':
        try:
            s.send('ACK0'.encode('utf-8'));
        except:
            return True,"";
        presummary+=ecommand;
        s.settimeout(refreshTime);
        try:
            ecommand = s.recv(maxsize);
        except:
            return True,"";
        if len(ecommand)==0:
            return True,"";
    serversummary=presummary.splitlines();
    return False,serversummary;

def get_flags(serversummary,mypkj,val):
    ind=mypkj.find('i');
    realname=mypkj[0:ind];
    ismissing=True;
    for text in serversummary:
        if realname in text:
            ismissing=False;
            break;
    indd=mypkj.find('d');
    dest=int(mypkj[0:indd]);
    indj=mypkj.find('j');
    jump=int(mypkj[ind+1:indj]);
    isdestination=dest==val;
    isnotlastjump=jump>1;
    return ismissing,isdestination,isnotlastjump;     

def send_file(s,mypkj,pathe,refreshTime):
    try:
        s.send(mypkj.encode('utf-8'));
    except:
        return True;
    s.settimeout(refreshTime);
    try:
        eanswer=s.recv(4);
    except:
        return True; 
    if eanswer !='ACK0':
        return True;
    f = open (pathe+'efiles/'+mypkj, "r");
    l = f.read();
    f.close();
    try:
        s.send(l.encode('utf-8'));
    except:
        return True;
    s.settimeout(refreshTime);
    try:
        eanswer=s.recv(4);
    except:
        return True; 
    if eanswer !='ACK0':
        return True;       
    return False;
    
def sendCommand(s,commande,refreshTime):
    try:
        s.send(commande.encode('utf-8'));
    except:
        return True;
    s.settimeout(refreshTime);
    try:
        eanswer=s.recv(4);
    except:
        return True;
    if eanswer !='ACK0':
        return True;
    return False;  
                               
def sendPkj(pathe,serveraddress,val,refreshTime,maxsize,sincronizetime):
    time.sleep(sincronizetime);
    mysummary=get_my_summary_vector(pathe);
    try:
        s=start_client(serveraddress,refreshTime);
    except:
        return True;
    failflag,serversummary = receive_server_summary_vector(s,maxsize,refreshTime);   
    if failflag:
        s.shutdown(1);
        s.close();
        return True;
    print ("summary received");
    i=0;
    while (i<len(mysummary)):
        ismissing,isdestination,isnotlastjump=get_flags(serversummary,mysummary[i],val);
        if (ismissing and (isdestination or isnotlastjump)):
            failflag=send_file(s,mysummary[i],pathe,refreshTime);
            if failflag:
                s.shutdown(1);
                s.close();
                return True;
            ####################################
            event_record.addEvent(12,val);
            print 'Sent package '+mysummary[i];
            ####################################
        i+=1;  
    failflag=sendCommand(s,"0c",refreshTime);
    if failflag:
        s.shutdown(1);
        s.close();        
        return True;
    s.shutdown(1);
    s.close();
    return False;
    