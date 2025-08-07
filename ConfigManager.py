import uos,gc
import ujson as json

class Config_Manager:
    def __init__(self, filename, default_config_file=None, default_config={}):
        self.config_file = filename
        if default_config_file:
            try:
                with open(default_config_file, 'r') as f:
                    self.default_config = json.load(f)
            except Exception:
                self.default_config = default_config
        else:
            self.default_config = default_config

        if self.config_file not in uos.listdir():
            self.save_config(self.default_config)
            
    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Debug: Loaded config ✘({e})")
            config = self.default_config.copy()
        gc.collect()
        return config
        
    def save_config(self, config):
        try:
            current_config = self.load_config()
            current_config.update(config)
            with open(self.config_file, 'w') as f:
                print("Debug: Saved config ✔")
                json.dump(current_config,f)
            gc.collect()
            return current_config
        except Exception as e:
            print(f"Debug: Saved config ✘{e}")
            gc.collect()
            return self.default_config.copy()
    
    def get_config(self, key, default=None):
        config = self.load_config()
        return config.get(key, default)

    def set_config(self, key, value):
        return self.save_config({key: value})

    def reset_config(self, keys=None):
        try:
            if keys is None:
                with open(self.config_file, 'w') as f:
                    json.dump(self.default_config.copy(), f)
                print(f"Debug: Reset all config ✔")
                gc.collect()
                return
            config = self.load_config()
            keys_to_reset = keys
            if isinstance(keys_to_reset, str):
                keys_to_reset = [keys_to_reset]

            for k in keys_to_reset:
                if k in self.default_config:
                    config[k] = self.default_config[k]
                    print(f"Debug: Reset '{k}' ✔")
                elif k in config:
                    del config[k]
                    print(f"Debug: Key '{k}' not in default_config, deleted ✘")
                else:
                    print(f"Debug: Key '{k}' not found in config ✘")
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            gc.collect()

        except Exception as e:
            gc.collect()
            print(f"Debug: Reset config ✘({e})")
