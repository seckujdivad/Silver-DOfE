import modules.items

class Generic(modules.items.ItemScript):
    def __init__(self, name, server):
        super().__init__(name, server)
        
        self.attributes.damage.destroyed_after = self.cfgs.item['destroyed after damage']
        self.attributes.damage.cooldown = self.cfgs.item['damage cooldown']
    
    def _tick(self):
        output = {}
        if self.attributes.first_tick:
            output['type'] = 'add'
            output['position'] = [self.attributes.pos.x, self.attributes.pos.y]
            output['rotation'] = self.attributes.rotation
            output['new'] = True
        
        elif not self.inside_map():
            output['type'] = 'remove'
        
        elif self.attributes.velocity.x != 0 or self.attributes.velocity.y != 0:
            self.attributes.pos.x += self.attributes.velocity.x
            self.attributes.pos.y += self.attributes.velocity.y
            
            output['type'] = 'update position'
            output['position'] = [self.attributes.pos.x, self.attributes.pos.y]
        
        for client in self.server.clients:
            damage_dealt = False
            if client.metadata.active and client.metadata.mode == 'player':
                if self.touching_player(client.metadata.pos.x, client.metadata.pos.y):
                    if self.attributes.damage.last is not None:
                        if (time.time() - self.attributes.damage.last) > self.attributes.damage.cooldown:
                            damage_dealt = True
                    else:
                        damage_dealt = True
            
            if damage_dealt and not self.attributes.creator == client:
                client.increment_health(0 - item['data']['damage']['player'], item['data']['display name'], item['creator'].metadata.username)
                item['last damage'] = time.time()
                
                client.push_health()
                
                if item['data']['destroyed after damage']:
                    output = {'type': 'remove'}
        
        return output


class ItemScriptFireball(Generic):
    def __init__(self, name, server):
        super().__init__(name, server)
        
    internal_name = 'fireball'


class ItemScriptSword(Generic):
    def __init__(self, name, server):
        super().__init__(name, server)
    
    internal_name = 'swordswipe'