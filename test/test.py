from cpu import CPU
from memory import Memory
from rom import Rom


def main():
    rom = Rom('nestest.nes')
    memory = Memory(rom)
    cpu = CPU(memory)
    cpu.program_counter = 0xC000
    cpu.interrupt_disable = 1
    for line in cpu.tick_debug():
        print line


if __name__ == '__main__':
    main()