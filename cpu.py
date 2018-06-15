class AddressingModes(object):
    IMMEDIATE = 1
    ZERO_PAGE = 2
    ZERO_PAGE_X = 3
    ZERO_PAGE_Y = 4
    ABSOLUTE = 5
    ABSOLUTE_X = 6
    ABSOLUTE_Y = 7
    ABSOLUTE_X_NO_PAGE = 12
    INDIRECT_X = 8
    INDIRECT_Y = 9
    ACCUMULATOR = 10
    RELATIVE = 11
    IMPLIED = 12


class CPU(object):
    def __init__(self):
        # Registers
        self.accumulator = 0
        self.x = 0
        self.y = 0
        self.program_counter = 0x34
        self.stack_pointer = 0xFD
        # Status Register
        self.carry = 0
        self.zero = 0
        self.interrupt_disable = 0
        self.overflow = 0
        self.negative = 0
        self.decimal_mode = 0
        self.break_command = 0
        self.addressing_mode = AddressingModes.IMPLIED
        # Memory
        self.memory = [0] * 0xFFFF

        self.cycles = 0

    @property
    def status_register(self):
        return self.carry +\
               self.zero * 0x2 +\
               self.interrupt_disable * 0x4 +\
               self.decimal_mode * 0x8 +\
               self.break_command * 0x10 + \
               1 * 0x20 + \
               self.overflow * 0x40 +\
               self.negative * 0x80

    def tick(self):
        if self.cycles > 0:
            self.cycles -= 1
            return
        op_code = self.get_memory(self.program_counter)
        command, addressing_mode, operations, cycles = INSTRUCTIONS_MAP[op_code]
        self.addressing_mode = addressing_mode
        operand = self.get_operand_address(addressing_mode)
        self.program_counter += operations
        command(self, operand)
        self.cycles += cycles - 1

    def get_memory(self, byte_number):
        return self.memory[byte_number]

    def set_memory(self, byte_number, value):
        self.memory[byte_number] = value

    def check_page(self, address1, address2):
        # If the two address refer to different pages add 1 to the cycle
        if address1 & 0xFF00 != address2 & 0xFF00:
            self.cycles += 1

    def get_operand_address(self, addressing_mode):
        data = self.get_memory(self.program_counter + 1)
        data2 = self.get_memory(self.program_counter + 2)
        if addressing_mode == AddressingModes.IMMEDIATE:
            return self.program_counter + 1
        elif addressing_mode == AddressingModes.ZERO_PAGE:
            return data
        elif addressing_mode == AddressingModes.ZERO_PAGE_X:
            return (data + self.x) % 0xFF
        elif addressing_mode == AddressingModes.ZERO_PAGE_Y:
            return (data + self.x) % 0xFF
        elif addressing_mode == AddressingModes.ABSOLUTE:
            return data * 0xFF + data2
        elif addressing_mode == AddressingModes.ABSOLUTE_X:
            address = data * 0xFF + data2
            result = address + self.x
            self.check_page(address, result)
            return result
        elif addressing_mode == AddressingModes.ABSOLUTE_X_NO_PAGE:
            address = data * 0xFF + data2
            result = address + self.x
            return result
        elif addressing_mode == AddressingModes.ABSOLUTE_Y:
            address = data * 0xFF + data2
            result = address + self.y
            self.check_page(address, result)
            return result
        elif addressing_mode == AddressingModes.INDIRECT_X:
            low_byte = self.get_memory((data + self.x) % 0xFF)
            high_byte = self.get_memory((data + self.x + 1) % 0xFF) * 0xFF
            return low_byte + high_byte
        elif addressing_mode == AddressingModes.INDIRECT_Y:
            low_byte = self.get_memory(data)
            high_byte = self.get_memory((data + 1) % 0xFF) * 0xFF
            address = low_byte + high_byte
            result = address + self.y
            self.check_page(address, result)
            return result
        elif addressing_mode == AddressingModes.RELATIVE:
            offset = data
            if offset >= 0x80:  # Negative
                offset -= 0x100
            return offset
        elif addressing_mode == AddressingModes.IMPLIED:
            return None

    def update_status_registers(self, value):
        if value == 0:
            self.zero = 1
        else:
            self.zero = 0

        if value > 0x80:
            self.negative = 1
        else:
            self.negative = 0

    def branch(self, offset):
        self.cycles += 1
        self.check_page(self.program_counter, self.program_counter + offset)
        self.program_counter += offset

    def push(self, value):
        self.set_memory(self.stack_pointer, value)
        self.stack_pointer -= 1

    def adc(self, operand_address):
        """ Add with Carry """
        value_to_add = self.get_memory(operand_address)
        self.accumulator = self.accumulator + value_to_add + self.carry
        if self.accumulator > 0xFF:
            self.carry = 1
            self.accumulator %= 0xFF
        else:
            self.carry = 0
        self.update_status_registers(self.accumulator)

    def and_(self, operand_address):
        operand = self.get_memory(operand_address)
        self.accumulator &= operand
        self.update_status_registers(self.accumulator)

    def asl(self, operand_address):
        if self.addressing_mode == AddressingModes.ACCUMULATOR:
            self.accumulator *= 2
            if self.accumulator > 0xFF:
                self.carry = 1
                self.accumulator %= 0xFF
            else:
                self.carry = 0
            self.update_status_registers(self.accumulator)
        else:
            value = self.get_memory(operand_address)
            value *= 2
            if value > 0xFF:
                self.carry = 1
                value %= 0xFF
            else:
                self.carry = 0
            self.update_status_registers(value)
            self.set_memory(operand_address, value)

    def bcc(self, offset):
        if self.carry == 0:
            self.branch(offset)

    def bcs(self, offset):
        if self.carry == 1:
            self.branch(offset)

    def beq(self, offset):
        if self.zero == 1:
            self.branch(offset)

    def bit(self, operand_address):
        operand = self.get_memory(operand_address)
        result = self.accumulator & operand
        if result == 0:
            self.zero = 1
        else:
            self.zero = 0

        if operand & 0x40:
            self.overflow = 1
        else:
            self.overflow = 0

        if operand & 0x80:
            self.negative = 1
        else:
            self.negative = 0

    def bmi(self, offset):
        if self.negative == 1:
            self.branch(offset)

    def bne(self, offset):
        if self.zero == 0:
            self.branch(offset)

    def bpl(self, offset):
        if self.negative == 0:
            self.branch(offset)

    def brk(self, _implied):
        self.break_command = 1
        self.push(self.program_counter >> 8)
        self.push(self.program_counter & 0xFF)
        self.push(self.status_register)
        self.program_counter = self.get_memory(0xFFFE) + self.get_memory(0xFFFF) * 0xFF

    def bvc(self, offset):
        if self.overflow == 0:
            self.branch(offset)

    def bvs(self, offset):
        if self.overflow == 1:
            self.branch(offset)

    def clc(self, _implied):
        self.carry = 0

    def cld(self, _implied):
        self.decimal_mode = 0

    def cli(self, _implied):
        self.interrupt_disable = 0

    def clv(self, _implied):
        self.overflow = 0

    def cmp(self, operand_address):
        operand = self.get_memory(operand_address)
        if self.accumulator > operand:
            self.carry = 1
        else:
            self.carry = 0
        result = self.accumulator - operand
        self.update_status_registers(result)

    def cpx(self, operand_address):
        operand = self.get_memory(operand_address)
        if self.x > operand:
            self.carry = 1
        else:
            self.carry = 0
        result = self.x - operand
        self.update_status_registers(result)

    def cpy(self, operand_address):
        operand = self.get_memory(operand_address)
        if self.y > operand:
            self.carry = 1
        else:
            self.carry = 0
        result = self.y - operand
        self.update_status_registers(result)

    def dec(self, operand_address):
        operand = self.get_memory(operand_address)
        result = (operand - 1) % 0xFF
        self.set_memory(operand_address, result)
        self.update_status_registers(result)

    def dex(self, _implied):
        self.x = (self.x - 1) % 0xFF
        self.update_status_registers(self.x)

    def dey(self, _implied):
        self.y = (self.y - 1) % 0xFF
        self.update_status_registers(self.y)

    def eor(self, operand_address):
        operand = self.get_memory(operand_address)
        self.accumulator ^= operand
        self.update_status_registers(self.accumulator)

    def inc(self, operand_address):
        operand = self.get_memory(operand_address)
        result = (operand + 1) % 0xFF
        self.set_memory(operand_address, result)
        self.update_status_registers(result)

    def inx(self, _implied):
        self.x = (self.x + 1) % 0xFF
        self.update_status_registers(self.x)

    def iny(self, _implied):
        self.y = (self.y + 1) % 0xFF
        self.update_status_registers(self.y)

    def jmp(self, operand_address):
        operand = self.get_memory(operand_address)
        # TODO implement the bug with indirect page boundaries
        self.program_counter = operand

    def jsr(self, operand_address):
        # TODO verify that I'm pushing the correct value of program counter
        self.push(self.program_counter - 1)
        self.program_counter = self.get_memory(operand_address)

    def lda(self, operand_address):
        self.accumulator = self.get_memory(operand_address)
        self.update_status_registers(self.accumulator)

    def ldx(self, operand_address):
        self.x = self.get_memory(operand_address)
        self.update_status_registers(self.x)

    def ldy(self, operand_address):
        self.y = self.get_memory(operand_address)
        self.update_status_registers(self.y)





