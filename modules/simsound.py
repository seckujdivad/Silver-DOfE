import multiprocessing as mp
import winsound
import time
import math
import threading
import os
import sys
import json

class Sound:
    def __init__(self):
        self.path = None
        
        self.interface = Interface()
        self.interface.play(1000, 1)
        
        self.sounds = {}
    
    def load_library(self, path):
        self.path = path
        
        if os.path.isdir(path):
            for filename in os.listdir(path):
                if filename.startswith('snd_') and filename.endswith('.json'):
                    with open(os.path.join(path, filename), 'r') as file:
                        data = json.load(file)
                    self.sounds[data['name']] = data
    
    def load_map(self, map_name):
        self.load_library(os.path.join(sys.path[0], 'server', 'maps', map_name, 'sounds'))
    
    def play(self, name):
        sound = self.sounds[name]
        
        for timing, freq in sound['form']:
            if timing[0] == 0:
                self.interface.play(freq, timing[1])
            else:
                self.interface.schedule(time.time() + timing[0], freq, timing[1])

class Interface:
    def __init__(self):
        self.pipe, pipe = mp.Pipe()
        
        self.controller_process = threading.Thread(target = Controller, args = [pipe], name = 'Sound controller').start()
    
    def play(self, freq, dura):
        self.pipe.send(['play', [freq, dura]])
    
    def schedule(self, timestamp, freq, dura):
        self.pipe.send(['schedule', [freq, dura], timestamp])
    
    def stop(self):
        self.pipe.send(['stop'])

class Controller:
    def __init__(self, pipe, resolution = 0.001, subdivisions = 10):
        self.pipe = pipe
        self.resolution = math.ceil(resolution)
        self.subdivisions = math.ceil(subdivisions)
        
        self.cont = True
        self.sound_queue = {}
        
        threading.Thread(target = self.handler).start()
    
    def handler(self):
        while self.cont:
            data = self.pipe.recv()
            
            if data[0] == 'stop':
                self.cont = False
                
            elif data[0] == 'play':
                self.insert_at('next', data[1])
                    
            elif data[0] == 'schedule':
                stamp = self.get_stamp(data[2], bias = 1)
                data.pop(2)
                
                if stamp < time.time():
                    self.insert_at('next', data[1])
                else:
                    self.insert_at(stamp, data[1])
    
    def insert_at(self, pos, sound):
        if pos == 'next':
            pos = self.get_stamp(time.time(), bias = 1)
        
        division_size = 1 / self.resolution
        num_insertions = math.ceil(sound[1] / division_size)
        
        for i in range(num_insertions):
            self._insert_direct(math.ceil((pos + (i * division_size)) / division_size) * division_size, sound[0])
    
    def _insert_direct(self, key, sound):
        if not sound in self.sound_queue:
            self.sound_queue[key] = [sound]
        else:
            self.sound_queue[key].append(sound)
        print(key - time.time())
    
    def player(self):
        while self.cont:
            start_time = time.time()
            to_play = []
            if 'next' in self.sound_queue:
                to_play = self.sound_queue['next'].copy()
                self.sound_queue['next'] = []
            
            now_key = self.get_stamp(time.time())
            if now_key in self.sound_queue:
                for sound in self.sound_queue[now_key]:
                    to_play.append(sound)
                self.sound_queue.pop(now_key)
            
            division_size = self.subdivisions / self.resolution
            slot_allocations = self.subdivisions / len(to_play) #slots allocated per sound
            snd_queue = []
            if snd_queue is not []:
                print(snd_queue)
            
            total_allocated = 0
            for sound in to_play:
                for i in range(total_allocated - int(total_allocated) + slot_allocations):
                    snd_queue.append(sound)
                total_allocated += slot_allocations
            
            for sound in snd_queue:
                self._play(sound, division_size)
            
            time.sleep(max([0, (1 / self.resolution) - time.time() + start_time]))
    
    def get_stamp(self, timestamp, bias = 0):
        'Bias of 0 means low, 1 means high'
        timestamp = timestamp / self.resolution
        if bias == 0:
            timestamp = math.floor(timestamp)
        else:
            timestamp = math.ceil(timestamp)
        return timestamp * self.resolution
    
    def _play(self, freq, dura):
        threading.Thread(target = self._winsound_beep, args = [freq, dura * 1000]).start()
    
    def _winsound_beep(self, freq, dura):
        winsound.Beep(freq, dura)
        print('b', freq, dura)