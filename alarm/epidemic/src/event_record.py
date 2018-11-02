import datetime
import numpy as np
import os

def iniEvents(pathe):
    global events;
    global epath;
    epath = pathe;    
    time = (datetime.datetime.now() - datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds();
    events= np.array([time,15,-1]);  #Start event

def saveList(vlist):
    time = (datetime.datetime.now() - datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds();
    with open(epath+'logs/log/visitedlist/'+str(time), "w") as f:
        for s in vlist:
            f.write(str(s) +" ");
            
def saveSummary(summary):
    time = (datetime.datetime.now() - datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds();
    text_file = open(epath+'logs/log/summary/'+str(time), "w");
    text_file.write(summary);
    text_file.close();
    
def addEvent(etype,device):
    global events;
    time = (datetime.datetime.now() - datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds();
    event=np.array([time,etype,device]);
    events=np.vstack([events, event]);

def saveEvents():
    try:
        np.savetxt(epath+'logs/log/events'+str(int(events[-1,0]))+'.csv', events, fmt='%.18g', delimiter=' ', newline=os.linesep);
    except:
        pass;
    