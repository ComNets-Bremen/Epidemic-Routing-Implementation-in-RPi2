#!/usr/bin/python
#It perform the epidemic routing protocol on top of WiFi direct and TCP/IP
import routing as r;
import dbus;
from gi.repository import GObject as gobject;
import threading;
from dbus.mainloop.glib import DBusGMainLoop;
import parameters as p;
import cmd_functions as c;
import time;
import debug as d;
import random;
#It locks sensitive procesess
mutex=threading.Lock(); 
#It describes the signals and the main functions for the epidemic routing protocol
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
    #It is executed when a Neighbor discovery beacon is received
    def deviceFound(self,devicepath):
        mutex.acquire();
        try:
            if self.state==p.SEARCH:
                self.state,self.neighborID,self.neighborMAC,self.wdTimer=r.handle_deviceFound(devicepath,self.myID,self.neighborList,self.wdTimer,self.eventLog_ref);
        finally:
            mutex.release();
    #It is executed when a neighbor requests a connection
    def goNegotiationRequest(self,devicepath,password,gointent):
        mutex.acquire();
        try:
            if self.state==p.SEARCH:
                self.state,self.neighborID,self.neighborMAC,self.wdTimer=r.handle_goNegotiationRequest(devicepath,self.myID,self.wdTimer,self.eventLog_ref);
        finally:
            mutex.release();
    #It is executed when 2 devices agree in a channel and in the roles for Wi-Fi direct
    def GONegotiationSuccess(self,status):
        mutex.acquire();
        try:
            if self.state==p.CONNECT:
                cmdout=c.write_read_cmd(['sudo', 'wpa_cli','p2p_stop_find']);
        finally:
            mutex.release();
    #It is executed when the wi-fi network between the 2 devices is ready
    def GroupStarted(self,properties):
        mutex.acquire();
        try:
            if self.state==p.CONNECT:
                self.state=p.TRANSPORT;
                r.handle_GroupStarted(properties,self.myID,self.myAddress,self.neighborID,self.neighborMAC,self.neighborList,self.eventLog_ref);
                interface=r.get_direct_interface();
                if interface!=None:
                    cmdout=c.write_read_cmd(['sudo','wpa_cli','p2p_group_remove',interface]);
                self.state=p.SEARCH;
                cmdout=c.write_read_cmd(['sudo', 'wpa_cli','p2p_find']);
                self.wdTimer=time.time()+random.random()*p.backoff;
        finally:
            mutex.release();
    #It is executed when the wi-fi network is removed
    def GroupFinished(self,status):
        mutex.acquire();
        try:
            if self.state==p.SEARCH:
                cmdout=c.write_read_cmd(['sudo', 'wpa_cli','p2p_find']);
            elif self.state==p.CONNECT:
                self.state=p.SEARCH;
                cmdout=c.write_read_cmd(['sudo', 'wpa_cli','p2p_find']);
                self.wdTimer=time.time()+random.random()*p.backoff;
                if p.recordEvents:  #Execute only in debug mode
                    d.save_fail("Group-Finished",self.neighborID,self.eventLog_ref);
        finally:
            mutex.release();
    #It is executed when there was an syncronization error in the formation of a wi-fi network between the 2 devices
    def GONegotiationFailure(self,status):
        mutex.acquire();
        try:
            if self.state==p.SEARCH:
                cmdout=c.write_read_cmd(['sudo', 'wpa_cli','p2p_find']);
            elif self.state==p.CONNECT:
                self.state=p.SEARCH;
                cmdout=c.write_read_cmd(['sudo','wpa_cli','p2p_cancel']);
                interface=r.get_direct_interface();
                if interface!=None:
                    cmdout=c.write_read_cmd(['sudo','wpa_cli','p2p_group_remove',interface]);
                cmdout=c.write_read_cmd(['sudo', 'wpa_cli','p2p_find']);
                self.wdTimer=time.time()+p.backoff;
                if p.recordEvents:  #Execute only in debug mode
                    d.save_fail("Go-Negotiation-Failure",self.neighborID,self.eventLog_ref);
        finally:
            mutex.release();
    #It is executed when there was an autentification error in the formation of a wi-fi network between the 2 devices
    def WpsFailure(self,status, etc):
        mutex.acquire();
        try:
            if self.state==p.SEARCH or self.state==p.CONNECT:
                cmdout=c.write_read_cmd(['sudo', 'wpa_cli','p2p_find']);
            elif self.state==p.CONNECT:
                self.state=p.SEARCH;
                cmdout=c.write_read_cmd(['sudo', 'wpa_cli','p2p_find']);
                self.wdTimer=time.time()+random.random()*p.backoff;
                if p.recordEvents:  #Execute only in debug mode
                    d.save_fail("WPS-Failure",self.neighborID,self.eventLog_ref);
        finally:
            mutex.release();
    #It is executed when the device deletes a neighbor from its internal neighborlist
    def deviceLost(self,devicepath):
        mutex.acquire();
        try:
            pass;
        finally:
            mutex.release();
    #Main loop for periodic procesess
    def p2p_periodic(self):
        time.sleep(p.sleepMainLoop);
        mutex.acquire();
        try:
            self.state,self.wdTimer=r.checkWDT(self.state,self.wdTimer,self.neighborID,self.eventLog_ref);
            r.update_neighbor_list(self.neighborList);
            currentTime=time.time();
            if p.recordEvents:
                if currentTime>=self.lastSave+p.saveTime:
                    d.save_events(self.fIndex_ref,self.debugPath,self.eventLog_ref);
                    self.lastSave=time.time();
        finally:
            mutex.release();
        
    # Constructor. It starts the epidemic protocol and it registers the wpa_supplicant signals in the D-Bus
    def __init__(self):
        # Initializes variables and threads
        self.state=p.SEARCH;
        wifiPort,gnssPort=r.get_interfaces();
        self.interface_name=wifiPort;   #Wireless interface
        self.neighborList={};   #Dictionary {iD,time_last_contact}
        self.myID=r.get_myID(); #Device's identifier
        self.myAddress=r.build_ip(self.myID);   #Device's IP address
        self.neighborID=None;   #Neighbor's identifier
        self.neighborMAC=None;  #Neighbor's MAC layer
        #Debug variables
        eventLog="";   #Events log register
        self.eventLog_ref=[eventLog];
        fIndex=0;
        self.fIndex_ref=[fIndex];
        self.lastSave=time.time();
        #Reset epidemic messages
        if p.resetFileSystem:
            d.reset_messages();
        #Start Debug
        if p.syncGNSSclock or p.recordPositions or p.recordEvents:
            self.debugPath=d.create_debug_folder();
        if p.syncGNSSclock or p.recordPositions:
            ser=d.start_gnss(gnssPort);
        if p.syncGNSSclock:
            d.clockSincronize(ser);
        if p.recordPositions:
            gnssthread = threading.Thread(target = d.run_gnss,args=(ser,self.debugPath,mutex));
            gnssthread.start();
        #Start epidemic protocol    
        r.start_protocol(wifiPort); 
        self.wdTimer=time.time()+random.random()*p.backoff;
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
    # Run P2P_EVENT. It runs the epidemic protocol
    def run(self):
        # Allows other threads to keep working while MainLoop runs (It works poorly with GLib.MainLoop())
        gobject.MainLoop().get_context().iteration(True)
        gobject.threads_init();
        gobject.MainLoop().run();
            
#It calls the epidemic protocol
p2p_catch_event = P2P_EVENT();
p2p_catch_event.start();
while True:
    p2p_catch_event.p2p_periodic();
