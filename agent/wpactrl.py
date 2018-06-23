import os
from collections import OrderedDict
import select

try:
    from gevent import socket
except ImportError:
    import socket

wpa_ctrl_counter=0


class wpa_ctrl(object):
    s = local = dest = None

def wpa_ctrl_open(ctrl_path):
    '''
    Open a control interface to wpa_supplicant/hostapd.
    '''
    ctrl = wpa_ctrl()

    try:
        ctrl.s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM, 0)
    except socket.error:
        return None
    print ctrl_path
    ctrl.local = '/tmp/wpa_ctrl_%d-%d' % (os.getpid(), wpa_ctrl_open.counter)
    wpa_ctrl_open.counter += 1

    try:
        ctrl.s.bind(ctrl.local)
    except socket.error:
        ctrl.s.close()

        return None

    try:
        ctrl.s.connect(ctrl_path)
    except socket.error:
        wpa_ctrl_close(ctrl)
        return None

    return ctrl

wpa_ctrl_open.counter = 0

def wpa_ctrl_close(ctrl):
    '''
    Close a control interface to wpa_supplicant/hostapd.
    '''
    os.unlink(ctrl.local)
    ctrl.s.close()


"""
def wpa_ctrl_request(ctrl, cmd, msg_cb=None, reply_len=4096):
    '''
    Send a command to wpa_supplicant/hostapd.
    '''

    ctrl.s.send(cmd)

    while True:
        rlist, wlist, xlist = select.select([ctrl.s], [], [], 2)

        if rlist and (ctrl.s in rlist):
            data = ctrl.s.recv(reply_len)

            if data and data[0] == '<':
                if msg_cb:
                    msg_cb(data)

                continue
            else:
                return data
        else:
            return -2 # Timed out
"""

def wpa_ctrl_request(ctrl,cmd,msg_cb=None,reply_len=1024):
        try:
            ctrl.s.send(cmd)
        except socket.timeout as e:
            raise WPASocketError('Timeout sending "{}"'.format(cmd),e)
        except socket.error as e:
            raise WPASocketError('Error sending "{}"'.format(cmd),e)
        resp = ctrl.s.recv(1024)
        if resp.strip() == 'UNKNOWN COMMAND':
            raise WPADataError("Command '{}' is not supported".format(cmd), 'command error')
        return resp.strip()




def wpa_ctrl_attach_helper(ctrl, attach):
    ret = wpa_ctrl_request(ctrl, 'ATTACH' if attach else 'DETACH')

    if isinstance(ret, basestring):
        return ret == 'OK\n'
    else:
        return ret

def wpa_ctrl_attach(ctrl):
    '''
    Register as an event monitor for the control interface.
    '''
    return wpa_ctrl_attach_helper(ctrl, True)

def wpa_ctrl_detach(ctrl):
    '''
    Unregister event monitor from the control interface.
    '''
    return wpa_ctrl_attach_helper(ctrl, False)

def wpa_ctrl_recv(ctrl):
    '''
    Receive a pending control interface message.
    '''
    return ctrl.s.recv(1024)

def wpa_ctrl_pending(ctrl):
    '''
    Check whether there are pending event messages.
    '''

    rlist, wlist, xlist = select.select([ctrl.s], [], [], 0)

    return ctrl.s in rlist

def wpa_ctrl_get_fd(ctrl):
    '''
    Get file descriptor used by the control interface.
    '''

    return ctrl.s.fileno()



class WPACtrlError(Exception):
    def __init__(self,msg,error):
        self.msg = msg
        self.error = error
        super(WPACtrlError,self).__init__(msg)


class WPASocketError(WPACtrlError):
    def __str__(self):
        return 'WPA socket error:{} ({})'.format(self.msg,self.error)


class WPADataError(WPACtrlError):
    def __str__(self):
        return 'WPA data error: {} ({})'.format(self.msg,self.error)


