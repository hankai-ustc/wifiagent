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
        self.init_connection()
        self.threads=[]
        self.thread = threading.Thread(target=self.wpa_ctrl)
        self.thread.daemon=True
        self.thread.start()

    def init_connection(self):
        try:
            self.create_socket(socket.AF_INET,socket.SOCK_STREAM)
        except socket.error:
            pass
        try:
            self.connect((SERVER_IP,SERVER_PORT))
        except socket.error:
            pass
        self.write_buffer = ''
        self.recv_buffer = ''

    def send_msg(self,msg):
        self.write_buffer +=msg


    def client_connect(self,mac):
        print 'connect', mac
        #obj = {
        #    'type':'client_connect',
        #    'client':mac
        #}
        obj = 'client_connect'+' '+mac+'\n'
        self.send_msg(obj)

    def client_disconnect(self,mac):
        print 'disconnect',mac
        #obj = {
        #    'type':'client_disconnect',
        #    'client':mac
        #}
        obj = 'client_disconnect'+' '+mac+'\n'
        self.send_msg(obj)

    def wpa_ctrl(self):
        wpa = wpactrl.WPACtrl('/var/run/hostapd-phy0/wlan0')
        wpa.attach()
        config=wpa.get_config()
        print('Bssid:{}'.format(config.bssid))
        print('SSID:{}'.format(config.ssid))

        while True:
            evt=wpa.recv(1024)
            if not evt:
                print 'Breaking no events'
                break
            print evt
            args = evt.split()

            event_name = args[0][3:]
            {
                'AP-STA-CONNECTED': self.client_connect,
                'AP-STA-DISCONNECTED': self.client_disconnect
            }[event_name](*args[1:])



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
        obj='quit'+'\n'
        self.send_msg(obj)
        print '**************************'
        self.close()
        #exit(0)

client=Client()

def sigint_handler(signum, frame):
    global client
    client.terminate()
    print 'catched interrupt signal!'

signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGHUP, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)

asyncore.loop(timeout=1)