INSTRUCTIONS_MAP = {
    # ADC
    0x69: (CPU.adc, AddressingModes.IMMEDIATE, 2, 2),
    0x65: (CPU.adc, AddressingModes.ZERO_PAGE, 2, 3),
    0x75: (CPU.adc, AddressingModes.ZERO_PAGE_X, 2, 4),
    0x6D: (CPU.adc, AddressingModes.ABSOLUTE, 3, 4),
    0x7D: (CPU.adc, AddressingModes.ABSOLUTE_X, 3, 4),
    0x79: (CPU.adc, AddressingModes.ABSOLUTE_Y, 3, 4),
    0x61: (CPU.adc, AddressingModes.INDIRECT_X, 2, 6),
    0x71: (CPU.adc, AddressingModes.INDIRECT_Y, 2, 5),
    # AND
    0x29: (CPU.and_, AddressingModes.IMMEDIATE, 2, 2),
    0x25: (CPU.and_, AddressingModes.ZERO_PAGE, 2, 3),
    0x35: (CPU.and_, AddressingModes.ZERO_PAGE_X, 2, 4),
    0x2D: (CPU.and_, AddressingModes.ABSOLUTE, 3, 4),
    0x3D: (CPU.and_, AddressingModes.ABSOLUTE_X, 3, 4),
    0x39: (CPU.and_, AddressingModes.ABSOLUTE_Y, 3, 4),
    0x21: (CPU.and_, AddressingModes.INDIRECT_X, 2, 6),
    0x31: (CPU.and_, AddressingModes.INDIRECT_Y, 2, 5),
    # ASL
    0x0A: (CPU.asl, AddressingModes.ACCUMULATOR, 1, 2),
    0x06: (CPU.asl, AddressingModes.ZERO_PAGE, 2, 5),
    0x16: (CPU.asl, AddressingModes.ZERO_PAGE_X, 2, 6),
    0x0E: (CPU.asl, AddressingModes.ABSOLUTE, 3, 6),
    0x1E: (CPU.asl, AddressingModes.ABSOLUTE_X_NO_PAGE, 3, 7),
    # BCC
    0x90: (CPU.bcc, AddressingModes.RELATIVE, 2, 2),
    # BCS
    0xB0: (CPU.bcs, AddressingModes.RELATIVE, 2, 2),
    # BEQ
    0xF0: (CPU.beq, AddressingModes.RELATIVE, 2, 2),
    # BIT
    0x24: (CPU.bit, AddressingModes.ZERO_PAGE, 2, 3),
    0x2C: (CPU.bit, AddressingModes.ABSOLUTE, 3, 4),
    # BMI
    0x30: (CPU.bmi, AddressingModes.RELATIVE, 2, 2),
    # BNE
    0xD0: (CPU.bne, AddressingModes.RELATIVE, 2, 2),
    # BPL
    0x10: (CPU.bpl, AddressingModes.RELATIVE, 2, 2),
    # BRK
    0x00: (CPU.brk, AddressingModes.IMPLIED, 1, 7),
    # BVC
    0x50: (CPU.bvc, AddressingModes.RELATIVE, 2, 2),
    # BVS
    0x70: (CPU.bvs, AddressingModes.RELATIVE, 2, 2),
    # Clear functions
    0x18: (CPU.clc, AddressingModes.IMPLIED, 1, 2),
    0xD8: (CPU.cld, AddressingModes.IMPLIED, 1, 2),
    0x58: (CPU.cli, AddressingModes.IMPLIED, 1, 2),
    0xB8: (CPU.clv, AddressingModes.IMPLIED, 1, 2),
    # CMP
    0xC9: (CPU.cmp, AddressingModes.IMMEDIATE, 2, 2),
    0xC5: (CPU.cmp, AddressingModes.ZERO_PAGE, 2, 3),
    0xD5: (CPU.cmp, AddressingModes.ZERO_PAGE_X, 2, 4),
    0xCD: (CPU.cmp, AddressingModes.ABSOLUTE, 3, 4),
    0xDD: (CPU.cmp, AddressingModes.ABSOLUTE_X, 3, 4),
    0xD9: (CPU.cmp, AddressingModes.ABSOLUTE_Y, 3, 4),
    0xC1: (CPU.cmp, AddressingModes.INDIRECT_X, 2, 6),
    0xD1: (CPU.cmp, AddressingModes.INDIRECT_Y, 2, 5),
    # CPX
    0xE0: (CPU.cpx, AddressingModes.IMMEDIATE, 2, 2),
    0xE4: (CPU.cpx, AddressingModes.ZERO_PAGE, 2, 3),
    0xEC: (CPU.cpx, AddressingModes.ABSOLUTE, 3, 4),
    # CPY
    0xC0: (CPU.cpy, AddressingModes.IMMEDIATE, 2, 2),
    0xC4: (CPU.cpy, AddressingModes.ZERO_PAGE, 2, 3),
    0xCC: (CPU.cpy, AddressingModes.ABSOLUTE, 3, 4),
    # DEC
    0xC6: (CPU.dec, AddressingModes.ZERO_PAGE, 2, 5),
    0xD6: (CPU.dec, AddressingModes.ZERO_PAGE_X, 2, 6),
    0xCE: (CPU.dec, AddressingModes.ABSOLUTE, 3, 6),
    0xDE: (CPU.dec, AddressingModes.ABSOLUTE_X_NO_PAGE, 3, 7),
    # DEX
    0xCA: (CPU.dex, AddressingModes.IMPLIED, 1, 2),
    # DEY
    0x88: (CPU.dey, AddressingModes.IMPLIED, 1, 2),


}

if __name__ == '__main__':
    cpu = CPU()
    # ADD 0x1F
    cpu.memory[0x34] = 0x69
    cpu.memory[0x35] = 0x1F
    # AND 0xF1
    cpu.memory[0x36] = 0x29
    cpu.memory[0x37] = 0xF1
    cpu.tick()
    cpu.tick()
    assert cpu.accumulator == 0x1F
    cpu.tick()
    cpu.tick()
    assert cpu.accumulator == 0x11
