import pyglet
import random
import sys
from pyglet.sprite import Sprite

KEY_MAP = {pyglet.window.key._1: 0x1,
           pyglet.window.key._2: 0x2,
           pyglet.window.key._3: 0x3,
           pyglet.window.key._4: 0xc,
           pyglet.window.key.A: 0x4,
           pyglet.window.key.Z: 0x5,
           pyglet.window.key.E: 0x6,
           pyglet.window.key.R: 0xd,
           pyglet.window.key.Q: 0x7,
           pyglet.window.key.S: 0x8,
           pyglet.window.key.D: 0x9,
           pyglet.window.key.F: 0xe,
           pyglet.window.key.W: 0xa,
           pyglet.window.key.X: 0,
           pyglet.window.key.C: 0xb,
           pyglet.window.key.V: 0xf
          }

LOGGING = False

def log(msg):
    if LOGGING:
        print(msg)

class cpu(pyglet.window.Window):
    memory = [0]*4096 # max 4096
    gpio = [0]*16 # max 16
    display_buffer = [0]*32*64 # 64*32
    stack = []
    key_inputs = [0]*16
    fonts = [0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
             0x20, 0x60, 0x20, 0x20, 0x70, # 1
             0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
             0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
             0x90, 0x90, 0xF0, 0x10, 0x10, # 4
             0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
             0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
             0xF0, 0x10, 0x20, 0x40, 0x40, # 7
             0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
             0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
             0xF0, 0x90, 0xF0, 0x90, 0x90, # A
             0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
             0xF0, 0x80, 0x80, 0x80, 0xF0, # C
             0xE0, 0x90, 0x90, 0x90, 0xE0, # D
             0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
             0xF0, 0x80, 0xF0, 0x80, 0x80  # F
             ]

    opcode = 0
    index = 0
    pc = 0
    exited = 0
    delay_timer = 0
    sound_timer = 0
    
    should_draw = False
    key_wait = False
    pixel = pyglet.resource.image('pixel.png')
    buzz = pyglet.resource.media('buzz.wav', streaming=False)   
    batch = pyglet.graphics.Batch()
    sprites = []
    for i in range(0,2048):
        sprites += [pyglet.sprite.Sprite(pixel,batch=batch)]
       
    def _0000(self):
        extracted_op = self.opcode & 0xf0ff
        try:
          self.funcmap[extracted_op]()
        except:
          print("Unknown instruction: %X" % self.opcode)

    def _00e0(self):
        log("clear screen")
        self.display_buffer = [0] * 64 * 32
        self.should_draw = True

    def _00ee(self):
        log("returns from subroutine")
        if self.stack:
            self.pc = self.stack[0]
            self.stack.pop()
    
    def _1000(self):
        log("jump to location nnn")
        addr = self.opcode & 0x0fff
        self.pc = addr

    def _2000(self):
        log("call subroutine at nnn")
        addr = self.opcode & 0x0fff
        self.stack = [self.pc] + self.stack
        self.pc = addr

    def _3000(self):
        log("skip next instruction if Vx == kk")
        val = self.opcode & 0x00ff
        if self.gpio[self.vx] == val:
            self.pc += 2

    def _4000(self):
        log("skip next instruction if vx != kk")
        val = self.opcode & 0x00ff
        if self.gpio[self.vx] != val:
            self.pc += 2

    def _5000(self):
        log("skip next instruction if vx = vy")
        if self.gpio[self.vx] == self.gpio[self.vy]:
            self.pc += 2

    def _6000(self):
        log("set vx = kk")
        val = self.opcode & 0x00ff
        self.gpio[self.vx] = val

    def _7000(self):
        log("set vx = vx + kk")
        val = self.opcode & 0x00ff
        self.gpio[self.vx] += val

    def _8000(self):
        extracted_op = self.opcode & 0xf00f
        extracted_op += 0xff0
        try:
          self.funcmap[extracted_op]()
        except:
          print("Unknown instruction: %X" % self.opcode)

    def _8ff0(self):
        log("set vx = vy")
        self.gpio[self.vx] = self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff
    
    def _8ff1(self):
        log ("set vx = vx OR vy")
        self.gpio[self.vx] = self.gpio[self.vx] | self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff
    

    def _8ff2(self):
        log ("set vx = vx AND vy")
        self.gpio[self.vx] = self.gpio[self.vx] & self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff


    def _8ff3(self):
        log ("set vx = vx XOR vy")
        self.gpio[self.vx] = self.gpio[self.vx] ^ self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff


    def _8ff4(self):
        log ("set vx = vx + vy, set vf = carry")
        self.gpio[0xf] = 1 if self.gpio[self.vx] + self.gpio[self.vy] > 0xff else  0
        self.gpio[self.vx] = self.gpio[self.vx] + self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff
    
    def _8ff5(self):
        log ("set vx = vx - vy, set vf = NOT borrow")
        self.gpio[0xf] = 1 if self.gpio[self.vx] > self.gpio[self.vy] else  0
        self.gpio[self.vx] = self.gpio[self.vx] - self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff

    def _8ff6(self):
        log("Shifts VX right by one. VF is set to the value of the least significant bit of VX before the shift.")
        self.gpio[0xf] = self.gpio[self.vx] & 0x0001
        self.gpio[self.vx] = self.gpio[self.vx] >> 1

    def _8ff7(self):
        log ("set vx = vy - vx, set vf = NOT borrow")
        self.gpio[0xf] = 1 if self.gpio[self.vx] <= self.gpio[self.vy] else  0
        self.gpio[self.vx] = self.gpio[self.vy] - self.gpio[self.vx]
        self.gpio[self.vx] &= 0xff
    
    def _8ffe(self):
        log ("set vx = vx SHL 1")
        self.gpio[0xf] = self.gpio[self.vx] >> 7
        self.gpio[self.vx] = self.gpio[self.vx] << 1
        self.gpio[self.vx] &= 0xff

    def _9000(self):
        log("Skip next instruction if Vx != Vy.")
        if self.gpio[self.vx] != self.gpio[self.vy]:
            self.pc += 2

    def _a000(self):
        log("value of register nnn = nnn")
        val = self.opcode & 0x0fff
        self.index = val

    def _b000(self):
        log("jump to location nnn + V0")
        val = self.opcode & 0x0fff
        self.pc = self.gpio[0] + val

    def _c000(self):
        log("set vx = random byte AND kk")
        random_value = random.randrange(256)
        val = self.opcode & 0x00ff
        self.gpio[self.vx] = random_value & val
        self.gpio[self.vx] &= 0xff

    def _d000(self):
        log("display n-byte sprite starting at memory location I at (vx, vy), set vf = collision")
        self.gpio[0xf] = 0
        n = self.opcode & 0x000f
        x = self.gpio[self.vx] & 0x00ff
        y = self.gpio[self.vy] & 0x00ff
        row = 0
        while row < n:
            curr_row = self.memory[row + self.index]
            pixel_offset = 0
            while pixel_offset < 8:
              loc = x + pixel_offset + ((y + row) * 64)
              pixel_offset += 1
              if (y + row) >= 32 or (x + pixel_offset - 1) >= 64:
                # ignore pixels outside the screen
                continue
              mask = 1 << 8-pixel_offset
              curr_pixel = (curr_row & mask) >> (8-pixel_offset)
              self.display_buffer[loc] ^= curr_pixel
              if self.display_buffer[loc] == 0:
                self.gpio[0xf] = 1
              else:
                self.gpio[0xf] = 0
            row += 1
        self.should_draw = True

    def _e000(self):
        extracted_op = self.opcode & 0xf00f
        try:
          self.funcmap[extracted_op]()
        except:
          print("Unknown instruction: %X" % self.opcode)

    def _e00e(self):
        log("skip next instruction if key with the value of vx is pressed")
        if self.key_inputs[self.gpio[self.vx]]:
            self.pc += 2

    def _e001(self):
        log("skip next instruction if key with the value of vx is not pressed")
        if not self.key_inputs[self.gpio[self.vx]]:
            self.pc += 2

    def _f000(self):
        extracted_op = self.opcode & 0xf0ff
        try:
            self.funcmap[extracted_op]()
        except:
            print("Unknown instruction: %X" % self.opcode)

    def _f007(self):
        log("Set Vx = delay timer value.")
        self.gpio[self.vx] = self.delay_timer

    def _f00a(self):
        log("wait for a key press, store the alue of the key in vx")
        res = self.get_key()
        if res >= 0:
            self.gpio[self.vx] = res
        else:
            self.pc -= 2

    def _f015(self):
        log("set delay timer = vx")
        self.delay_timer = self.gpio[self.vx]

    def _f018(self):
        log("set sound timer = vx")
        self.sound_timer = self.gpio[self.vx]

    def _f01e(self):
        log("Adds VX to I. if overflow, vf = 1")
        self.index += self.gpio[self.vx]
        if self.index > 0xfff:
          self.gpio[0xf] = 1
          self.index &= 0xfff
        else:
          self.gpio[0xf] = 0

    def _f029(self):
        log("set I = location of sprite for digit vx")
        self.index = int((5*(self.gpio[self.vx]))) & 0xfff

    def _f033(self):
        log("Store BCD representation of Vx in memory locations I, I+1, and I+2.")
        self.memory[self.index]   = self.gpio[self.vx] / 100
        self.memory[self.index+1] = (self.gpio[self.vx] % 100) / 10
        self.memory[self.index+2] = self.gpio[self.vx] % 10

    def _f055(self):
        log("Store registers V0 through Vx in memory starting at location I.")
        i = 0
        while i <= self.vx:
            self.memory[self.index + i] = self.gpio[i]
            i += 1
        self.index += self.vx + 1

    def _f065(self):
        log("Read registers V0 through Vx from memory starting at location I.")
        i = 0
        while i <= self.vx:
            self.gpio[i] = self.memory[self.index + i]
            i += 1
        self.index += self.vx + 1

    def __init__(self, *args, **kwargs):
        super(cpu, self).__init__(*args, **kwargs)
        self.funcmap = {0x0000: self._0000,
                        0x00e0: self._00e0,
                        0x00ee: self._00ee,
                        0x1000: self._1000,
                        0x2000: self._2000,
                        0x3000: self._3000,
                        0x4000: self._4000,
                        0x5000: self._5000,
                        0x6000: self._6000,
                        0x7000: self._7000,
                        0x8000: self._8000,
                        0x8ff0: self._8ff0,
                        0x8ff1: self._8ff1,
                        0x8ff2: self._8ff2,
                        0x8ff3: self._8ff3,
                        0x8ff4: self._8ff4,
                        0x8ff5: self._8ff5,
                        0x8ff6: self._8ff6,
                        0x8ff7: self._8ff7,
                        0x8ffe: self._8ffe,
                        0x9000: self._9000,
                        0xa000: self._a000,
                        0xb000: self._b000,
                        0xc000: self._c000,
                        0xd000: self._d000,
                        0xe000: self._e000,
                        0xe00e: self._e00e,
                        0xe001: self._e001,
                        0xf000: self._f000,
                        0xf007: self._f007,
                        0xf00a: self._f00a,
                        0xf015: self._f015,
                        0xf018: self._f018,
                        0xf01e: self._f01e,
                        0xf029: self._f029,
                        0xf033: self._f033,
                        0xf055: self._f055,
                        0xf065: self._f065}

    def draw(self):
        if not self.should_draw:
            return
        i = 0
        while i < 2048:
          if self.display_buffer[i] == 1:
            self.sprites[i].x = (i%64)*10
            self.sprites[i].y = 310 - ((i/64)*10)
            self.sprites[i].batch = self.batch
          else:
            self.sprites[i].batch = None
          i += 1
        self.clear() 
        self.batch.draw()
        self.flip() 
        self.should_draw = False

    def on_key_press(self, symbol, modifiers):
        log("key pressed {symbol}")
        if symbol in KEY_MAP.keys():
            self.key_inputs[KEY_MAP[symbol]] = 1
            if self.key_wait:
                self.key_wait = False
        else:
            super(cpu, self).on_key_press(symbol, modifiers)

    def on_key_release(self, symbol, modifiers):
        log("key released {symbol}")
        if symbol in KEY_MAP.keys():
            self.key_inputs[KEY_MAP[symbol]] = 0

    def get_key(self):
        i = 0
        while i < 16:
            if self.key_inputs[i] == 1:
                return i
            i += 1
        return -1
    
    def initialize(self):
        self.clear()
        self.key_inputs = [0] * 16
        self.display_buffer = [0] * 32 * 64
        self.memory = [0] * 4096
        self.gpio = [0] * 16
        self.sound_timer = 0
        self.delay_timer = 0
        self.opcode = 0
        self.index = 0
        self.pc = 0x200
        self.stack = []
        self.should_draw = False
        for i in range(80):
            self.memory[i] = self.fonts[i]

    def load_rom(self, path):
        log(f"loading the rom at {path}")
        binary = open(path, "rb").read()
        i = 0
        while i < len(binary):
            self.memory[i + 0x200] = binary[i]
            i += 1

    def cycle(self):
        self.opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        log("Current opcode: %X" % self.opcode)
        self.vx = (self.opcode & 0x0f00) >> 8
        self.vy = (self.opcode & 0x00f0) >> 4
        self.pc += 2
        extracted_opcode = self.opcode & 0xf000
        #input()
        try:
            self.funcmap[extracted_opcode]()
        except:
            print(f"Unknown instruction {self.opcode}")
        #timers
        if self.delay_timer > 0:
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1
            if self.sound_timer == 0:
                self.buzz.play()
                log("playing a sound")
    
    def main(self):
        if len(sys.argv) <= 1:
            print("USAGE: python chip8.py <path_to_ROM> <log>")
            return
        self.initialize()
        self.load_rom(sys.argv[1])
        while not self.exited:
            self.dispatch_events()
            self.cycle()
            self.draw()

if len(sys.argv) == 3 and sys.argv[2] == "log":
    LOGGING = True

chip8_emulator = cpu(640, 320)
chip8_emulator.main()
log("end")