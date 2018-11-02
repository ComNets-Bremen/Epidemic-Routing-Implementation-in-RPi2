import serial
import io
import os
import numpy as np
import threading

class USB_GPS (threading.Thread):
    def loadParameters(self,time,pathe):
        self.time=time;
        self.pathe=pathe;
                 
    def readGPS(self,time,i):
        lstart=i;
        while i<lstart+time:
            ind=-1;
            while ind<0:
                gpsline = self.sio.readline();
                gpsstr = gpsline.encode('ascii','ignore');
                ind=gpsstr.find("$GPGGA,");   
            gpsnorth=float(gpsstr[18:27]);
            gpseast=float(gpsstr[30:39]);
            gpsseconds=int(gpsstr[7:9])*3600+int(gpsstr[9:11])*60+int(gpsstr[11:13]);
            self.positions[i,0]=gpsseconds;
            self.positions[i,1]=gpseast;
            self.positions[i,2]=gpsnorth;
            i+=1;
            
    def clockSincronize(self):
        ind=-1;
        while ind<0:
            gpsline = self.sio.readline();
            gpsstr = gpsline.encode('ascii','ignore');
            ind=gpsstr.find("$GPGGA,");        
        os.system("sudo date --set='"+gpsstr[7:9]+":"+gpsstr[9:11]+":"+gpsstr[11:13]+"'"); 
           
    def generateMobility(self,time):
        self.positions=np.zeros((time,3));
        self.readGPS(time,0);
        
    def updateMobility(self,time):
        plength=self.positions.shape[0];
        self.positions.resize(plength+time, 3);
        self.readGPS(time,plength);
        try:
            np.savetxt(self.pathe+'logs/log/positions'+str(self.positions[-1,0])+'.csv', self.positions, fmt='%.18g', delimiter=' ', newline=os.linesep);
        except:
            pass;  
    
    def __init__(self):
        self.ser = serial.Serial('/dev/ttyACM0');
        self.ser.baudrate = 4800;
        self.sio = io.TextIOWrapper(io.BufferedRWPair(self.ser, self.ser)); 
        self.sio.flush();
        self.clockSincronize();
        threading.Thread.__init__(self);
    
    def run(self):
        self.generateMobility(self.time);
        while True:
            self.updateMobility(self.time);       
