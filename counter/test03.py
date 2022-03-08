import AsyncSocketComms
import socket

s1 = AsyncSocketComms.AsyncSocketServer(60002)
s2 = AsyncSocketComms.AsyncSocketServer(60003)

#test = [s1,s2]

while True:
    r1 = s1.run()
    if r1:
        print('1 ',r1)
    r2 = s2.run()
    if r2:
        print('1 ',r2)