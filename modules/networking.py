from tkinter import messagebox
import multiprocessing as mp
import sqlite3 as sql
import socket
import threading
import json
import os
import sys
import random
import time
import math

import modules.servercmds
import modules.logging
import modules.netclients

class Server:
    def __init__(self, port_, frame = None):
        class serverdata:
            host = '' #hostname of server
            port = port_ #port server is operating on
            connections = [] #open or closed connections with clients
            map = None #map name
            mapdata = None #map attributes
            conn_data = [] #individual spaces for connections to store data to be publicly accessible
            item_data = [] #store ongoing items
            item_ticket = 0 #allow clients to know which items are which from tick to tick
            tickrate = 10 #times to process items per second
            looptime = 1 / tickrate #time per loop
            gamemode = None #current gamemode int
            scoreline = [0, 0] #current game scoreline
            round_start_time = None #timestamp for start of round
            round_in_progress = False #whether or not a round is in progress
            running = True #whether or not server is running
            item_dicts = {} #store attributes of the map's possible items
        self.serverdata = serverdata
        
        self.clients = []
        
        self.frame = frame
        
        self.log = modules.logging.Log(os.path.join(sys.path[0], 'server', 'logs', 'svlog.txt'))
        
        self.database = ServerDatabase(os.path.join(sys.path[0], 'server', 'database.db'), modules.logging.Log(os.path.join(sys.path[0], 'server', 'logs', 'dblog.txt')))
        
        self.output_pipe, pipe = mp.Pipe()
        
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.bind((self.serverdata.host, self.serverdata.port))
        self.connection.listen(5)
        
        self.cmdline = modules.servercmds.ServerCommandLineUI(self.handle_command, pipe, self.frame)
        
        with open(os.path.join(sys.path[0], 'server', 'config.json'), 'r') as file:
            self.settingsdata = json.load(file)
        for script in self.settingsdata['scripts']['autoexec']:
            with open(os.path.join(sys.path[0], 'server', 'scripts', '{}.txt'.format(script)), 'r') as file:
                text = file.read()
            self.output_pipe.send(self.run_script(text))
        
        self.serverdata.tickrate = self.settingsdata['network']['tickrate']
        self.serverdata.looptime = 1 / self.serverdata.tickrate
        
        while self.serverdata.mapdata is None:
            time.sleep(0.01) #refuse to come online until a map is loaded
        
        self.serverdata.round_start_time = time.time()
        self.serverdata.round_in_progress = True

        threading.Thread(target = self.acceptance_thread, name = 'Acceptance thread', daemon = True).start()
        threading.Thread(target = self.handle_items, name = 'Item handler', daemon = True).start()
        threading.Thread(target = self.push_timeleftd, name = 'Round timer daemon', daemon = True).start()
        
    def acceptance_thread(self):
        while self.serverdata.running:
            self.output_pipe.send('Ready for incoming connections')
            
            conn, addr = self.connection.accept()
            self.serverdata.connections.append([addr, conn])
            
            netcl = modules.netclients.NetClient(addr, conn)
            client = modules.netclients.ServerClient(self, netcl)
            
            client.metadata.health = 100
            client.metadata.username = 'guest'
            client.metadata.team_id = self.get_team_id(self.get_team_distributions())
            
            netcl.start()
            
            self.clients.append(client)
            
            for script in self.settingsdata['scripts']['userconnect']:
                with open(os.path.join(sys.path[0], 'server', 'scripts', '{}.txt'.format(script)), 'r') as file:
                    text = file.read()
                self.output_pipe.send(self.run_script(text))
    
    def handle_command(self, command, source = 'internal'):
        if command == '' or command.startswith(' '):
            command = 'help'
        splitcommand = command.split(' ')
        name = splitcommand[0]
        argstring = ''
        for arg in splitcommand[1:]:
            argstring += '{} '.format(arg)
        argstring = argstring[:len(argstring) - 1]
        
        self.log.add('command input', command)
        
        output = 'ERROR'
        if name == 'help':
            output = '''Commands:
map: load a map by name
exec: execute a script by name stored in the server/scripts directory
echo: output the text given to the console
clear: clear the console
close_window: close the console

say: send a message to all players
say_pop: send a fullscreen message to all players

mp_gamemode: set the gamemode
mp_respawn_all: respawn all players
mp_scoreline_team1: set the scoreline of team 1
mp_scoreline_team2: set the scoreline of team 2

sv_:
sv_conns: list of connections to the server
sv_kick_addr: kick a player by address
sv_quit: destroy the server
sv_hitbox: choose whether or not to use accurate hitboxes'''
        elif name == 'map':
            if source == 'internal':
                try:
                    self.load_map(argstring)
                    output = 'Loading map \'{}\'...'.format(argstring)
                except ValueError:
                    type, value, traceback = sys.exc_info()
                    output = 'Error while loading map \'{}\'\nERROR: {}\n{}'.format(argstring, type, value)
            else:
                output = 'No permissions'
        elif name.startswith('say'):
            if name == 'say':
                self.send_all(Request(command = 'say', arguments = {'text': argstring}))
                output = 'Said \'{}\' to all users'.format(argstring)
            elif name == 'say_pop':
                self.send_all(Request(command = 'popmsg', subcommand = 'general', arguments = {'text': argstring}))
                output = 'Said \'{}\' to all users with a fullscreen message'.format(argstring)
        elif name.startswith('sv_'):
            if name == 'sv_kick_addr':
                if source == 'internal':
                    try:
                        self.kick_address(argstring)
                        output = 'Kicked all connections through \'{}\''.format(argstring)
                    except ValueError:
                        output = 'Error while kicking \'{}\''.format(argstring)
                else:
                    output = 'No permissions'
            elif name == 'sv_quit':
                if source == 'internal':
                    self.quit()
                    output = 'Server is now offline'
                else:
                    output = 'No permissions'
            elif name == 'sv_hitbox':
                if source == 'internal':
                    try:
                        self.set_hitboxes(argstring)
                    except ValueError:
                        output = 'Error while setting hitboxes to \'{}\''.format(argstring)
                else:
                    output = 'No permissions'
            else:
                output = 'Command not found, try \'help\''
        elif name.startswith('mp_'):
            if name == 'mp_gamemode':
                if source == 'internal':
                    if argstring == '':
                        output = '''Options:
0: xvx arena
1: deathmatch
2: team deathmatch
3: pve survival'''
                    else:
                        output = ['Gamemode not supported by this map', 'Gamemode changed successfully', 'This is already the gamemode - no action taken'][self.set_gamemode(int(argstring))]
                else:
                    output = 'No permissions'
            elif name == 'mp_respawn_all':
                if source == 'internal':
                    self.respawn_all()
                    output = 'Done!'
                else:
                    output = 'No permissions'
            elif name.startswith('mp_scoreline_'):
                if name == 'mp_scoreline_team1':
                    if argstring == '':
                        output = 'Score for team 1: {}'.format(self.serverdata.scoreline[0])
                    elif source == 'internal':
                        self.set_scoreline(score0 = int(argstring))
                    else:
                        output = 'No permissions'
                elif name == 'mp_scoreline_team2':
                    if argstring == '':
                        output = 'Score for team 2: {}'.format(self.serverdata.scoreline[1])
                    elif source == 'internal':
                        self.set_scoreline(score1 = int(argstring))
                    else:
                        output = 'No permissions'
        elif name == 'exec':
            with open(os.path.join(sys.path[0], 'server', 'scripts', '{}.txt'.format(argstring)), 'r') as file:
                text = file.read()
            output = self.run_script(text)
        elif name == 'echo':
            output = argstring
        elif name == 'clear':
            output = '$$clear$$'
        elif name == 'close_window':
            output = '$$close_window$$'
        else:
            output = 'Command not found, try \'help\''
            
        self.log.add('command output', output)
        
        return output
    
    def run_script(self, text):
        output = ''
        for line in text.split('\n'):
            if not line == '':
                cmdout = self.handle_command(line)
                if not cmdout == '':
                    output += '{}\n'.format(cmdout)
        return output
    
    def load_map(self, mapname):
        self.serverdata.map = mapname
        
        with open(os.path.join(sys.path[0], 'server', 'maps', self.serverdata.map, 'list.json'), 'r') as file:
            self.serverdata.mapdata = json.load(file)
        
        for data in self.serverdata.conn_data:
            data['model'] = random.choice(self.serverdata.mapdata['entity models']['player'])
        
        self.set_gamemode(self.serverdata.mapdata['gamemode']['default'])
        
        req = Request(command = 'var update w', subcommand = 'map', arguments = {'map name': self.serverdata.map})
        self.send_all(req)
        
        for conn_data in self.serverdata.conn_data:
            if conn_data['active']:
                req = Request(command = 'give', arguments = {'items': self.serverdata.mapdata['player']['starting items'][conn_data['team']]})
                self.send(conn_data['connection'], req)
                req = Request(command = 'var update w', subcommand = 'team', arguments = {'value': conn_data['team']})
                self.send(conn_data['connection'], req)
        
        self.serverdata.item_dicts = {}
        for name in os.listdir(os.path.join(sys.path[0], 'server', 'maps', self.serverdata.map, 'items')):
            with open(os.path.join(sys.path[0], 'server', 'maps', self.serverdata.map, 'items', name), 'r') as file:
                self.serverdata.item_dicts[name] = json.load(file)
                
    def kick_address(self, target_address):
        i = 0
        to_delete = []
        for address, connection in self.serverdata.connections:
            if address[0] == target_address:
                connection.close()
                to_delete.append(i)
            i += 1
        for i in to_delete:
            self.serverdata.connections.pop(i)
    
    def send(self, connection, data):
        self.log.add('sent', 'Data sent to {} - {}'.format(connection.getpeername(), data.pretty_print()))
        connection.send(data.as_json().encode())
        
    def send_all(self, data):
        for client in self.clients:
            client.send(data)
    
    def quit(self):
        self.serverdata.running = False
        self.connection.close()
    
    def get_team_id(self, team_quantities):
        return team_quantities.index(min(team_quantities))
    
    def get_team_distributions(self):
        team_quantities = [0, 0]
        for conn_data in self.serverdata.conn_data:
            if conn_data['active'] and conn_data['team'] != None:
                team_quantities[conn_data['team']] += 1
        return team_quantities
    
    def handle_items(self):
        while self.serverdata.running:
            start = time.time()
            
            to_remove = []
            data_to_send = []
            
            i = 0
            for item in self.serverdata.item_data:
                to_send_loop = {}
                
                out_of_bounds = False
                if item['data']['hitbox']['type'] == 'circular':
                    if item['position'][0] > self.serverdata.mapdata['geometry'][0] + item['data']['hitbox']['radius']:
                        out_of_bounds = True
                    elif item['position'][0] < 0 - item['data']['hitbox']['radius']:
                        out_of_bounds = True
                    if item['position'][1] > self.serverdata.mapdata['geometry'][1] + item['data']['hitbox'][
                        'radius']:
                        out_of_bounds = True
                    elif item['position'][1] < 0 - item['data']['hitbox']['radius']:
                        out_of_bounds = True
            
                if ((not item['data']['range'] == None) and item['distance travelled'] >= item['data']['range']) or out_of_bounds:
                    to_send_loop['type'] = 'remove'
                    to_send_loop['ticket'] = item['ticket']
                    to_remove.append(i)
                   
                elif item['new']:
                    to_send_loop['type'] = 'add'
                    
                    to_send_loop['position'] = item['position']
                    to_send_loop['rotation'] = item['rotation']
                    to_send_loop['new'] = True
                    item['new'] = False
                    to_send_loop['data'] = item['data']
                
                elif not item['data']['speed'] == 0:
                    to_send_loop['type'] = 'update position'
                    
                    to_move = item['data']['speed'] / self.serverdata.tickrate
                    item['distance travelled'] += to_move

                    item['position'][0] +=  to_move * math.cos(math.radians(item['rotation']))
                    item['position'][1] +=  to_move * math.sin(math.radians(item['rotation']))
                    
                    to_send_loop['position'] = item['position']
                    
                #clipping
                for playerdata in self.serverdata.conn_data:
                    damage_dealt = False
                    if playerdata['active'] and playerdata['mode'] == 'player':
                        if self.item_touches_player(playerdata['position']['x'], playerdata['position']['y'], item):
                            if 'last damage' in item and not item['last damage'] == None:
                                if (time.time() - item['last damage']) > item['data']['damage cooldown']:
                                    damage_dealt = True
                            else:
                                damage_dealt = True
                    
                    if damage_dealt and not item['creator']['id'] == playerdata['id']:
                        self.increment_health(playerdata, 0 - item['data']['damage']['player'], item['data']['display name'], self.serverdata.conn_data[item['creator']['id']]['username'])
                        item['last damage'] = time.time()
                        
                        self.send(playerdata['connection'], Request(command = 'var update w', subcommand = 'health', arguments = {'value': playerdata['health']}))
                        
                        if item['data']['destroyed after damage']:
                            to_send_loop['type'] = 'remove'
                            to_send_loop['ticket'] = item['ticket']
                            to_remove.append(i)
                
                if not to_send_loop == {}:
                    to_send_loop['ticket'] = item['ticket']
                    data_to_send.append(to_send_loop)
                    
                i += 1
			
            to_remove.sort()
            to_remove.reverse()
            for i in to_remove:
                self.serverdata.item_data.pop(i)
            
            for conn_data in self.serverdata.conn_data:
                self.send(conn_data['connection'], Request(command = 'update items', subcommand = 'server tick', arguments = {'pushed': data_to_send}))
                self.send(conn_data['connection'], Request(command = 'var update w', subcommand = 'player positions', arguments = {'positions': self.get_all_positions([conn_data['id']])}))
            
            time.sleep(max(0, self.serverdata.looptime - (time.time() - start))) #prevent server from running too quickly
    
    def item_touches_player(self, x, y, item):
        if item['data']['hitbox']['type'] == 'circular':
            if self.distance_to_point(x, y, *item['position']) <= item['data']['hitbox']['radius']:
                return True
        return False
    
    def distance_to_point(self, x0, y0, x1, y1):
        return math.hypot(x1 - x0, y1 - y0)
    
    def update_health(self, client_data, health, weapon = None, killer = None):
        old_health = client_data['health']
        client_data['health'] = health
        
        if not old_health == client_data['health']: #health has changed
            if (old_health == 0 and client_data['health'] < 0): #death has already occured
                client_data['health'] = 0
            elif client_data['health'] <= 0 and old_health > 0: #this is the 'first death' (first time health reached 0)
                self.on_death(client_data['id'], weapon = weapon, killer = killer)
    
    def increment_health(self, client_data, health, weapon = None, killer = None):
        self.update_health(client_data, client_data['health'] + health, weapon, killer)
    
    def set_mode(self, client_data, client_mode):
        self.send(client_data['connection'], Request(command = 'set mode', subcommand = client_mode))
        
        client_data['mode'] = client_mode
        
        if client_mode == 'spectator':
            self.send_text(['chat', 'new mode', 'spectator'], [client_data['username']])
            self.output_pipe.send('{} is now spectating'.format(client_data['username']))
        elif client_mode == 'player':
            self.send_text(['chat', 'new mode', 'player'], [client_data['username']])
            self.output_pipe.send('{} is now playing'.format(client_data['username']))
            
            for client in self.serverdata.conn_data:
                if client['active']:
                    self.send(client['connection'], Request(command = 'var update w', subcommand = 'player positions', arguments = {'positions': self.get_all_positions([client['id']])}))
    
    def send_text(self, path, formats = None, connection = None, category = 'general'):
        string = self.settingsdata['messages']
        for item in path:
            string = string[item]
        
        if type(string) == list:
            string = random.choice(list)
        
        if not type(string) == str:
            raise ValueError('Invalid string path {} - doesn\'t give a string'.format(path))
        
        if not formats == None:
            string = string.format(*formats)
        
        if path[0] == 'fullscreen':
            req = Request(command = 'popmsg', subcommand = 'welcome', arguments = {'text': string})
        elif path[0] == 'chat':
            req = Request(command = 'say', subcommand = category, arguments = {'text': string, 'category': category})
        else:
            raise ValueError('Invalid text mode "{}"'.format(path[0]))
        
        if connection is None:
            self.send_all(req)
        else:
            self.send(connection, req)
    
    def set_gamemode(self, gamemode, force = False):
        if gamemode in self.serverdata.mapdata['gamemode']['supported']:
            if self.serverdata.gamemode == gamemode and not force:
                return 2
            self.serverdata.gamemode = gamemode
            self.respawn_all()
            self.set_scoreline(0, 0)
            self.send_text(['fullscreen', 'gamemode change'], formats = [['PvP arena',
                                                                          'deathmatch',
                                                                          'team deathmatch',
                                                                          'PvE survival'][self.serverdata.gamemode]],
                           category = 'gamemode change')
        else:
            return 0
        return 1

    def respawn_all(self):
        for client in self.serverdata.conn_data:
            if client['active']:
                self.respawn(client['id'])
                
        self.serverdata.round_in_progress = True
        self.serverdata.round_start_time = time.time()
    
    def respawn(self, conn_id):
        client = self.serverdata.conn_data[conn_id]
        
        spawnpoint = self.generate_spawn(conn_id)
        self.set_mode(client, 'player')
        self.send(client['connection'], Request(command = 'var update w',
                                                subcommand = 'client position',
                                                arguments = {'x': spawnpoint[0],
                                                             'y': spawnpoint[1],
                                                             'rotation': 0}))
        self.update_health(client, 100)
        self.send(client['connection'], Request(command = 'clear inventory'))
        self.send(client['connection'], Request(command = 'give',
                                                arguments = {'items': self.serverdata.mapdata['player']['starting items'][client['team']]}))
    
    def respawn_after(self, conn_id, delay):
        threading.Thread(target = self._respawn_after, args = [conn_id, delay], name = 'Scheduled respawn', daemon = True).start()
    
    def _respawn_after(self, conn_id, delay):
        self.respawn(conn_id)
    
    def generate_spawn(self, conn_id):
        if self.serverdata.gamemode == 0:
            return random.choice(self.serverdata.mapdata['player']['spawnpoints'][0][self.serverdata.conn_data[conn_id]['team']])
        elif self.serverdata.gamemode == 1:
            cmin, cmax = self.serverdata.mapdata['player']['spawnpoints'][1]
            return [random.randrange(cmin[0], cmax[0]), random.randrange(cmin[1], cmax[1])]
        elif self.serverdata.gamemode == 2:
            cmin, cmax = self.serverdata.mapdata['player']['spawnpoints'][2][self.serverdata.conn_data[conn_id]['team']]
            return [random.randrange(cmin[0], cmax[0]), random.randrange(cmin[1], cmax[1])]
    
    def set_scoreline(self, score0 = None, score1 = None):
        if score0 is None:
            score0 = self.serverdata.scoreline[0]
        if score1 is None:
            score1 = self.serverdata.scoreline[1]
        
        self.serverdata.scoreline = [score0, score1]
        self.send_all(Request(command = 'var update w', subcommand = 'scoreline', arguments = {'scores': self.serverdata.scoreline}))
        self.output_pipe.send('Scoreline is now {} - {}'.format(score0, score1))
    
    def increment_scoreline(self, score0 = None, score1 = None):
        if score0 is not None:
            score0 += self.serverdata.scoreline[0]
        if score1 is not None:
            score1 += self.serverdata.scoreline[1]
        self.set_scoreline(score0, score1)
    
    def on_death(self, conn_id, weapon = 'world', killer = 'world'):
        client = self.serverdata.conn_data[conn_id]
        
        client['health'] = 0
        
        s = random.choice(self.settingsdata['messages']['killfeed'])
        self.send_all(Request(command = 'event', subcommand = 'death', arguments = {'text': s.format(weapon = weapon.lower(), killer = killer, victim = client['username']),
                                                                                    'weapon': weapon.lower()}))
        self.output_pipe.send('Player {} died'.format(client['username']))
        
        self.set_mode(client, 'spectator')
        
        if self.serverdata.gamemode == 0:
            alive = self.num_alive()
            
            if alive[0] == 0:
                self.round_ended(winner = 1)
            elif alive[1] == 0:
                self.round_ended(winner = 0)
                
        elif self.serverdata.gamemode == 1:
            self.respawn_after(conn_id, self.settingsdata['player']['gamemodes']['deathmatch']['respawn time'])
            
        elif self.serverdata.gamemode == 2:
            if client['team'] == 0:
                self.increment_scoreline(score0 = 1)
            elif client['team'] == 1:
                self.increment_scoreline(score1 = 1)
                
            self.respawn_after(conn_id, self.settingsdata['player']['gamemodes']['team deathmatch']['respawn time'])
            
        elif self.serverdata.gamemode == 3:
            self.respawn_after(conn_id, self.settingsdata['player']['gamemodes']['pve surival']['respawn time'])
        
    def round_ended(self, winner = None):
        self.serverdata.round_in_progress = False
        if self.serverdata.gamemode == 0:
            self.xvx_round_ended(winner = winner)
        
        elif self.serverdata.gamemode == 1:
            time.sleep(self.settingsdata['player']['gamemodes']['deathmatch']['after game time'])
            self.respawn_all()
        
        elif self.serverdata.gamemode == 2:
            time.sleep(self.settingsdata['player']['gamemodes']['team deathmatch']['after game time'])
            self.respawn_all()
        
        elif self.serverdata.gamemode == 3:
            time.sleep(self.settingsdata['player']['gamemodes']['pve survival']['after game time'])
            self.respawn_all()
        
    def num_alive(self):
        count = [0, 0]
        for client in self.serverdata.conn_data:
            if client['active'] and client['mode'] == 'player' and client['health'] > 0:
                count[client['team']] += 1
        return count
    
    def xvx_round_ended(self, winner):
        threading.Thread(target = self._xvx_round_ended, args = [winner]).start()
    
    def _xvx_round_ended(self, winner):
        self.serverdata.round_in_progress = False
        
        if winner == 0 and self.serverdata.scoreline[0] + 1 == self.settingsdata['player']['gamemodes']['xvx']['min rounds']:
            self.xvx_game_won(0)
            
        elif winner == 1 and self.serverdata.scoreline[1] + 1 == self.settingsdata['player']['gamemodes']['xvx']['min rounds']:
            self.xvx_game_won(1)
            
        else:
            if winner == 0:
                self.increment_scoreline(score0 = 1)
                self.output_pipe.send('Team 1 won the round')
                self.send_text(['fullscreen', 'xvx', 'round won'], ["1"], category = 'round end')
                
            elif winner == 1:
                self.increment_scoreline(score1 = 1)
                self.output_pipe.send('Team 2 won the round')
                self.send_text(['fullscreen', 'xvx', 'round won'], ["2"], category = 'round end')
            
            elif winner is None:
                self.output_pipe.send('Both teams ran out of time')
                self.send_text(['fullscreen', 'xvx', 'round draw'], category = 'round end')
        
            time.sleep(self.settingsdata['player']['gamemodes']['xvx']['after round time'])
            self.respawn_all()
        
    def get_all_positions(self, omit):
        output = []
        for data in self.serverdata.conn_data:
            if data['active'] and data['mode'] == 'player' and data['id'] not in omit:
                d = data['position'].copy()
                d['id'] = data['id']
                output.append(d)
        return output
    
    def xvx_game_won(self, winner):
        self.send_text(['fullscreen', 'xvx', 'game won'], formats = [winner + 1], category = 'game end')
        
        self.output_pipe.send('Team {} won the game'.format(winner + 1))
        
        threading.Thread(target = self._xvx_game_won, daemon = True).start()
    
    def _xvx_game_won(self):
        time.sleep(self.settingsdata['player']['gamemodes']['xvx']['after game time'])
        self.set_gamemode(0, force = True)
    
    def gamemode_text(self):
        return ['xvx', 'deathmatch', 'team deathmatch', 'pve survival'][self.serverdata.gamemode]
    
    def get_timeleft(self):
        if self.serverdata.round_in_progress:
            gamemode_data = self.settingsdata['player']['gamemodes'][self.gamemode_text()]
            if 'round time' in gamemode_data:
                return gamemode_data['round time'] + self.serverdata.round_start_time - time.time()
            else:
                return None
        else:
            return None
    
    def push_timeleftd(self):
        while self.serverdata.running:
            if self.serverdata.round_in_progress:
                tleft = self.get_timeleft()
                
                self.send_all(Request(command = 'var update w', subcommand = 'round time', arguments = {'value': tleft}))
                
                if tleft is None:
                    time.sleep(0.1)
                elif tleft <= 0:
                    self.send_all(Request(command = 'var update w', subcommand = 'round time', arguments = {'value': None}))
                    self.round_ended()
                else:
                    delay = tleft - math.floor(tleft)
                    if delay <= 0:
                        time.sleep(0.5)
                    else:
                        time.sleep(delay)
            else:
                time.sleep(0.1)

