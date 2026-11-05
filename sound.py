"""Generated beeps via pygame.mixer - no audio asset files. Silence if no audio device."""
import math
import struct

import pygame

import config as C


class SoundPack:
    """4 synthesized tones (kill / level-up / boss / chest), stdlib PCM, no asset files."""

    def __init__(self):
        self.on = True
        self.ok = False
        self.sounds = {}
        self.gap = {}
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=1024)
            for name, (freq, ms, vol, min_gap) in C.SFX.items():
                self.sounds[name] = self._tone(freq, ms, vol)
                self.gap[name] = min_gap
            self.ok = True
        except Exception:
            self.on = False

    def _tone(self, freq, ms, vol):
        rate = 22050
        buf = bytearray()
        for i in range(int(rate * ms / 1000)):
            env = 1.0 - i / (rate * ms / 1000)
            v = int(vol * env * 32767 * math.sin(2 * math.pi * freq * i / rate))
            buf += struct.pack("<h", v)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def play(self, name):
        if not (self.on and self.ok) or name not in self.sounds:
            return
        now = pygame.time.get_ticks() / 1000.0
        if now - self.gap.get(name + "_t", -9.9) < self.gap[name]:
            return
        self.gap[name + "_t"] = now
        self.sounds[name].play()
