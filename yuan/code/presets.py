import json
import os


class PresetManager:
    def __init__(self, path="presets.json"):
        self.path = path
        self.presets = self.load_presets()

    def load_presets(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {"默认连招": "j,0.1,0.2;left_click,0.1,0.3;k,0.05,0.1"}
        return {"默认连招": "j,0.1,0.2;left_click,0.1,0.3;k,0.05,0.1"}

    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.presets, f, ensure_ascii=False, indent=2)

    def add(self, name, seq):
        self.presets[name] = seq
        self.save()

    def delete(self, name):
        if name in self.presets:
            del self.presets[name]
            self.save()
