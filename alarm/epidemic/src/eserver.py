import socket;
from subprocess import check_output
import os
import re
import event_record

def secure_filename(path):
    _split = re.compile(r'[\0%s]' % re.escape(''.join([os.path.sep, os.path.altsep or ''])));
    return _split.sub('', path);

def write_read_cmd(list_command):
    out = check_output(list_command)
    return out  

def get_my_summary_vector(pathe):
    efilespath=pathe+'efiles/';
    myfilespath=pathe+'myfiles/';
    mysummary1=write_read_cmd(['ls', efilespath,'-t']);
    mysummary2=write_read_cmd(['ls', myfilespath,'-t']);
    return mysummary1+mysummary2

def start_server(serveraddress,refreshTime):
    s = socket.socket();
    s.settimeout(refreshTime)
    s.bind((serveraddress,9999));
    s.listen(1);
    sc, address = s.accept();
    sc.settimeout(refreshTime);
    print address;
    return s,sc

def receive_command(sc,refreshTime):
    sc.settimeout(refreshTime);
    try:    
        ecommand = sc.recv(32);
    except:
        return True,"",False,False;
    if len(ecommand)==0:
        return True,"",False,False;
    try:     
        sc.send('ACK0'.encode('utf-8'));
    except:
        return True,"",False,False;
    iscommand=ecommand=='0c';
    ind=ecommand.find('.dat');
    isname=ind>0;
    return False,ecommand,isname,iscommand;
    
def process_name(prename,myval,pathe):
    ind=prename.find('i');
    indd=prename.find('d');
    dest=int(prename[0:indd]);
    indj=prename.find('j');
    jump=int(prename[ind+1:indj])-1;
    inds=prename.find('s');
    psize=int(prename[indj+1:inds]);
    newname=prename[0:ind+1]+str(jump)+prename[indj:];
    ename=secure_filename(newname);   
    if dest==myval:
        epath=pathe+"myfiles/"+ename;
    else:
        epath=pathe+"efiles/"+ename;
    return epath,psize;

def receive_file(sc,epath,psize,refreshTime):
    sc.settimeout(refreshTime);
    try:
        l = sc.recv(psize);
    except:
        return True;
    if len(l)==0:
        return True;
    try:
        sc.send('ACK0'.encode('utf-8'));
    except:
        return True;        
    f = open(epath,'w');
    f.write(l);
    f.close();
    return False; 

def send_summary(sc,mysummary,maxsize,refreshTime):    
    ssize=len(mysummary);
    while ssize>maxsize:
        try:
            sc.send(mysummary[0:maxsize].encode('utf-8'));
        except:
            return True;
        sc.settimeout(refreshTime);
        try:            
            eanswer=sc.recv(4);
        except:
            return True;
        if eanswer !='ACK0':
            return True;        
        mysummary=mysummary[maxsize:];
        ssize=len(mysummary);
    if ssize>0:
        try:
            sc.send(mysummary.encode('utf-8'));
        except:
            return True;
        sc.settimeout(refreshTime);
        try:            
            eanswer=sc.recv(4);
        except:
            return True;
        if eanswer !='ACK0':
            return True;  
    try:
        sc.send('1c'.encode('utf-8'));
    except:
        return True;
    return False;
           
def receivePkj(pathe,serveraddress,myval,val,refreshTime,maxsize):
    mysummary=get_my_summary_vector(pathe);
    if mysummary=="":
        mysummary="none";  
    try:      
        s,sc=start_server(serveraddress,refreshTime);
    except:
        return True;
    failflag=send_summary(sc,mysummary,maxsize,refreshTime);
    if failflag:
        s.shutdown(1);
        s.close();
        return True;
    print ("summary sent");
    iscommand=False;
    while (iscommand==False):
        failflag,ecommand,isname,iscommand=receive_command(sc,refreshTime);
        if failflag:
            s.shutdown(1);
            s.close();
            print ("command fail");
            return True;        
        if isname:
            epath,psize=process_name(ecommand,myval,pathe);
            failflag=receive_file(sc,epath,psize,refreshTime);
            if failflag:
                s.shutdown(1);
                s.close();
                print ("file fail");
                return True;
            ####################################
            event_record.addEvent(13,val);
            print 'Reeceived package '+ecommand;
            ####################################
    s.shutdown(1);
    s.close();
    return False;
