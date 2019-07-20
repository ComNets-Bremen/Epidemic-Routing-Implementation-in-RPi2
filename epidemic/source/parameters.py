#General parameters for the network protocol

#Time out for WDT
timeout=15;
backoff=5;
retryTime=5;

#TCP parameters
serverPort=9999;
bufferSize=1024;
ClientDelay=1;

#Neighbor caducity time
timeCaducity=240;

#Codes for message definition
endCode=bytes("aaa",'utf8');
breakMessage=bytes("bbb",'utf8');
breakName=bytes("+",'utf8');
nullCode=bytes("ddd",'utf8');
summaryCode=bytes("eee",'utf8');
requestCode=bytes("fff",'utf8');
messagesCode=bytes("ggg",'utf8');
#Type of messages
SUMMARY=0;
REQUEST=1;
MESSAGES=2;
ERROR=3;
TYPES=["Summary","Request","Messages","Empty"];

#TCP ROLES
SERVER=0;
CLIENT=1;

#Type of transport actions
BREAK=0;
CONTINUE=1;

#States
SEARCH=0;
CONNECT=1;
TRANSPORT=2;
STATES=["Search","Connect","Transport"];

#Network Address class A
netIp="10";

#Minimum RSSI
MINRSSI=-50;

#Intended Mac not connected device
FREEINTENDED='00:00:00:00:00:00';

#File system
pathe='/home/alarm/epidemic';

#GPS baudrate
gnssBaudrate=4800;
#Time Zone for GNSS
timeZone=2; #Germany
#Codes to parse GNSS sentences
gnssInstruction=bytes("$GPGGA",'utf-8');
gnssDelimeter=bytes(",",'utf-8');
gnssEndCode=bytes('\n','utf-8');

#Timer for periodic tasks
sleepMainLoop=2;
#WPA initialization delay
sleepStart=1;

#Debug parameters
saveTime=60;    #Time to save log files
recordEvents=True;  #Save in lof files events related with the epidemic protocol
resetFileSystem=True;   #Clean epidemic buffer and set initial messages
recordPositions=True;   #Saves geographical position (Requises GNSS device)
syncGNSSclock=True; #Syncronizes the device's clock (Requises GNSS device)
