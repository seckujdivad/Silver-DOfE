import tkinter as tk
import socket
import threading
import time

class Game:
    def __init__(self, canvas):
        self.canvas = canvas
        
        class server:
            mode = 'internal' #either 'internal' or 'external'
            allow_external = True
            name = 'localhost'
        self.server = server
        
        self.running = True        
        threading.Thread(target = self.main, daemon = True).start()
    
    def main(self):
        while self.running:
            time.sleep(1)
    
    def connect_to_server(self, hostname = None):
        'Connect to a server. If the hostname is None, a server will be created'
        if hostname == None:
            self.server.mode = 'internal'
            self.server.name = 'localhost'
            self.server.object = Server(4321)
        else:
            self.server.mode = 'external'
            self.server.name = hostname
        self.client = Client(self.server.name, 4321)
        self.client.send_raw('hello world!')
    
    def close(self):
        self.running = False

class Engine:
    pass

class Water:
    pass

class Player:
    pass
    
class Server:
    def __init__(self, port_):
        class serverdata:
            host = ''
            port = port_
        self.serverdata = serverdata
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.bind((self.serverdata.host, self.serverdata.port))
        self.connection.listen(5)
        threading.Thread(target = self.acceptance_thread, name = 'Acceptance thread', daemon = True).start()
        
    def acceptance_thread(self):
        while True:
            print('ready')
            conn, addr = self.connection.accept()
            print(addr)
            threading.Thread(target = self.connection_handler, args = [addr, conn], daemon = True).start()
    
    def connection_handler(self, address, connection):
        print(address)
        while True:
            data = connection.recv(2048)
            print(data.decode('UTF-8'))

class Client:
    def __init__(self, host_, port_):
        class serverdata:
            host = host_
            port = port_
        self.serverdata = serverdata
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('xd')
        self.connection.connect((self.serverdata.host, self.serverdata.port))
        print('2')
    
    def send_raw(self, text):
        self.connection.send(text.encode())