class Request:
    def __init__(self, data = {}, **args):
        #priorities data from the data variable over the flags
        if not data == {}:
            if type(data) == str:
                self.json_in(data)
            elif type(data) == dict:
                self.dict_in(data)
            else:
                raise TypeError('Data must be dict or str, not {} (value = {})'.format(type(data).__name__, data))
                
        elif not args == {}:
            self.dict_in(args)
            
        else:
            self.dict_in(data)
    
    def as_json(self):
        return json.dumps(self.as_dict())
    
    def as_dict(self):
        return {'command': self.command,
                'subcommand': self.subcommand,
                'arguments': self.arguments}
        
    def json_in(self, data):
        self.dict_in(json.loads(data))
   
    def dict_in(self, data):
        self._clear_all_values()
        
        if 'command' in data:
            self.command = data['command']
        else:
            self.command = ''
        if 'subcommand' in data:
            self.subcommand = data['subcommand']
        else:
            self.subcommand = None
        if 'arguments' in data:
            self.arguments = data['arguments']
        else:
            self.arguments = []
        
    def _clear_all_values(self):
        self.request_id = None
        self.response_id = None
    
    def pretty_print(self):
        return '<{}> - {} {}'.format(self.command, self.subcommand, self.arguments)

class ServerDatabase:
    def __init__(self, path, log = None):
        self.path = path
        self.log = log
        
        pipe, self.pipe = mp.Pipe()
        
        threading.Thread(target = self.databasecontrollerd, name = 'Server database controller daemon', args = [pipe]).start()
    
    def databasecontrollerd(self, input_pipe):
        database_is_new = False
        if not os.path.isfile(self.path):
            database_is_new = True
            
        self.connection = sql.connect(self.path)
        
        if database_is_new:
            self._make()
        
        self._log_wrapper('Connected to SQLite database at {}'.format(self.path))
        
        cont = True
        while cont:
            data = input_pipe.recv()
            
            if len(data) == 2:
                task, arguments = data
                
                self._log_wrapper('Received command #{} with arguments {}'.format(task, arguments))
                
                if task == self.lookup.make:
                    self._make()
                elif task == self.lookup.disconnect:
                    cont = False
                elif task == self.lookup.user_connected:
                    self._user_connected(arguments[0])
                elif task == self.lookup.match_concluded:
                    self._match_concluded(arguments[0], arguments[1])
                elif task == self.lookup.get_user_data:
                    self.output.dictionary[arguments[1]] = self._get_user_data(arguments[0])
                else:
                    self._log_wrapper('Uncaught command #{}'.format(task))
            else:
                self._log_wrapper('Command must be of length 2, not {}'.format(len(data)))
            self.connection.commit()
        self.connection.close()
                
    def _make(self):
        'Make the \'users\' table in the database. Overwrites if it already exists'
        self.connection.execute("""CREATE TABLE `users` (
	`username`	TEXT,
	`lastconn`	REAL,
	`elo`	REAL,
	`wins`	INTEGER,
	`losses`	INTEGER,
	`metadata`	TEXT
)""")
        self._log_wrapper('Made user table')
    
    def _add_user(self, username):
        'Add a user to the database if the username doesn\'t already exist'
        if self._get_user_data(username) == None:
            self.connection.execute("INSERT INTO `users` VALUES ((?), (?), 1500.0, 0, 0, '{}')", (username, time.time()))
            self._log_wrapper('Added user {}'.format(username))
        else:
            self._log_wrapper('Couldn\'t add user {}'.format(username))
            raise ValueError('Username "{}" is already in use'.format(username))
    
    def _user_connected(self, username):
        'Add a user if they don\'t already exist. Update their last connection time if they do'
        if self._get_user_data(username) == None:
            self._add_user(username)
        self.connection.execute("UPDATE users SET lastconn = (?) WHERE username = (?)", (time.time(), username))
        self._log_wrapper('User {} connected'.format(username))
    
    def _match_concluded(self, winner_name, loser_name):
        'Update win/loss records for two users'
        if (not self._get_user_data(winner_name) == None) and (not self._get_user_data(winner_name) == None):
            self.connection.execute('UPDATE users SET wins = wins + 1 WHERE username = (?)', (winner_name,))
            self.connection.execute('UPDATE users SET losses = losses + 1 WHERE username = (?)', (loser_name,))
            self._log_wrapper('{} beat {}, stored in database'.format(winner_name, loser_name))
        else:
            self._log_wrapper('Couldn\'t find either {} or {}'.format(winner_name, loser_name))
            raise ValueError('Either {} or {} do not exist'.format(winner_name, loser_name))
    
    def _get_user_data(self, username):
        'Return all information on a user'
        'Finds the data for a user if they exist. If not, returns None'
        data = self.connection.execute("SELECT * FROM users WHERE username = (?)", (username,)).fetchall()
        
        if len(data) == 0:
            self._log_wrapper('Couldn\'t find data for {}'.format(username))
            return None
        else:
            self._log_wrapper('Found data for {}, {} entry/entries'.format(username, len(data)))
            return data[0]
    
    def _log_wrapper(self, text):
        'A wrapper for the database log (if it has been specified)'
        if not self.log == None:
            self.log.add('database', text)
    
    class lookup:
        make = 0
        disconnect = 1
        user_connected = 2
        match_concluded = 3
        get_user_data = 4
    
    class output:
        ticket = 0
        dictionary = {}
    
    def make(self):
        'Make the \'users\' table in the database. Overwrites if it already exists'
        self.pipe.send([self.lookup.make, []])
    
    def disconnect(self):
        'Disconnect from the database'
        self.pipe.send([self.lookup.disconnect, []])
    
    def user_connected(self, username):
        'Updates the last connection time on a user'
        self.pipe.send([self.lookup.user_connected, [username]])
        print('{} connected'.format(username))
    
    def match_concluded(self, winner_name, loser_name):
        self.pipe.send([self.lookup.match_concluded, [winner_name, loser_name]])
    
    def get_user_data(self, username):
        ticket = str(self.output.ticket)
        self.output.ticket += 1
        
        self.pipe.send([self.lookup.get_user_data, [username, ticket]])
        
        while not ticket in self.output.dictionary:
            time.sleep(0.05)
        return self.output.dictionary.pop(ticket)