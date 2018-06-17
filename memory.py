class Memory(object):
    def __init__(self, rom):
        self.ram = [0] * 0x800
        self.ppu_registers = [0] * 0x8
        self.apu_registers = [0] * 0x18
        self.disabled = [0] * 0x8
        self.rom = rom

    def get_memory(self, address):
        if address < 0x2000:
            return self.ram[address % 0x800]
        elif address < 0x4000:
            return self.ppu_registers[address % 0x008]
        elif address < 0x4018:
            return self.apu_registers[address - 0x4000]
        elif address < 0x4020:
            return self.disabled[address - 0x4018]
        else:
            return self.rom.get_address(address - 0x4020)

    def set_memory(self, address, value):
        if address < 0x2000:
            self.ram[address % 0x800] = value
        elif address < 0x4000:
            self.ppu_registers[address % 0x008] = value
        elif address < 0x4018:
            self.apu_registers[address - 0x4000] = value
        elif address < 0x4020:
            self.disabled[address - 0x4018] = value
        else:
            self.rom.set_address(address - 0x4020, value)