import socket
addr = '2406:da18:243:7410:41f7:de76:b2ed:de41'
port = 5432
s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.settimeout(5)
try:
    s.connect((addr, port, 0, 0))
    print('CONNECTED')
except Exception as e:
    print('CONNECT ERROR:', e)
finally:
    s.close()
