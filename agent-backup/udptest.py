import datetime
import asyncore
import os
import socket
import threading

import signal

import sys

import wpactrl
import time
agent_client =socket.socket(socket.AF_INET,socket.SOCK_STREAM)
agent_server =socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

class AgentClient(asyncore.dispatcher):

    def __init__(self,host,port):
        asyncore.dispatcher.__init__(self)
        self.write_buffer = ''
        self.recv_buffer = ''
        self.wpa_intefaces=[]
        self.wpa_intefaces.append(self.start_wpa('/var/run/hostapd/wlan1'))
        self.set_socket(agent_client)
        self.init_connection(host,port)

    def init_connection(self,host,port):
        try:
            self.connect((host,port))
        except socket.error:
            pass
        wpa=self.wpa_intefaces[0]
        resp=wpa.status()
        type = 'STATUS'
        phy=resp.phy
        channel=resp.channel
        ifname=resp.bss_0
        bssid=resp.bssid_0
        ssid=resp.ssid_0
        portId='1'
        obj=type+' '+phy+' '+channel+' '+ifname+' '+bssid+' '+ssid+' '+portId
        self.send_msg(obj)

    def start_wpa(self,path):
        wpa=wpactrl.WPACtrl(path)
        return wpa

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


class AgentServer(asyncore.dispatcher):

    def __init__(self,host,port):
        asyncore.dispatcher.__init__(self)
        self.set_socket(agent_server)
        self.set_reuse_addr()
        self.bind((host,port))

    def handle_read(self):
        data,addr = self.socket.recvfrom(1024)
        if not data:
            self.close()
        print datetime.datetime.now()
        print data
        agent_client.send(data)


class ClientThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        client=AgentClient('192.168.109.144',6677)
        asyncore.loop(timeout=1)


class ServerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        server = AgentServer('localhost',6688)
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

def sigint_handler(signum, frame):
    print 'catched interrupt signal!'
    agent_client.close()
    agent_server.close()
    exit(0)

if __name__ =="__main__":
    Watcher()
    ct=ClientThread()
    ct.start()
    time.sleep(1)
    st=ServerThread()
    st.start()