class KeyValResp(object):

    def __init__(self, data):
        self._data = OrderedDict()
        self.load(data)

    def __getattr__(self, name):
        try:
            return self._data[name]
        except KeyError:
            pass
        try:
            return getattr(self._data, name)
        except AttributeError:
            raise AttributeError("'{}' key not found in data".format(name))

    def load(self, data):
        lines = data.strip().split('\n')
        for k, v in (self.parse_line(l) for l in lines):
            self._data[k] = v

    def __str__(self):
        s = []
        for k, v in self._data.items():
            s.append('{}={}'.format(k, v))
        return '\n'.join(s)

    @staticmethod
    def parse_line(line):
        try:
            k, v = line.split('=', 1)
        except ValueError as e:
            raise WPADataError("Cannot parse line '{}'".format(line), e)
        k = k.strip()
        if '[' in k:
            k = k.replace('[', '_').replace(']', '')
        return k, v.strip()

class error(Exception):pass


class WPACtrl(object):
    SOCK_DEFAULT_PATH = '/var/run/hostapd-phy0/wlan0'
    SOCK_TIMEOUT = 5
    BUFF_SIZE = 4096
    SOCKETS_COUNT = 0

    def __init__(self,path=None):
        self.sock_path = path or self.SOCK_DEFAULT_PATH
        self.ctrl_iface = wpa_ctrl_open(path)
        if not self.ctrl_iface:
            raise error('wpa_ctrl_pending failed')
        self.attached = 0

    def close(self):
        if self.attached==1:
            self.detach()
        wpa_ctrl_close(self.ctrl_iface)

    #def __del__(self):
    #    self.close()

    def request(self,cmd):
        '''
        Send a command to wpa_supplicant/hostapd. Returns the command response in s string
        '''
        data = wpa_ctrl_request(self.ctrl_iface,cmd)

        if data ==-2:
            raise error('wpa_ctrl_request time out')
        return data

    def attach(self):
        '''
        Register as an event monitor for control interface
        '''
        if self.attached == 1:
            return
        try:
            ret = wpa_ctrl_attach(self.ctrl_iface)
        except socket.error:
            raise error('wpa_ctrl_attach failed')
        if ret == True:
            self.attached =1
        elif  ret==-1:
            raise error('wpa_ctrl_attach time out')

    def detach(self):
        '''
        Uregister event  monitor from the control interface
        '''
        if self.attached == 0:
            return

        try:
            ret = wpa_ctrl_detach(self.ctrl_iface)
        except socket.error:
            raise error('wpa_ctrl_detach failed')
        if ret == True:
            self.attached = 0
        elif ret == -1:
            raise error('wpa_ctrl_attach time out')

    def pending(self):
        '''
        Check if any events/messages are pending. Returns True if messages are pending,otherwise False
        '''
        try:
            return wpa_ctrl_pending(self.ctrl_iface)
        except socket.error:
            raise error('wpa_ctrl_pending failed')

    def recv(self,reply_len):
        try:
            data = self.ctrl_iface.s.recv(reply_len)
        except socket.error as e:
            raise WPASocketError('Error reading response',e)
        return data


    def connect(self):
        if self.sock:
            return
        self.sock = socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
        try:
            self.sock.bind(self.local_path)
        except socket.error:
            self.sock.close()
            self.sock=None
            return
        try:
            self.sock.connect(self.sock_path)
        except socket.error:
            self.disconnect()
            return
        print 'Connect to ctrl_path '



    def test(self):
        try:
            resp = self.request('PING')
        except WPACtrlError:
            return False
        return resp == 'PONG'

    def status(self):
        resp = self.request('STATUS')
        return KeyValResp(resp)

    def get_config(self):
        resp = self.request('GET_CONFIG')
        return KeyValResp(resp)

    def get_config(self):
        resp = self.request('GET_CONFIG')
        return KeyValResp(resp)
    def set_ssid(self,ssid):
        return self.request('SET ssid {}'.format(ssid.strip())=='OK')

if __name__=='__main__':
    import sys
    wc = WPACtrl('/home/hankai/workspace/hostap')
    if not wc.test():
        sys.exit(0)
    #resp = wc.status()
    #print('State:{}'.format(resp.state))
    #print('Interface:{}'.format(resp.bss_0))
    #print('SSID:{}'.format(resp.ssid_0))
    #print('Chanel:{}'.format(resp.channel))
    #resp =wc.get_config()
    #print(resp)
    while True:
        print 'agent_cmd >>',
        try:
            info=raw_input()
        except Exception,e:
            print 'can\'t input'
            exit()
        try:
            resp=wc.request(info)
            print resp
        except Exception,e:
            print e
            #break
    exit()

