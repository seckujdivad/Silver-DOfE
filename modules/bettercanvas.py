import tkinter as tk
import os
import sys

class CanvasController:
    def __init__(self, canvas, game):
        self.canvas = canvas
        self.game = game
        
        self.layers = []
        self.reserved_args = ['layer']
        
        with open(os.path.join(sys.path[0], 'user', 'layers.json'), 'r') as file:
            self.layer_config = json.load(file) #load user defined order for screen items to be rendered in
        
    def create_rectangle(self, *coords, **args):
        'Wrapper function to provide tk canvas-like syntax'
        return self._create('rectangle', coords, args)
    
    def create_image(self, *coords, **args):
        'Wrapper function to provide tk canvas-like syntax'
        return self._create('image', coords, args)
    
    def create_text(self, *coords, **args):
        return self._create('text', coords, args)
    
    def create_window(self, *coords, **args):
        return self._create('window', coords, args)
    
    def _create(self, obj_type, coords, args):
        if not 'layer' in args:
            args['layer'] = 0
        
        if type(args['layer']) == str: #layer is string, use lookup table
            if args['layer'] in self.layer_config:
                args['layer'] = self.layer_config[args['layer']]
            else:
                raise ValueError('Couldn\'t find layer name "{}" in config'.format(args['layer'])) #layer not in lookup table
            
        while not len(self.layers) >= args['layer'] + 1:
            self.layers.append([]) #make layer if it doesn't exist
        
        filtered_args = {} #remove arguments that are reserved for controller (layer etc) and pass the rest on to the canvas
        for key in args:
            if not key in self.reserved_args:
                filtered_args[key] = args[key]
        
        if obj_type == 'rectangle': #call relevant canvas function
            obj = self.canvas.create_rectangle(*coords, **filtered_args)
        elif obj_type == 'image':
            obj = self.canvas.create_image(*coords, **filtered_args)
        elif obj_type == 'text':
            obj = self.canvas.create_text(*coords, **filtered_args)
        elif obj_type == 'window':
            obj = self.canvas.create_window(*coords, **filtered_args)
        
        self.layers[args['layer']].append({'object': obj})
        
        ## objects are always created on the top of their layer
        
        if not len(self.layers) == args['layer'] + 1: ## logic to find next highest tag and move just below it
            next_layer = None
            for i in range(len(self.layers) - 1, args['layer'], -1):
                if not len(self.layers[i]) == 0:
                    next_layer = i
            if next_layer == None:
                if len(self.layers) == 1:
                    lower_to = None
                    for i in range(args['layer']):
                        if not len(self.layers[i]) == 0:
                            lower_to = self.layers[i][len(self.layers[args['layer']]) - 1]
                    if not lower_to == None:
                        self.canvas.tag_lower(obj, lower_to['object'])
                else:
                    self.canvas.tag_lower(obj, self.layers[args['layer']][len(self.layers[args['layer']]) - 2]['object'])
            else:
                self.canvas.tag_lower(obj, self.layers[next_layer][0]['object'])
        
        return obj
    
    def delete(self, obj):
        'Delete item from canvas'
        to_remove = []
        for a in range(len(self.layers)):
            for b in range(len(self.layers[a])):
                if self.layers[a][b]['object'] == obj:
                    to_remove.append([a, b])
        
        self.canvas.delete(obj)
        
        to_remove.reverse()
        for a, b in to_remove:
            self.layers[a].pop(b)
        
    def coords(self, obj, *coords):
        'Set the coordinates of something on the canvas'
        self.canvas.coords(obj, *coords)
    
    def itemconfigure(self, obj, **args):
        'Configure an item on the canvas'
        self.canvas.itemconfigure(obj, **args)

class Model:
    '''
    Model:
    Similar in function to canvas.create_image
    canvas_controller - CanvasController object to render to
    mdl_name - name of model in map files
    map_path - path to map files
    layer - string or int for canvas controller
    img_mode - 'pil' or 'tk', PIL requires pillow
    '''
    def __init__(self, canvas_controller, mdl_name, map_path, layer):
        self.mdl_name = mdl_name
        self.map_path = map_path
        self.canvas_controller = canvas_controller
        self.layer = layer
        
        ## make data structures
        class attributes:
            class pos: #current coordinates
                x = 0
                y = 0
                
            class offscreen: #coordinates where the model is guaranteed to be offscreen
                x = 0
                y = 0
                
            rotation = 0 #current rotation (0-359)
            rotation_steps = 0 #number of different rotations to make
            
            transparency = 0 #current transparency (0-255)
            transparency_steps = 0 #number of different transparencies to make
            
            class offset: #amount that each layer of a stacked model is offset by
                x = 0
                y = 0
            
            baseimages = [] #images before any effects have been applied to them
            imageobjs = [] #image objects with effects that can be used to create canvas objects
            canvasobjs = [] #references to canvas objects created from imageobjs
            
            uses_PIL = False
            is_animated = False
            
            render_quality = 0 #0-3 - render quality as defined in the user's config
        self.attributes = attributes
        
        class cfgs:
            model = {}
            user = {}
            map = {}
        self.cfgs = cfgs
        
        class pillow:
            image = None
            image_chops = None
        self.pillow = pillow
        
        ## load data into structures
        #load configs
        with open(os.path.join(self.map_path, 'models', self.mdl_name, 'list.json'), 'r') as file:
            self.cfgs.model = json.load(file)
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            self.cfgs.user = json.load(file)
        
        with open(os.path.join(self.map_path, 'list.json'), 'r') as file:
            self.cfgs.map = json.load(file)
        
        #translate data from cfgs into model data structures
        self.attributes.offscreen.x = self.cfgs.model['offscreen'][0]
        self.attributes.offscreen.y = self.cfgs.model['offscreen'][1]
        
        self.attributes.pos.x = self.attributes.offscreen.x
        self.attributes.pos.y = self.attributes.offscreen.y
        
        self.attributes.uses_PIL = self.cfgs.user['graphics']['PILRender']
        self.attributes.is_animated = self.cfgs.model['animated']
        self.attributes.render_quality = self.cfgs.user['graphics']['model quality']
        self.attributes.rotation_steps = self.cfgs.model['rotations'][self.attributes.render_quality]
        
        if 'transparencies' in self.cfgs.model:
            self.attributes.transparency_steps = self.cfgs.model['transparencies'][self.attributes.render_quality]
        else:
            self.attributes.transparency_steps = 1
        
        