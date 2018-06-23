import socket
import json
import time
import threading
import datetime
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.bind(('127.0.0.1',6677))
s.listen(5)
print('Server is running ...')

def TCP(sock,addr):
    print('Accept new connection from %s:%s.' %addr)
    while True:
        data =sock.recv(1024)
        print data
        if not data or data.decode()=='quit':
            break
        print datetime.datetime.now()
        print data
    sock.close()
    print('Connection from %s:%s closed.'%addr)

while True:
    sock,addr =s.accept()
    TCP(sock,addr)
    break
s.close()
exit(0)
