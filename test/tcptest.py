import socket

s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)

s.connect(('192.168.109.144',6677))

while True:
    print 'test_cmd >>',
    try:
        info=raw_input()
    except Exception,e:
        print 'can\'t input'
        exit()
    try:
        msg = info+'\n'
        s.send(msg)
    except socket.error,e:
        print e
        break
s.close()