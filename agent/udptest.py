import datetime
import asyncore
import os
import socket
import threading
import json
import signal
from argparse import ArgumentParser
import sys
from vap import VAP

import wpactrl
import time
CTRL_IP='192.168.109.144'
CTRL_PORT=6677
agent_client =socket.socket(socket.AF_INET,socket.SOCK_STREAM)
agent_server =socket.socket(socket.AF_INET,socket.SOCK_DGRAM)


def create_config_file(ifname,bssid,ssid):
    os.chdir('/etc/hostapd')
    file_name='hostapd-%s.conf' %ifname
    if os.path.exists(file_name):
        print "ERROR:'%s' already exists" %ifname
        return
    fobj=open(file_name,'w')
    line1 = "interface=%s\n" %ifname
    line2 = "ssid=%s\n" %ssid
    line3 = "ctrl_interface=/var/run/hostapd\n"
    line4 = "agent_port=6688\n"
    if bssid==None:
        line5 = "\n"
    else:
        line5 = "bssid=%s\n" %bssid
    fobj.writelines([line1,line2,line3,line4,line5])
    fobj.close()




class AgentClient(asyncore.dispatcher):

    def __init__(self,host,port,dpid,g_iface,iface):
        asyncore.dispatcher.__init__(self)
        self.host=host
        self.port=port
        self.dpid=dpid
        self.g_iface=g_iface
        self.global_wpa=self.start_wpa(self.g_iface)
        self.first_iface=iface
        self.write_buffer = ''
        self.recv_buffer = ''
        self.wpa_interfaces={}
        self.wpa_interfaces[iface]=VAP(self.first_iface)
        self.set_socket(agent_client)
        self.init_connection(self.host,self.port)

    def init_connection(self,host,port):
        try:
            self.connect((host,port))
        except socket.error:
            pass
        vap=self.wpa_interfaces[self.first_iface]
        resp=vap.status()
        type = 'STATUS'
        self.phy=resp.phy
        self.channel=resp.channel
        ifname=resp.bss_0
        bssid=resp.bssid_0
        ssid=resp.ssid_0
        portId='1'
        obj={
            'type':type,
            'phy':self.phy,
            'channel':self.channel,
            'ifname':ifname,
            'bssid':bssid,
            'ssid':ssid,
            'portId':portId
        }
        self.send_msg(obj)

    def start_wpa(self,path):
        wpa=wpactrl.WPACtrl(path)
        return wpa

    def send_msg(self,msg):
        self.write_buffer +=json.dumps(msg)+'\n'

    def writable(self):
        if not self.connected:
            return True
        return (len(self.write_buffer)>0)

    def handle_write(self):
        print datetime.datetime.now()
        sent = self.send(self.write_buffer)
        print 'send bytes',sent
        self.write_buffer =self.write_buffer[sent:]

    def handle_error(self):
        print 'Handling connection error, reconnecting ...'
        self.init_connection(self.host,self.port)

    def handle_close(self):
        print 'Handling connection disconnect, reconnecting ...'
        self.close()
        self.init_connection()

    def add_vap(self,ifname,ssid,bssid=None):
        create_config_file(ifname,ssid,bssid)
        cmd="ADD %s:/etc/hostapd/hostapd-%s.conf" %(self.phy,ifname)
        resp=self.global_wpa.request(cmd)
        if resp=="OK":
            self.wpa_interfaces[ifname] =VAP(ifname)
            return True
        else:
            return False

    def remove_vap(self,ifname):
        os.chdir("/etc/hostapd")
        file_name="/etc/hostapd/hostapd-%s.conf" %ifname
        cmd="REMOVE %s" %ifname
        resp=self.global_wpa.request(cmd)
        if resp=="OK":
            if os.path.exists(file_name):
                os.remove(file_name)
                del self.wpa_interfaces[ifname]
            return True
        else:
            return False


class AgentServer(asyncore.dispatcher):

    def __init__(self,host,port):
        asyncore.dispatcher.__init__(self)
        self.set_socket(agent_server)
        self.set_reuse_addr()
        self.bind((host,port))
        self.write_buffer=''
    def handle_read(self):
        data,addr = self.socket.recvfrom(1024)
        if not data:
            self.close()
        print datetime.datetime.now()
        print data
        msg=data.split(' ')
        print msg[0]
        obj={
            'type':msg[0],
            'bssid':msg[1],
            'client':msg[2]
        }
        self.send_msg(obj)

    def send_msg(self,msg):
        msg_buffer=''
        msg_buffer+=json.dumps(msg)+'\n'
        agent_client.send(msg_buffer)

    def writable(self):
        if not self.connected:
            return True
        return (len(self.write_buffer)>0)


class ClientThread(threading.Thread):
    def __init__(self,ip,port,dpid,g_iface,iface):
        threading.Thread.__init__(self)
        self.ip=ip
        self.port=int(port)
        self.dpid=dpid
        self.g_iface=g_iface
        self.iface=iface
    def run(self):
        client=AgentClient(self.ip,self.port,self.dpid,self.g_iface,self.iface)
        asyncore.loop(timeout=1)


class ServerThread(threading.Thread):
    def __init__(self,port):
        threading.Thread.__init__(self)
        self.port=port
    def run(self):
        server = AgentServer('localhost',int(self.port))
        asyncore.loop(timeout=1)


class Watcher():

    def __init__(self):
        self.child = os.fork()
        if self.child == 0:
            return
        else:
            self.watch()

    def watch(self):
        try:
            os.wait()
        except KeyboardInterrupt:
            self.kill()
        sys.exit()

    def kill(self):
        try:
            agent_server.close()
            agent_client.close()
            os.kill(self.child, signal.SIGKILL)
        except OSError:
            pass

#def sigint_handler(signum, frame):
#    print 'catched interrupt signal!'
#    agent_client.close()
#    agent_server.close()
#    exit(0)

if __name__ =="__main__":
    """Parse the command line and set the callbacks."""
    usage ="%s [options]" %sys.argv[0]
    parser = ArgumentParser(usage=usage)
    parser.add_argument("-c","--ctrl",dest="ctrl",default=CTRL_IP,help="Controller address;default=%s" %CTRL_IP)
    parser.add_argument("-p","--port",dest="port",default=CTRL_PORT,type=int,help="Controller port;default=%u" %CTRL_PORT)
    parser.add_argument("-d","--dpid",dest="dpid",default=1,type=int,help="Switch dpdi;default=1")
    parser.add_argument("-g","--global-interface",dest="g_iface",default=None,help="Hostapd global control interface")
    parser.add_argument("-i","--iface",dest="iface",default="wlan0",help="first wifi interface name;default=wlan0")
    parser.add_argument("-l","--listen",dest="listen",default=6688,help="listen port for hostapd;default=6688")
    (args, _) = parser.parse_known_args(sys.argv[1:])

    Watcher()
    ct=ClientThread(args.ctrl,args.port,args.dpid,args.g_iface,args.iface)
    ct.start()
    time.sleep(1)
    st=ServerThread(args.listen)
    st.start()




