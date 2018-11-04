#!/usr/bin/python
#Run as sudo
import dbus
import os
from gi.repository import GObject as gobject
import threading
from dbus.mainloop.glib import DBusGMainLoop
from subprocess import check_output
import datetime
import event_record
import usbgps
import eclient
import eserver

def find_in_list(element, list_element):
    try:
        index_element = list_element.index(element)
        return index_element
    except ValueError:
        return -1
            
def write_read_cmd(list_command):
    out = check_output(list_command)
    return out   
                             
def ini_wpa(pathe):
    #Initialize wpa_supplicant
    f = open(pathe+'p2pfiles/p2p.conf','r')
    fout=f.read();
    inde=fout.find('EPI');
    indd=fout.find('DEMIC');
    myVal=int(fout[inde+3:indd]);
    #os.system("sudo rm /var/run/wpa_supplicant/wlan0 -f");
    #os.system("sudo killall wpa_supplicant");
    os.system("sudo wpa_supplicant -i wlan0 -c "+pathe+"p2pfiles/p2p.conf -Dnl80211 -B -u");
    return myVal;
     
class P2P_EVENT (threading.Thread):
    # Needed Variables
    global bus
    global wpas_object
    global interface_object
    global p2p_interface
    global interface_name
    global wpas
    global wpas_dbus_interface
    global timeout
    global path
    # Dbus Paths
    global wpas_dbus_opath
    global wpas_dbus_interfaces_opath
    global wpas_dbus_interfaces_interface
    global wpas_dbus_interfaces_p2pdevice   
    # Required Signals
    def deviceFound(self,devicepath):
        self.WDTreset=datetime.datetime.now();
        mac=devicepath[-12:];
        MAC=mac[0:2]+":"+mac[2:4]+":"+mac[4:6]+":"+mac[6:8]+":"+mac[8:10]+":"+mac[10:12]; #get mac address
        if self.Formation_pending==False:
            cmdout=write_read_cmd(['sudo', 'wpa_cli','p2p_peer',MAC]);
            inde=cmdout.find('EPI'); 
            if inde != -1: #same kind?
                indd=cmdout.find('DEMIC');
                val=int(cmdout[inde+3:indd]);
                ####################################
                event_record.addEvent(0,val);
                print "Device found"+str(val);
                ####################################
                if (self.myVal<val):
                    ind=find_in_list(val, self.VALlist);
                    if ind == -1: #perr was not visted in a short time
                        self.val=val;
                        self.MAC=MAC;
                        self.WDTreset=datetime.datetime.now();     
                        self.Formation_pending=True;
                        cmdout=write_read_cmd(['sudo','wpa_cli','p2p_connect',MAC,'pbc','go_intent=15']);
                        ####################################
                        event_record.addEvent(1,self.val);
                        print "Request to:"+str(self.val);
                        ####################################
                        
    def goNegotiationRequest(self,devicepath,password,gointent): 
        if self.Formation_pending==False:
            mac=devicepath[-12:];
            MAC=mac[0:2]+":"+mac[2:4]+":"+mac[4:6]+":"+mac[6:8]+":"+mac[8:10]+":"+mac[10:12]; #get mac address
            self.WDTreset=datetime.datetime.now();
            cmdout1=write_read_cmd(['sudo', 'wpa_cli','p2p_peer',MAC]);
            inde=cmdout1.find('EPI');           
            indd=cmdout1.find('DEMIC');
            self.val=int(cmdout1[inde+3:indd]);
            self.MAC=MAC; 
            self.WDTreset=datetime.datetime.now();
            self.Formation_pending=True;
            os.system('sudo wpa_cli p2p_connect '+ MAC + ' pbc go_intent=0');
            ####################################
            event_record.addEvent(2,self.val);            
            print "Accept to:"+str(self.val);
            ####################################
        else:
            ####################################
            event_record.addEvent(3,-1); 
            print "Ignore request";
            ####################################
        print password;
        print gointent;
            
    def GONegotiationSuccess(self,status):
        self.WDTreset=datetime.datetime.now();
        print "Go Negotiation Success"
        print status;
    
    def GroupStarted(self,properties):
        if properties.has_key("group_object"):
            self.WDTenable=False;   #turn of WDT
            os.system("sudo wpa_cli p2p_stop_find");    #Avoid other peers to try to connect
            cmdout=write_read_cmd(['sudo', 'wpa_cli','interface']);
            interfaces=cmdout.splitlines();
            self.interface=interfaces[2];
            if (self.myVal<self.val):
                try:
                    os.system("sudo ifconfig "+self.interface+" 192.168.1.1 netmask 255.255.255.0 up");
                except:
                    os.system("sudo wpa_cli p2p_group_remove "+self.interface);
                    self.WDTreset=datetime.datetime.now();
                    self.WDTenable=True;
                    ####################################
                    event_record.addEvent(6,self.val);                    
                    print "Failed connection with:"+str(self.val);
                    ####################################
                else:
                    ####################################
                    event_record.addEvent(4,self.val);
                    print "Mode 1 connection with:"+str(self.val);
                    ####################################
                    ####################Data exchange###########################
                    broken_link=eserver.receivePkj(self.pathe, "192.168.1.1", self.myVal,self.val,self.refresh,self.maxsize); #I am 192.168.1.1
                    if broken_link==False:
                        broken_link=eclient.sendPkj(self.pathe,"192.168.1.2",self.val,self.refresh,self.maxsize,self.sincronizetime);
                    ####################Data exchange###########################
                    self.CloseConnection(broken_link);
            else:
                try:
                    os.system("sudo ifconfig "+self.interface+" 192.168.1.2 netmask 255.255.255.0 up");
                except:
                    os.system("sudo wpa_cli p2p_group_remove "+self.interface);
                    self.WDTreset=datetime.datetime.now();
                    self.WDTenable=True;
                    ####################################
                    event_record.addEvent(6,self.val);                    
                    print "Failed connection with:"+str(self.val);
                    ####################################
                else:
                    ####################################
                    event_record.addEvent(5,self.val);
                    print "Mode 2 connection with:"+str(self.val);
                    ####################################
                    ####################Data exchange###########################
                    broken_link=eclient.sendPkj(self.pathe,"192.168.1.1",self.val,self.refresh,self.maxsize,self.sincronizetime);
                    if broken_link==False:
                        broken_link=eserver.receivePkj(self.pathe, "192.168.1.2", self.myVal,self.val,self.refresh,self.maxsize); #I am 192.168.1.2
                    ####################Data exchange###########################                    
                    self.CloseConnection(broken_link);
   
    def GroupFinished(self,status):
        efilespath=self.pathe+'efiles/';
        myfilespath=self.pathe+'myfiles/';
        self.checkPkj(efilespath,myfilespath,self.maxpkj);
        self.WDTreset=datetime.datetime.now();
        self.WDTenable=True;
        self.Formation_pending=False; 
        #Get summary list
        cmdout=write_read_cmd(['ls', efilespath,'-t']);
        mysummary1=cmdout.splitlines();
        cmdout=write_read_cmd(['ls', myfilespath,'-t']);
        mysummary2=cmdout.splitlines();
        ####################################
        event_record.saveSummary(', '.join(mysummary1+mysummary2));
        print 'Summary vector'
        print ', '.join(mysummary1+mysummary2);
        ####################################
        #Restart search
        self.WDTreset=datetime.datetime.now();
        self.WDTenable=True;
        os.system("sudo wpa_cli p2p_flush");
        os.system("sudo wpa_cli p2p_find");
        ####################################
        event_record.addEvent(9,self.val); 
        print "Disconnected from:"+str(self.val);
        ####################################
        ####################################
        event_record.saveEvents();
        ####################################        
        print status;
    
    def GONegotiationFailure(self,status):
        self.WDTreset=datetime.datetime.now();
        print 'Go Negotiation Failed. Status:'
        print format(status)
    
    def WpsFailure(self,status, etc):
        self.WDTreset=datetime.datetime.now();
        print "WPS Authentication Failure".format(status)
        print etc
    
    def deviceLost(self,devicepath):
        self.WDTreset=datetime.datetime.now();
        print "Device lost: %s" % (devicepath)
    #General functions 
    def CloseConnection(self,broken_link):
        os.system("sudo wpa_cli p2p_group_remove "+self.interface);                    
        if broken_link==False:
            if len(self.VALlist)>(self.visitlimit-1):
                ####################################
                event_record.addEvent(11,self.VALlist[-1]); 
                print "Device erased"+str(self.VALlist[-1]);
                ####################################
                self.VALlist.pop();
                self.Timelist.pop();                      
            contactTime=datetime.datetime.now();
            self.VALlist.insert(0, self.val);
            self.Timelist.insert(0, contactTime);
            self.WDTreset=datetime.datetime.now();
            self.WDTenable=True;
            ####################################
            event_record.addEvent(7,self.val);                              
            print "Completed communication with:"+str(self.val);
            ####################################
            ####################################
            event_record.saveList(self.VALlist);
            ####################################
        else:
            self.WDTreset=datetime.datetime.now();
            self.WDTenable=True;
            ####################################
            event_record.addEvent(8,self.val);
            print "Interrupted communication with:"+str(self.val);
            ####################################          
    
    def remove_incomplete(self,pathE):
        cmdout=write_read_cmd(['ls', pathE,'-t']);
        summaryE=cmdout.splitlines();
        i=0;
        while i<len(summaryE):
            realsize=os.path.getsize(pathE+summaryE[i]);
            indj=summaryE[i].find('j');
            inds=summaryE[i].find('s');
            originalsize=int(summaryE[i][indj+1:inds]);
            if realsize != originalsize:
                os.system('rm '+ pathE+summaryE[i]+' -f');
                print 'Delete incomplete package '+summaryE[i];
            i=i+1; 
                  
    def checkPkj(self,epath,mpath,maxPkj):
        self.remove_incomplete(mpath);
        self.remove_incomplete(epath);
        cmdout=write_read_cmd(['ls', epath,'-t']);
        mysummary1=cmdout.splitlines();
        if maxPkj<len(mysummary1):
            i=maxPkj;
            while i<len(mysummary1):
                os.system('rm '+ epath+mysummary1[i]+' -f');
                ####################################
                event_record.addEvent(14,-1);
                print 'Delete old package '+mysummary1[i];
                ####################################
                i=i+1;
            
    def removeConnection(self):
        cmdout=write_read_cmd(['sudo', 'wpa_cli','interface']);
        interfaces=cmdout.splitlines();
        interface=interfaces[2];
        os.system("sudo wpa_cli p2p_group_remove "+interface);  
          
    def WDTinterruption(self):
        self.removeConnection();
        self.Formation_pending=False; 
        os.system("sudo wpa_cli p2p_flush");
        os.system("sudo wpa_cli p2p_find");
        self.WDTreset=datetime.datetime.now();
        ####################################
        event_record.addEvent(10,-1); 
        print "time out";
        ####################################

    def getParameters(self,pathe,myVal):
        self.WDTenable=False;
        self.Formation_pending=True; 
        #Initialize wpa_supplicant
        f = open(pathe+'p2pfiles/epidemic.xml','r')
        fout=f.read();
        sp=fout.find('<peerlife>');
        sv=fout.find('<visitlimit>');
        sm=fout.find('<maxpkj>');
        sr=fout.find('<refresh>');
        sb=fout.find('<buffer>');
        st=fout.find('<synchronization>');
        fp=fout.find('</peerlife>');
        fv=fout.find('</visitlimit>');
        fm=fout.find('</maxpkj>');
        fr=fout.find('</refresh>');
        fb=fout.find('</buffer>');
        ft=fout.find('</synchronization>');
        self.pathe=pathe;
        self.myVal=myVal;
        self.peerlife=int(fout[sp+10:fp]);
        self.visitlimit=int(fout[sv+12:fv]);
        self.maxpkj=int(fout[sm+8:fm]);
        self.refresh=int(fout[sr+9:fr]);
        self.maxsize=int(fout[sb+8:fb]);
        self.sincronizetime=int(fout[st+17:ft]);
        #Get summary list
        efilespath=self.pathe+'efiles/';
        myfilespath=self.pathe+'myfiles/';
        cmdout=write_read_cmd(['ls', efilespath,'-t']);
        mysummary1=cmdout.splitlines();
        cmdout=write_read_cmd(['ls', myfilespath,'-t']);
        mysummary2=cmdout.splitlines();
        ####################################
        event_record.saveSummary(', '.join(mysummary1+mysummary2));
        print 'Summary vector'
        print ', '.join(mysummary1+mysummary2);
        ####################################
    # Check Time List
    def tlistUpdate(self):
        contactTime=datetime.datetime.now();
        i=0;
        while i<len(self.Timelist):
            td=contactTime-self.Timelist[i];
            td_sec=int(round(td.total_seconds()));
            if td_sec>self.peerlife: #visited not recently
                ####################################
                event_record.addEvent(11,self.VALlist[i]); 
                print "Device erased:"+str(self.VALlist[i]);
                ####################################
                self.VALlist.pop(i); #Remove from list
                self.Timelist.pop(i);
                ####################################
                event_record.saveList(self.VALlist);
                ####################################
            i=i+1;
        if self.WDTenable==True:
            td=contactTime-self.WDTreset;
            td_sec=int(round(td.total_seconds()));
            if td_sec>self.refresh:
                self.WDTinterruption();
                ####################################
                event_record.saveEvents();
                ####################################
    # Constructor
    def __init__(self):
        #Initial Visited lists
        self.VALlist=[-1];
        self.Timelist=[datetime.datetime.now()];
        # Initializes variables and threads
        self.interface_name = 'wlan0'
        self.wpas_dbus_interface = 'fi.w1.wpa_supplicant1'
        # Initializes thread and daemon allows for ctrl-c kill
        threading.Thread.__init__(self)
        self.daemon = True
        # Generating interface/object paths
        self.wpas_dbus_opath = "/" + \
                        self.wpas_dbus_interface.replace(".","/")
        self.wpas_wpas_dbus_interfaces_opath = self.wpas_dbus_opath + \
                        "/Interfaces"
        self.wpas_dbus_interfaces_interface = \
                        self.wpas_dbus_interface + ".Interface"
        self.wpas_dbus_interfaces_p2pdevice = \
                        self.wpas_dbus_interfaces_interface \
                        + ".P2PDevice"
        # Getting interfaces and objects
        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        self.wpas_object = self.bus.get_object(
                        self.wpas_dbus_interface,
                        self.wpas_dbus_opath)
        self.wpas = dbus.Interface(self.wpas_object,
                        self.wpas_dbus_interface)
        self.path = self.wpas.GetInterface(
                                self.interface_name)
        self.interface_object = self.bus.get_object(
                        self.wpas_dbus_interface, self.path)
        self.p2p_interface = dbus.Interface(self.interface_object,
                        self.wpas_dbus_interfaces_p2pdevice)
        #Adds listeners for find and lost
        self.bus.add_signal_receiver(self.deviceFound,
                dbus_interface=self.wpas_dbus_interfaces_p2pdevice,
                signal_name="DeviceFound");
        self.bus.add_signal_receiver(self.deviceLost,
                dbus_interface=self.wpas_dbus_interfaces_p2pdevice,
                signal_name="DeviceLost");
        self.bus.add_signal_receiver(self.goNegotiationRequest,
                dbus_interface=self.wpas_dbus_interfaces_p2pdevice,
                signal_name="GONegotiationRequest");
        self.bus.add_signal_receiver(self.GONegotiationSuccess,
                dbus_interface=self.wpas_dbus_interfaces_p2pdevice,
                signal_name="GONegotiationSuccess");
        self.bus.add_signal_receiver(self.GONegotiationFailure,
                dbus_interface=self.wpas_dbus_interfaces_p2pdevice,
                signal_name="GONegotiationFailure");
        self.bus.add_signal_receiver(self.GroupStarted,
                dbus_interface=self.wpas_dbus_interfaces_p2pdevice,
                signal_name="GroupStarted");
        self.bus.add_signal_receiver(self.WpsFailure,
                dbus_interface=self.wpas_dbus_interfaces_p2pdevice,
                signal_name="WpsFailed");
        self.bus.add_signal_receiver(self.GroupFinished,
                dbus_interface=self.wpas_dbus_interfaces_p2pdevice,
                signal_name="GroupFinished");   
    # Run P2P_EVENT
    def run(self):
        # Allows other threads to keep working while MainLoop runs
        gobject.MainLoop().get_context().iteration(True)
        gobject.threads_init();
        self.WDTreset=datetime.datetime.now();
        self.WDTenable=True;
        self.Formation_pending=False;       
        os.system("sudo wpa_cli p2p_find");
        gobject.MainLoop().run()
            
if __name__ == "__main__":
    pathe="/home/alarm/epidemic/";
    gpsSave=20;
    gpsusb = usbgps.USB_GPS();
    gpsusb.loadParameters(gpsSave, pathe)
    gpsusb.start();
    myVal=ini_wpa(pathe);
    event_record.iniEvents(pathe);
    p2p_catch_event = P2P_EVENT();
    p2p_catch_event.getParameters(pathe,myVal);
    p2p_catch_event.start();
    while(True):
        p2p_catch_event.tlistUpdate();
