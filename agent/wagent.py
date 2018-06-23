import re
import json
import time
import threading
import asyncore, socket
import subprocess
import wpactrl
import datetime
import signal
SERVER_IP = '192.168.109.144'
SERVER_PORT = 6677
is_sigint_up = False

class Client(asyncore.dispatcher):
    def __init__(self):
        asyncore.dispatcher.__init__(self)
        self.wpa_intefaces=[]
        self.wpa_intefaces.append(self.start_wpa('/var/run/hostapd/wlan1'))
        self.write_buffer = ''
        self.recv_buffer = ''
        self.init_connection()
        self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.sock.bind(('localhost',6688))
        self.thread = threading.Thread(target=self.event_listen)
        self.thread.daemon=True
        self.thread.start()
    def start_wpa(self,path):
        wpa=wpactrl.WPACtrl(path)
        return wpa

    def init_connection(self):
        try:
            self.create_socket(socket.AF_INET,socket.SOCK_STREAM)
        except socket.error:
            pass
        try:
            self.connect((SERVER_IP,SERVER_PORT))
        except socket.error:
            pass
        wpa=self.wpa_intefaces[0]
        resp=wpa.status()
        type = 'status'
        phy=resp.phy
        channel=resp.channel
        ifname=resp.bss_0
        bssid=resp.bssid_0
        ssid=resp.ssid_0
        obj=type+' '+phy+' '+channel+' '+ifname+' '+bssid+' '+ssid
        self.send_msg(obj)
    def event_listen(self):
        while True:
            data,addr=self.sock.recvfrom(1024)
            if not data:
                break
            print data
            data=data.split()
            event_name=data[0]
            {
                'AP-STA-CONNECTED':self.client_connect,
                'AP-STA-DISCONNECTED':self.client_disconnect
            }[event_name](*data[1:])
        self.sock.close()

    def send_msg(self,msg):
        self.write_buffer +=msg


    def client_connect(self,mac):
        print 'connect', mac
        obj = 'client_connect'+' '+mac+'\n'
        self.send_msg(obj)

    def client_disconnect(self,mac):
        print 'disconnect',mac
        obj = 'client_disconnect'+' '+mac+'\n'
        self.send_msg(obj)

    """
    def wpa_ctrl(self,wpa):
        while True:
            if wpa.pending():
                evt=wpa.recv(1024)
                if not evt:
                    print 'Breaking no events'
                    break
                args = evt.split()
                if args[0][0:3]=='<3>':
                    event_name = args[0][3:]
                    {
                        'AP-STA-CONNECTED': self.client_connect,
                        'AP-STA-DISCONNECTED': self.client_disconnect
                    }[event_name](*args[1:])
    """

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
        self.init_connection()

    def handle_close(self):
        print 'Handling connection disconnect, reconnecting ...'
        self.close()
        self.init_connection()

    def terminate(self):
        self.sock.close()
        self.close()


client=Client()

def sigint_handler(signum, frame):
    global client
    client.terminate()
    print 'catched interrupt signal!'

signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGHUP, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)

asyncore.loop(timeout=1)


