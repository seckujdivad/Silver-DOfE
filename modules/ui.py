from tkinter import messagebox
import tkinter as tk
import threading
import time
import json
import os
import sys
import functools
import shutil

class UI:
    def __init__(self):
        self.ready = {'tkthread': False}
        self.triggers = {}
        
        threading.Thread(target = self.tkthread).start() #start tkinter window in separate thread
        clearpass = False
        while not clearpass: #wait for all threads to check in before returning
            clearpass = True
            for name in self.ready:
                if not self.ready[name]:
                    clearpass = False
    
    def tkthread(self):
        self.root = tk.Tk() #create tkinter window
        
        class styling: #consistent styling tools
            @classmethod
            def get(self, font_size = 'medium', object_type = tk.Label, relief = 'default', fonts = 'default'):
                'Get styling for a specific type of widget'
                output = {}
                if object_type == tk.Button:
                    output['overrelief'] = self.reliefs[relief]['overrelief']
                output['relief'] = self.reliefs[relief]['relief']
                if not object_type in [tk.Canvas, tk.Scrollbar]:
                    output['font'] = self.fonts[fonts][font_size]
                return output
            
            @classmethod
            def set_weight(self, frame, width, height, weight_ = 1, dorows = True, docolumns = True):
                'Set uniform weighting across a frame'
                for cheight in range(height):
                    if dorows:
                        frame.rowconfigure(cheight, weight = weight_)
                    for cwidth in range(width):
                        if docolumns:
                            frame.columnconfigure(cwidth, weight = weight_)
            fonts = {}
            reliefs = {}
            with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
                settingsdata = json.load(file)
            for style_type in settingsdata['styling']:
                fonts[style_type] = settingsdata['styling'][style_type]['fonts']
                reliefs[style_type] = settingsdata['styling'][style_type]['reliefs']
        self.styling = styling        
        
        class main: #store data to do with ui
            title = ''
            geometry = None
            current = None
            page_frame = tk.Frame(self.root)
            page_frame.pack(fill = tk.BOTH, expand = True)
        
        class uiobjects:
            class menu: #menu ui
                config = {'name': 'Menu'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
                        settingsdict = json.load(file)
                        
                    pilrender_msg = settingsdict['graphics']['PILrender']
                    if not pilrender_msg:
                        pilrender_msg = 'False (WARNING! - disables sprite rotation)'
                        
                    text_ = 'Name: {}, PIL rendering: {} \nGo to settings to make sure all packages have been installed'.format(settingsdict['user']['name'], pilrender_msg)
                    self.label_userdata.config(text = text_)
                    
                    self.button_editor.config(command = self.load_editor)
                    self.button_connect.config(command = self.load_connect_server)
                    self.button_host.config(command = self.load_host_server)
                    self.button_settings.config(command = self.load_settings)
                    self.button_server_settings.config(command = self.load_server_settings)
                    self.button_quit.config(command = self.close_window)
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                @classmethod
                def load_settings(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.settings)
                
                @classmethod
                def load_host_server(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.game)
                
                @classmethod
                def load_connect_server(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.connect_server)
                
                @classmethod
                def load_editor(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.editor_choose_file)
                
                @classmethod
                def load_server_settings(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.server_settings)
                
                @classmethod
                def close_window(self):
                    self.config['methods'].uiobject.call_trigger('quit')
                    
                frame = tk.Frame(main.page_frame)
                label_title = tk.Label(frame, text = 'Hydrophobes', **self.styling.get(font_size = 'large', object_type = tk.Label))
                button_editor = tk.Button(frame, text = 'Map editor', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_connect = tk.Button(frame, text = 'Connect to a server', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_host = tk.Button(frame, text = 'Host a server', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_settings = tk.Button(frame, text = 'Change client settings', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_server_settings = tk.Button(frame, text = 'Change server settings', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_quit = tk.Button(frame, text = 'Quit', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                label_userdata = tk.Label(frame, text = 'Loading...', **self.styling.get(font_size = 'small', object_type = tk.Label))
                
                label_title.grid(row = 0, column = 0, sticky = 'NESW')
                button_editor.grid(row = 1, column = 0, sticky = 'NESW')
                button_connect.grid(row = 2, column = 0, sticky = 'NESW')
                button_host.grid(row = 3, column = 0, sticky = 'NESW')
                button_settings.grid(row = 4, column = 0, sticky = 'NESW')
                button_server_settings.grid(row = 5, column = 0, sticky = 'NESW')
                button_quit.grid(row = 6, column = 0, sticky = 'NESW')
                label_userdata.grid(row = 7, column = 0, sticky = 'NESW')
                self.styling.set_weight(frame, 1, 8)
                
            class settings:
                config = {'name': 'Settings'}
                
                @classmethod
                def on_load(self):
                    self.button_close.config(command = self.choose_accept) #can't use functools with classmethods inside of classes that haven't been created yet
                    self.button_cancel.config(command = self.choose_cancel)
                    self.button_reset_default.config(command = self.choose_reset_default)
                    self.button_match_requirements.config(command = self.meet_requirements)
                    
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    
                    self.fetch_settings(os.path.join(sys.path[0], 'user', 'config.json'))
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                @classmethod
                def choose_cancel(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def choose_accept(self):
                    self.push_settings(os.path.join(sys.path[0], 'user', 'config.json'))
                       
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def choose_reset_default(self):
                    self.fetch_settings(os.path.join(sys.path[0], 'user', 'default_config.json'))
                
                @classmethod
                def push_settings(self, path):
                    with open(path, 'r') as file:
                        settingsdict = json.load(file)
                        
                    settingsdict['graphics']['PILrender'] = [True, False][self.pilrender_flipswitch.state]
                    settingsdict['graphics']['model quality'] = self.mdlquality_flipswitch.state
                    settingsdict['hud']['chat']['position'] = self.chatalign_flipswitch.state
                    settingsdict['hud']['chat']['colour'] = self.chatcol_var.get()
                    settingsdict['hud']['chat']['fontsize'] = self.chatsize_var.get()
                    settingsdict['hud']['chat']['font'] = self.chatfont_var.get()
                    settingsdict['hud']['chat']['maxlen'] = self.chatmaxlen_var.get()
                    settingsdict['hud']['chat']['persist time'] = self.chatpersisttime_var.get()
                    settingsdict['user']['name'] = self.username_var.get()
                    settingsdict['network']['interpolations per second'] = self.interp_var.get()
                    settingsdict['default window state'] = self.windowzoom_flipswitch.state
                    
                    with open(os.path.join(sys.path[0], 'user', 'config.json'), 'w') as file:
                       json.dump(settingsdict, file, sort_keys=True, indent='\t')
                
                @classmethod
                def fetch_settings(self, path):
                    with open(path, 'r') as file:
                        settingsdict = json.load(file)
                    if settingsdict['graphics']['PILrender']:
                        self.pilrender_flipswitch.on_option_press(0, run_binds = False)
                    else:
                        self.pilrender_flipswitch.on_option_press(1, run_binds = False)
                    self.mdlquality_flipswitch.on_option_press(settingsdict['graphics']['model quality'], run_binds = False)
                    self.chatalign_flipswitch.on_option_press(settingsdict['hud']['chat']['position'], run_binds = False)
                    self.chatcol_var.set(settingsdict['hud']['chat']['colour'])
                    self.chatsize_var.set(settingsdict['hud']['chat']['fontsize'])
                    self.chatfont_var.set(settingsdict['hud']['chat']['font'])
                    self.chatmaxlen_var.set(settingsdict['hud']['chat']['maxlen'])
                    self.chatpersisttime_var.set(settingsdict['hud']['chat']['persist time'])
                    self.username_var.set(settingsdict['user']['name'])
                    self.interp_var.set(settingsdict['network']['interpolations per second'])
                    self.windowzoom_flipswitch.on_option_press(settingsdict['default window state'], run_binds = False)
                
                @classmethod
                def meet_requirements(self):
                    messagebox.showinfo('Installing packages...', 'Installation of all required packages will now start in the console\n\nThe "install packages" button will always remain in settings because the requirements may change over time')
                    print('Running pip using "requirements.txt...')
                    os.system('py -m pip install -r "{}"'.format(os.path.join(sys.path[0], 'requirements.txt')))
                    print('All installations are now finished!')
                
                frame = tk.Frame(main.page_frame)
                
                settings_frame = tk.Frame(frame)
                
                cat_general_label = tk.Label(settings_frame, text = 'General', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                windowzoom_label = tk.Label(settings_frame, text = 'Default window zoom', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                windowzoom_flipswitch = TkFlipSwitch(settings_frame, options = [{'text': 'Windowed', 'command': print},
                                                                                {'text': 'Maximised', 'command': print},
                                                                                {'text': 'Fullscreen', 'command': print}], **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                cat_graphics_label = tk.Label(settings_frame, text = 'Graphics', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                pilrender_label = tk.Label(settings_frame, text = 'PIL rendering', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                pilrender_flipswitch = TkFlipSwitch(settings_frame, options = [{'text': 'On', 'command': print},
                                                                               {'text': 'Off', 'command': print}], **self.styling.get(font_size = 'medium', object_type = tk.Button))
                mdlquality_label = tk.Label(settings_frame, text = 'Model quality', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                mdlquality_flipswitch = TkFlipSwitch(settings_frame, options = [{'text': 'Low', 'command': print},
                                                                                {'text': 'Medium', 'command': print},
                                                                                {'text': 'High', 'command': print},
                                                                                {'text': 'Full', 'command': print}], **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                cat_hud_label = tk.Label(settings_frame, text = 'HUD', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                chatalign_label = tk.Label(settings_frame, text = 'Chat alignment', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                chatalign_flipswitch = TkFlipSwitch(settings_frame, options = [{'text': 'Top left', 'command': print},
                                                                               {'text': 'Top right', 'command': print},
                                                                               {'text': 'Bottom left', 'command': print},
                                                                               {'text': 'Bottom right', 'command': print}], **self.styling.get(font_size = 'medium', object_type = tk.Button))
                chatcol_label = tk.Label(settings_frame, text = 'Chat colour', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                chatcol_var = tk.StringVar()
                chatcol_entry = tk.Entry(settings_frame, textvariable = chatcol_var, **self.styling.get(font_size = 'medium', object_type = tk.Entry))
                chatfont_label = tk.Label(settings_frame, text = 'Chat font', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                chatfont_var = tk.StringVar()
                chatfont_entry = tk.Entry(settings_frame, textvariable = chatfont_var, **self.styling.get(font_size = 'medium', object_type = tk.Entry))
                chatsize_label = tk.Label(settings_frame, text = 'Chat size', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                chatsize_var = tk.IntVar()
                chatsize_spinbox = tk.Spinbox(settings_frame, from_ = 0, to = 128, textvariable = chatsize_var, **self.styling.get(font_size = 'medium', object_type = tk.Spinbox))
                chatmaxlen_label = tk.Label(settings_frame, text = 'Chat messages to display', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                chatmaxlen_var = tk.IntVar()
                chatmaxlen_spinbox = tk.Spinbox(settings_frame, from_ = 0, to = 128, textvariable = chatmaxlen_var, **self.styling.get(font_size = 'medium', object_type = tk.Spinbox))
                chatpersisttime_label = tk.Label(settings_frame, text = 'Chat persist time',
                                            **self.styling.get(font_size = 'medium', object_type = tk.Label))
                chatpersisttime_var = tk.IntVar()
                chatpersisttime_spinbox = tk.Spinbox(settings_frame, from_ = 0, to = 128, textvariable = chatpersisttime_var,
                                                **self.styling.get(font_size = 'medium', object_type = tk.Spinbox))
                
                cat_user_label = tk.Label(settings_frame, text = 'Network', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                username_label = tk.Label(settings_frame, text = 'Username', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                username_var = tk.StringVar()
                username_entry = tk.Entry(settings_frame, textvariable = username_var, **self.styling.get(font_size = 'medium', object_type = tk.Entry))
                interp_label = tk.Label(settings_frame, text = 'Interpolations per second', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                interp_var = tk.IntVar()
                interp_spinbox = tk.Spinbox(settings_frame, textvariable = interp_var, from_ = 0, to = 9999, **self.styling.get(font_size = 'medium', object_type = tk.Spinbox))
                
                button_close = tk.Button(frame, text = 'Accept', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_cancel = tk.Button(frame, text = 'Cancel', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_reset_default = tk.Button(frame, text = 'Reset to default', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_match_requirements = tk.Button(frame, text = 'Click to install any required packages...', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                widget_row = 0
                
                cat_general_label.grid(row = widget_row, column = 0, columnspan = 2, sticky = 'NESW')
                windowzoom_label.grid(row = widget_row + 1, column = 0, sticky = 'NESW')
                windowzoom_flipswitch.grid(row = widget_row + 1, column = 1, sticky = 'NESW')
                
                widget_row += 2
                
                cat_graphics_label.grid(row = widget_row, column = 0, columnspan = 2, sticky = 'NESW')
                pilrender_label.grid(row = widget_row + 1, column = 0, sticky = 'NESW')
                pilrender_flipswitch.grid(row = widget_row + 1, column = 1, sticky = 'NESW')
                mdlquality_label.grid(row = widget_row + 2, column = 0, sticky = 'NESW')
                mdlquality_flipswitch.grid(row = widget_row + 2, column = 1, sticky = 'NESW')
                
                widget_row += 3
                
                cat_hud_label.grid(row = widget_row, column = 0, columnspan = 2, sticky = 'NESW')
                chatalign_label.grid(row = widget_row + 1, column = 0, sticky = 'NESW')
                chatalign_flipswitch.grid(row = widget_row + 1, column = 1, sticky = 'NESW')
                chatcol_label.grid(row = widget_row + 2, column = 0, sticky = 'NESW')
                chatcol_entry.grid(row = widget_row + 2, column = 1, sticky = 'NESW')
                chatfont_label.grid(row = widget_row + 3, column = 0, sticky = 'NESW')
                chatfont_entry.grid(row = widget_row + 3, column = 1, sticky = 'NESW')
                chatsize_label.grid(row = widget_row + 4, column = 0, sticky = 'NESW')
                chatsize_spinbox.grid(row = widget_row + 4, column = 1, sticky = 'NESW')
                chatmaxlen_label.grid(row = widget_row + 5, column = 0, sticky = 'NESW')
                chatmaxlen_spinbox.grid(row = widget_row + 5, column = 1, sticky = 'NESW')
                chatpersisttime_label.grid(row = widget_row + 6, column = 0, sticky = 'NESW')
                chatpersisttime_spinbox.grid(row = widget_row + 6, column = 1, sticky = 'NESW')
                
                widget_row += 7
                
                cat_user_label.grid(row = widget_row, column = 0, columnspan = 2, sticky = 'NESW')
                username_label.grid(row = widget_row + 1, column = 0, sticky = 'NESW')
                username_entry.grid(row = widget_row + 1, column = 1, sticky = 'NESW')
                interp_label.grid(row = widget_row + 2, column = 0, sticky = 'NESW')
                interp_spinbox.grid(row = widget_row + 2, column = 1, sticky = 'NESW')
                
                widget_row += 3
                
                settings_frame.grid(row = 0, column = 0, columnspan = 3, sticky = 'NESW')
                button_match_requirements.grid(row = 1, column = 0, columnspan = 3, sticky = 'NESW')
                button_close.grid(row = 2, column = 0, sticky = 'NESW')
                button_cancel.grid(row = 2, column = 1, sticky = 'NESW')
                button_reset_default.grid(row = 2, column = 2, sticky = 'NESW')
                
                self.styling.set_weight(settings_frame, 2, widget_row, dorows = False)
                frame.columnconfigure(0, weight = 1)
                frame.columnconfigure(1, weight = 1)
                frame.columnconfigure(2, weight = 1)
                frame.rowconfigure(0, weight = 1)
            
            class connect_server:
                config = {'name': 'Connect'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    self.populate_server_list()
                    
                    self.serverlist_list.bind('<Return>', self.choose_server)
                    self.addserver_choose_button.config(command = self.add_server)
                    
                    self.button_back.config(command = self.return_to_menu)
                    self.button_connect.config(command = self.choose_server)
                    
                    with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
                        settingsdata = json.load(file)
                    
                    self.vars.tickrate.set(settingsdata['network']['default tickrate'])
                    self.vars.port.set(settingsdata['network']['default port'])
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                @classmethod
                def populate_server_list(self):
                    with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
                        settingsdata = json.load(file)
                    self.serverlist_list.delete(0, tk.END)
                    formatter = '{} ({}:{}){}'
                    for server in settingsdata['network']['servers']:
                        port = server['port']
                        if port == 'normal':
                            port = settingsdata['network']['default port']
                        if server['internal']:
                            additional_text = ' - limited to local network'
                        else:
                            additional_text = ''
                        self.serverlist_list.insert(tk.END, formatter.format(server['name'], server['address'], server['port'], additional_text))
                
                @classmethod
                def return_to_menu(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def choose_server(self, event = None):
                    curselection = self.serverlist_list.curselection()
                    if not curselection == ():
                        with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
                            settingsdata = json.load(file)
                        server_target = settingsdata['network']['servers'][curselection[0]]
                        self.config['methods'].uiobject.call_trigger('connect to server', [server_target])
                
                @classmethod
                def add_server(self):
                    with open(os.path.join(sys.path[0], 'user', 'config.json')) as file:
                        settingsdata = json.load(file)
                        
                    sv_dict = {'address': self.vars.address.get(),
                               'internal': not bool(self.addserver_islocal_flipswitch.state),
                               'name': self.vars.name.get(),
                               'port': self.vars.port.get(),
                               'tickrate': self.vars.tickrate.get()}
                    try:
                        sv_dict['port'] = int(sv_dict['port'])
                    except: #is a word (normal), do nothing
                        sv_dict['port'] = 'normal'
                    settingsdata['network']['servers'].append(sv_dict)
                    
                    with open(os.path.join(sys.path[0], 'user', 'config.json'), 'w') as file:
                        json.dump(settingsdata, file, sort_keys=True, indent='\t')
                
                    self.populate_server_list()
                    self.vars.address.set('')
                    self.vars.name.set('')
                    self.vars.tickrate.set(settingsdata['network']['default tickrate'])
                    self.vars.port.set(settingsdata['network']['default port'])
                
                class vars:
                    address = tk.StringVar()
                    port = tk.StringVar()
                    name = tk.StringVar()
                    tickrate = tk.IntVar()
                
                frame = tk.Frame(main.page_frame)
                
                serverlist_frame = tk.Frame(frame)
                serverlist_list = tk.Listbox(serverlist_frame, **self.styling.get(font_size = 'small', object_type = tk.Listbox))
                serverlist_bar = tk.Scrollbar(serverlist_frame, command = serverlist_list.yview)
                serverlist_list.config(yscrollcommand = serverlist_bar.set)
                
                button_connect = tk.Button(frame, text = 'Connect', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_back = tk.Button(frame, text = 'Return to menu', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                addserver_frame = tk.Frame(frame)
                addserver_choose_button = tk.Button(addserver_frame, text = 'Add server', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                addserver_name_label = tk.Label(addserver_frame, text = 'Name', **self.styling.get(font_size = 'small', object_type = tk.Label))
                addserver_name_entry = tk.Entry(addserver_frame, textvariable = vars.name, **self.styling.get(font_size = 'small', object_type = tk.Entry))
                addserver_address_label = tk.Label(addserver_frame, text = 'Address', **self.styling.get(font_size = 'small', object_type = tk.Label))
                addserver_address_entry = tk.Entry(addserver_frame, textvariable = vars.address, **self.styling.get(font_size = 'small', object_type = tk.Entry))
                addserver_port_label = tk.Label(addserver_frame, text = 'Port', **self.styling.get(font_size = 'small', object_type = tk.Label))
                addserver_port_spinbox = tk.Spinbox(addserver_frame, textvariable = vars.port, from_ = 1024, to = 65535, **self.styling.get(font_size = 'small', object_type = tk.Spinbox))
                addserver_tickrate_label = tk.Label(addserver_frame, text = 'Tickrate', **self.styling.get(font_size = 'small', object_type = tk.Label))
                addserver_tickrate_spinbox = tk.Spinbox(addserver_frame, textvariable = vars.tickrate, from_ = 1, to = 1024, **self.styling.get(font_size = 'small', object_type = tk.Spinbox))
                addserver_islocal_flipswitch = TkFlipSwitch(addserver_frame, options = [{'text': 'Local machine only', 'command': print},
                                                                                        {'text': 'Open to LAN', 'command': print}], **self.styling.get(font_size = 'small', object_type = tk.Button))
                
                serverlist_bar.pack(side = tk.RIGHT, fill = tk.Y)
                serverlist_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
                
                serverlist_frame.grid(row = 0, column = 0, columnspan = 2, sticky = 'NESW')
                button_back.grid(row = 1, column = 0, sticky = 'NESW')
                button_connect.grid(row = 1, column = 1, sticky = 'NESW')
                addserver_frame.grid(row = 2, column = 0, columnspan = 2, sticky = 'NESW')
                
                addserver_name_label.grid(row = 0, column = 0, sticky = 'NESW')
                addserver_name_entry.grid(row = 0, column = 1, sticky = 'NESW')
                addserver_address_label.grid(row = 1, column = 0, sticky = 'NESW')
                addserver_address_entry.grid(row = 1, column = 1, sticky = 'NESW')
                addserver_port_label.grid(row = 2, column = 0, sticky = 'NESW')
                addserver_port_spinbox.grid(row = 2, column = 1, sticky = 'NESW')
                addserver_tickrate_label.grid(row = 3, column = 0, sticky = 'NESW')
                addserver_tickrate_spinbox.grid(row = 3, column = 1, sticky = 'NESW')
                addserver_islocal_flipswitch.grid(row = 4, column = 0, columnspan = 2, sticky = 'NESW')
                addserver_choose_button.grid(row = 0, column = 2, rowspan = 4, sticky = 'NESW')
                
                self.styling.set_weight(frame, 2, 4)
                frame.rowconfigure(1, weight = 0)
                frame.rowconfigure(2, weight = 0)
                frame.rowconfigure(3, weight = 0)
                
                self.styling.set_weight(addserver_frame, 3, 4)
                
            class game:
                config = {'name': 'Game'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    self.config['methods'].uiobject.call_trigger('create game object', [self.canvas])
                    
                    #set keybinds for returning to the menu
                    with open(os.path.join(sys.path[0], 'user', 'keybinds.json'), 'r') as file:
                        keybinds_data = json.load(file)
                    if type(keybinds_data['window']['return to menu']) == str:
                        keybinds_data['window']['return to menu'] = [keybinds_data['window']['return to menu']]
                    for key in keybinds_data['window']['return to menu']:
                        self.canvas.bind('<{}>'.format(key), self.return_to_menu)
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                    self.config['methods'].uiobject.call_trigger('close game')
                
                @classmethod
                def return_to_menu(self, event = None):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                frame = tk.Frame(main.page_frame)
                
                canvas = tk.Canvas(frame, width = 800, height = 600, **self.styling.get(font_size = 'medium', object_type = tk.Canvas))
                
                canvas.grid(row = 0, column = 0)
                
                self.styling.set_weight(frame, 1, 1)
                frame.rowconfigure(1, weight = 0)
            
            class editor_choose_file:
                config = {'name': 'Editor'}
                
                @classmethod
                def on_load(self):
                    for name in os.listdir(os.path.join(sys.path[0], 'server', 'maps')):
                        if not name.startswith('_'):
                            self.listbox_box.insert(tk.END, name)
                    
                    self.button_choose.config(command = self.open_map)
                    self.button_go_back.config(command = self.return_to_menu)
                    self.button_new.config(command = self.create_new_map)
                    
                    self.listbox_box.bind('<Return>', self.open_map)
                    
                    self.frame.pack(fill = tk.BOTH, expand = True)
                
                @classmethod
                def on_close(self):
                    self.listbox_box.delete(0, tk.END)
                    self.frame.pack_forget()
                
                @classmethod
                def open_map(self, event = None):
                    index = self.listbox_box.curselection()
                    if type(index[0]) == int: #if there is a selection
                        map_name = self.listbox_box.get(index[0])
                        self.config['methods'].uiobject.call_trigger('edit map', [map_name])
                
                @classmethod
                def return_to_menu(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def create_new_map(self):
                    if self.entry_mapname.get() == '':
                        messagebox.showerror('Error while creating new map', 'You must enter a map name')
                    elif os.path.isdir(os.path.join(sys.path[0], 'server', 'maps', self.entry_mapname.get())):
                        messagebox.showerror('Error while creating new map', 'The map name "{}" is already in use'.format(self.entry_mapname.get()))
                    else:
                        try:
                            shutil.copytree('_template', self.entry_mapname.get())
                        except:
                            messagebox.showerror('Unidentified error', 'Unidentified error while creating map with name "{}"\n\nRemember! It must be a valid directory name'.format(self.entry_mapname.get()))
                
                frame = tk.Frame(main.page_frame)
                
                listbox_frame = tk.Frame(frame)
                listbox_box = tk.Listbox(listbox_frame, **self.styling.get(font_size = 'small', object_type = tk.Listbox))
                listbox_bar = tk.Scrollbar(listbox_frame, command = listbox_box.yview)
                listbox_box.config(yscrollcommand = listbox_bar.set)
                
                listbox_bar.pack(side = tk.RIGHT, fill = tk.Y)
                listbox_box.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
                
                entry_mapname = tk.Entry(frame, **self.styling.get(font_size = 'medium', object_type = tk.Entry))
                button_new = tk.Button(frame, text = 'Create new map', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_choose = tk.Button(frame, text = 'Open map', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_go_back = tk.Button(frame, text = 'Return to menu', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                listbox_frame.grid(row = 0, column = 0, columnspan = 4, sticky = 'NESW')
                
                entry_mapname.grid(row = 1, column = 0, sticky = 'NESW')
                button_new.grid(row = 1, column = 1, sticky = 'NESW')
                button_choose.grid(row = 1, column = 2, sticky = 'NESW')
                button_go_back.grid(row = 1, column = 3, sticky = 'NESW')
                
                self.styling.set_weight(frame, 4, 2)
                frame.rowconfigure(1, weight = 0)
            
            class editor:
                config = {'name': 'Editor'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    self.config['methods'].uiobject.call_trigger('start editor', [self.frame, self.config['methods']])
                
                @classmethod
                def on_close(self):
                    self.config['methods'].uiobject.call_trigger('close editor', [])
                    self.frame.pack_forget()
                
                frame = tk.Frame(main.page_frame)
            
            class server_settings:
                config = {'name': 'Server settings'}
                
                @classmethod
                def on_load(self):
                    self.button_close.config(command = self.choose_accept)
                    self.button_cancel.config(command = self.choose_cancel)
                    self.button_reset_default.config(command = self.choose_reset_default)
                    
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    
                    self.fetch_settings(os.path.join(sys.path[0], 'server', 'config.json'))
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                @classmethod
                def choose_cancel(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def choose_accept(self):
                    self.push_settings(os.path.join(sys.path[0], 'server', 'config.json'))
                       
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def choose_reset_default(self):
                    self.fetch_settings(os.path.join(sys.path[0], 'server', 'default_config.json'))
                
                @classmethod
                def push_settings(self, path):
                    with open(path, 'r') as file:
                        settingsdict = json.load(file)
                    
                    settingsdict['network']['accurate hit detection'] = bool(self.hitbox_precision_flipswitch.state)
                    
                    with open(os.path.join(sys.path[0], 'server', 'config.json'), 'w') as file:
                       json.dump(settingsdict, file, sort_keys=True, indent='\t')
                
                @classmethod
                def fetch_settings(self, path):
                    with open(path, 'r') as file:
                        settingsdict = json.load(file)
                    
                    self.hitbox_precision_flipswitch.on_option_press(settingsdict['network']['accurate hit detection'])
                
                frame = tk.Frame(main.page_frame)
                
                settings_frame = tk.Frame(frame)
                
                widget_row = 0
                
                #network
                cat_network = tk.Label(settings_frame, text = 'Network', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                hitbox_precision_label = tk.Label(settings_frame, text = 'Hitbox precision', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                hitbox_precision_flipswitch = TkFlipSwitch(settings_frame, options = [{'text': 'Low (stock python)'},
                                                                                      {'text': 'High (requires numpy)'}], **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                cat_network.grid(row = widget_row, column = 0, columnspan = 2, sticky = 'NESW')
                hitbox_precision_label.grid(row = widget_row + 1, column = 0, sticky = 'NESW')
                hitbox_precision_flipswitch.grid(row = widget_row + 1, column = 1, sticky = 'NESW')
                
                widget_row += 2
                
                #functional buttons
                button_close = tk.Button(frame, text = 'Accept', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_cancel = tk.Button(frame, text = 'Cancel', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_reset_default = tk.Button(frame, text = 'Reset to default', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                settings_frame.grid(row = 0, column = 0, columnspan = 3, sticky = 'NESW')
                button_close.grid(row = 2, column = 0, sticky = 'NESW')
                button_cancel.grid(row = 2, column = 1, sticky = 'NESW')
                button_reset_default.grid(row = 2, column = 2, sticky = 'NESW')
                
                #set weights
                self.styling.set_weight(settings_frame, 2, widget_row, dorows = False)
                frame.columnconfigure(0, weight = 1)
                frame.columnconfigure(1, weight = 1)
                frame.columnconfigure(2, weight = 1)
                frame.rowconfigure(0, weight = 1)
                
        uiobjects.main = main
        self.uiobjects = uiobjects
        
        #apply additional setup to pages
        for itemname in dir(self.uiobjects):
            ismagicvariable = itemname.startswith('__') and itemname.endswith('__')
            isspecialcase = itemname in ['main']
            if not (ismagicvariable or isspecialcase):
                item = self.uiobjects.__getattribute__(self.uiobjects, itemname) #get class from name
                if not 'config' in dir(item):
                    item.config = {'name': itemname}
                item.config['methods'] = PageMethods(self, item)
        
        self.ready['tkthread'] = True
        self.root.mainloop()
        self.call_trigger('window closed')
    
    def load(self, page, *pageargs, **pagekwargs):
        'Load a page'
        if (not self.uiobjects.main.current == None) and 'on_close' in dir(self.uiobjects.main.current):
            self.uiobjects.main.current.on_close() #close current page if one exists
        self.uiobjects.main.current = page #set loading page as current page
        if 'on_load' in dir(page):
            page.on_load(*pageargs, **pagekwargs) #run the load function for the page
        page.config['methods'].set_title(page.config["name"]) #set correct window title
    
    def set_title(self, title):
        self.uiobjects.main.title = title
        if self.uiobjects.main.current == None:
            self.uiobjects.root.title(self.uiobjects.main.title)
        elif self.uiobjects.main.current.config['methods'].current_title == None:
            self.uiobjects.root.title(self.uiobjects.main.title)
        else:
            self.uiobjects.main.current.config['methods'].set_title(self.uiobjects.main.current.config['methods'].current_title)
    
    def set_geometry(self, geometry):
        self.uiobjects.main.geometry = geometry
        self.root.geometry(self.uiobjects.main.geometry)
    
    def set_trigger(self, string, function):
        if string in self.triggers:
            self.triggers[string].append(function)
        else:
            self.triggers[string] = [function]
    
    def clear_triggers(self, string):
        if string in self.triggers:
            self.triggers.pop(string)
    
    def call_trigger(self, string, args = None):
        if string in self.triggers:
            for function in self.triggers[string]:
                if args == None:
                    function()
                else:
                    function(*args)
        else:
            raise ValueError('Trigger "{}" hasn\'t been registered'.format(string))

class PageMethods:
    def __init__(self, uiobject, page):
        self.uiobject = uiobject
        self.page = page
        
        self.current_title = None
    
    def set_title(self, title = None):
        if not title == None:
            self.current_title = title
        self.uiobject.root.title('{} - {}'.format(self.uiobject.uiobjects.main.title, self.current_title))

class TkFlipSwitch:
    def __init__(self, container, **kwargs):
        self.container = container

        self.required_internal_args = ['options']
        self.state = 0
        
        self.filtered_args = {}
        self.internal_args = {}
        for key in kwargs:
            if key in self.required_internal_args:
                self.internal_args[key] = kwargs[key]
            else:
                self.filtered_args[key] = kwargs[key]

        for arg in self.required_internal_args:
            if not arg in self.internal_args:
                raise TypeError('Missing keyword argument "{}"'.format(arg))

        self.frame = tk.Frame(container)
        self.buttons = []
        for option in self.internal_args['options']:
            self.buttons.append(tk.Button(self.frame, text = option['text'], command = functools.partial(self.on_option_press, len(self.buttons)), **self.filtered_args))

        self.on_option_press(self.state, run_binds = False)

        for i in range(len(self.buttons)):
            self.buttons[i].grid(column = i, row = 0, sticky = 'NESW')
            self.frame.columnconfigure(i, weight = 1)
        self.frame.rowconfigure(0, weight = 1)

        self.pack = self.frame.pack
        self.grid = self.frame.grid
        self.destroy = self.frame.destroy
        self.pack_forget = self.frame.pack_forget

    def on_option_press(self, index, run_binds = True):
        for button in self.buttons:
            button.config(state = tk.NORMAL, **self.filtered_args)
        self.buttons[index].config(relief = tk.FLAT, state = tk.DISABLED)
        self.state = index
        
        if run_binds and 'command' in self.internal_args['options'][index] and (not self.internal_args['options'][index]['command'] is None):
            self.internal_args['options'][index]['command']()