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
    INDIRECT = 13


class CPU(object):
    def __init__(self, memory):
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
        self.memory = memory

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

    def tick_debug(self):
        self.total_cycles = 0
        while True:
            if self.cycles > 0:
                self.tick()
            else:
                yield self.debug_message()
                self.tick()
                self.total_cycles += self.cycles + 1

    def debug_message(self):
        op_code = self.get_memory(self.program_counter)
        command, addressing_mode, number_of_bytes, cycles = INSTRUCTIONS_MAP[op_code]
        operand = self.get_operand_address(addressing_mode)
        data1 = "{:02X}".format(self.get_memory(self.program_counter + 1)) if number_of_bytes > 1 else "  "
        data2 = "{:02X}".format(self.get_memory(self.program_counter + 2)) if number_of_bytes > 2 else "  "
        args = (
            self.program_counter,
            op_code,
            data1,
            data2,
            command.__name__.upper() if command.__name__ != 'and_' else 'AND',
            operand,
            self.accumulator,
            self.x,
            self.y,
            self.status_register,
            self.stack_pointer,
            (self.total_cycles * 3) % 341,
            (((self.total_cycles * 3) / 341) + 242) % 261 - 1
        )
        return args

    def get_memory(self, byte_number):
        return self.memory.get_memory(byte_number)

    def set_memory(self, byte_number, value):
        self.memory.set_memory(byte_number, value)

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
            return (data + self.x) % 0x100
        elif addressing_mode == AddressingModes.ZERO_PAGE_Y:
            return (data + self.x) % 0x100
        elif addressing_mode == AddressingModes.ABSOLUTE:
            return data + data2 * 0x100
        elif addressing_mode == AddressingModes.ABSOLUTE_X:
            address = data * 0x100 + data2
            result = address + self.x
            self.check_page(address, result)
            return result
        elif addressing_mode == AddressingModes.ABSOLUTE_X_NO_PAGE:
            address = data2 * 0x100 + data
            result = address + self.x
            return result
        elif addressing_mode == AddressingModes.ABSOLUTE_Y:
            address = data2 * 0x100 + data
            result = address + self.y
            self.check_page(address, result)
            return result
        elif addressing_mode == AddressingModes.INDIRECT_X:
            low_byte = self.get_memory((data + self.x) % 0xFF)
            high_byte = self.get_memory((data + self.x + 1) % 0xFF) * 0x100
            return low_byte + high_byte
        elif addressing_mode == AddressingModes.INDIRECT_Y:
            low_byte = self.get_memory(data)
            high_byte = self.get_memory((data + 1) % 0xFF) * 0x100
            address = low_byte + high_byte
            result = address + self.y
            self.check_page(address, result)
            return result
        elif addressing_mode == AddressingModes.RELATIVE:
            offset = data
            if offset >= 0x80:  # Negative
                offset -= 0x100
            return offset
        elif addressing_mode == AddressingModes.INDIRECT:
            address = data * 0x100 + data2
            low_byte = self.get_memory(address)
            if data & 0xFF == 0xFF:
                high_address = address | 0xFF00
            else:
                high_address = address + 1
            high_byte = self.get_memory(high_address) * 0x100
            return low_byte + high_byte

        elif addressing_mode == AddressingModes.IMPLIED:
            return None

    def update_status_registers(self, value):
        if value == 0:
            self.zero = 1
        else:
            self.zero = 0

        if value >= 0x80 or value < 0:
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

    def pop(self):
        self.stack_pointer += 1
        return self.get_memory(self.stack_pointer)

    def adc(self, operand_address):
        """ Add with Carry """
        value_to_add = self.get_memory(operand_address)
        result = self.accumulator + value_to_add + self.carry
        if result > 0xFF:
            self.carry = 1
        else:
            self.carry = 0

        if (self.accumulator ^ result) & (value_to_add ^ result) & 0x80:
            self.overflow = 1
        else:
            self.overflow = 0

        self.accumulator = result % 0x100


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
                self.accumulator %= 0x100
            else:
                self.carry = 0
            self.update_status_registers(self.accumulator)
        else:
            value = self.get_memory(operand_address)
            value *= 2
            if value > 0xFF:
                self.carry = 1
                value %= 0x100
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
        self.push(self.status_register | 0x10)
        self.program_counter = self.get_memory(0xFFFE) + self.get_memory(0xFFFF) * 0x100

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
        if self.accumulator >= operand:
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
        result = (operand - 1) % 0x100
        self.set_memory(operand_address, result)
        self.update_status_registers(result)

    def dex(self, _implied):
        self.x = (self.x - 1) % 0x100
        self.update_status_registers(self.x)

    def dey(self, _implied):
        self.y = (self.y - 1) % 0x100
        self.update_status_registers(self.y)

    def eor(self, operand_address):
        operand = self.get_memory(operand_address)
        self.accumulator ^= operand
        self.update_status_registers(self.accumulator)

    def inc(self, operand_address):
        operand = self.get_memory(operand_address)
        result = (operand + 1) % 0x100
        self.set_memory(operand_address, result)
        self.update_status_registers(result)

    def inx(self, _implied):
        self.x = (self.x + 1) % 0x100
        self.update_status_registers(self.x)

    def iny(self, _implied):
        self.y = (self.y + 1) % 0x100
        self.update_status_registers(self.y)

    def jmp(self, operand_address):
        self.program_counter = operand_address

    def jsr(self, operand_address):
        value_to_push = self.program_counter - 1
        self.push(value_to_push >> 8)
        self.push(value_to_push & 0xFF)
        self.program_counter = operand_address

    def lda(self, operand_address):
        self.accumulator = self.get_memory(operand_address)
        self.update_status_registers(self.accumulator)

    def ldx(self, operand_address):
        self.x = self.get_memory(operand_address)
        self.update_status_registers(self.x)

    def ldy(self, operand_address):
        self.y = self.get_memory(operand_address)
        self.update_status_registers(self.y)

    def lsr(self, operand_address):
        if self.addressing_mode == AddressingModes.ACCUMULATOR:
            original_value = self.accumulator
            self.accumulator = (self.accumulator >> 1)
            self.update_status_registers(self.accumulator)
        else:
            original_value = self.get_memory(operand_address)
            new_value = (original_value >> 1)
            self.update_status_registers(new_value)
            self.set_memory(operand_address, new_value)
        self.carry = original_value & 0x01

    def nop(self, _implied):
        pass

    def ora(self, operand_address):
        operand = self.get_memory(operand_address)
        self.accumulator |= operand
        self.update_status_registers(self.accumulator)

    def pha(self, _implied):
        self.push(self.accumulator)

    def php(self, _implied):
        self.push(self.status_register | 0x10)

    def pla(self, _implied):
        self.accumulator = self.pop()
        self.update_status_registers(self.accumulator)

    def plp(self, _implied):
        status_registers = self.pop()
        if status_registers & 0x1:
            self.carry = 1
        else:
            self.carry = 0
        self.carry = 1 if status_registers & 0x1 else 0
        self.zero = 1 if status_registers & 0x2 else 0
        self.interrupt_disable = 1 if status_registers & 0x4 else 0
        self.decimal_mode = 1 if status_registers & 0x8 else 0
        self.overflow = 1 if status_registers & 0x40 else 0
        self.negative = 1 if status_registers & 0x80 else 0

    def rol(self, operand_address):
        if self.addressing_mode == AddressingModes.ACCUMULATOR:
            original_value = self.accumulator
            self.accumulator = (self.accumulator << 1) + self.carry
            self.update_status_registers(self.accumulator)
        else:
            original_value = self.get_memory(operand_address)
            new_value = (original_value << 1) + self.carry
            self.update_status_registers(new_value)
            self.set_memory(operand_address, new_value)
        self.carry = original_value & 0x80

    def ror(self, operand_address):
        if self.addressing_mode == AddressingModes.ACCUMULATOR:
            original_value = self.accumulator
            self.accumulator = (self.accumulator >> 1) + self.carry * 0x80
            self.update_status_registers(self.accumulator)
        else:
            original_value = self.get_memory(operand_address)
            new_value = (original_value >> 1) + self.carry * 0x80
            self.update_status_registers(new_value)
            self.set_memory(operand_address, new_value)
        self.carry = original_value & 0x01

    def rti(self, _implied):
        self.plp(_implied)
        self.program_counter = self.pop() + self.pop() * 0x100

    def rts(self, _implied):
        self.program_counter = self.pop() + self.pop() * 0x100 + 1

    def sbc(self, operand_address):
        operand = self.get_memory(operand_address)
        result = self.accumulator - operand - (1 - self.carry)
        if result >= 0:
            self.carry = 1
        else:
            self.carry = 0
        if (self.accumulator ^ result) & (operand ^ result) & 0x80:
            self.overflow = 1
        else:
            self.overflow = 0
        self.accumulator = result % 0x100

        self.update_status_registers(self.accumulator)

    def sec(self, _implied):
        self.carry = 1

    def sed(self, _implied):
        self.decimal_mode = 1

    def sei(self, _implied):
        self.interrupt_disable = 1

    def sta(self, operand_address):
        self.set_memory(operand_address, self.accumulator)

    def stx(self, operand_address):
        self.set_memory(operand_address, self.x)

    def sty(self, operand_address):
        self.set_memory(operand_address, self.y)

    def tax(self, _implied):
        self.x = self.accumulator
        self.update_status_registers(self.x)

    def tay(self, _implied):
        self.y = self.accumulator
        self.update_status_registers(self.y)

    def tsx(self, _implied):
        self.x = self.stack_pointer
        self.update_status_registers(self.x)

    def txa(self, _implied):
        self.accumulator = self.x
        self.update_status_registers(self.accumulator)

    def txs(self, _implied):
        self.stack_pointer = self.x

    def tya(self, _implied):
        self.accumulator = self.y
        self.update_status_registers(self.accumulator)


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
    # EOR
    0x49: (CPU.eor, AddressingModes.IMMEDIATE, 2, 2),
    0x45: (CPU.eor, AddressingModes.ZERO_PAGE, 2, 3),
    0x55: (CPU.eor, AddressingModes.ZERO_PAGE_X, 2, 4),
    0x4D: (CPU.eor, AddressingModes.ABSOLUTE, 3, 4),
    0x5D: (CPU.eor, AddressingModes.ABSOLUTE_X, 3, 4),
    0x59: (CPU.eor, AddressingModes.ABSOLUTE_Y, 3, 4),
    0x41: (CPU.eor, AddressingModes.INDIRECT_X, 2, 6),
    0x51: (CPU.eor, AddressingModes.INDIRECT_Y, 2, 5),
    # INC
    0xE6: (CPU.inc, AddressingModes.ZERO_PAGE, 2, 5),
    0xF6: (CPU.inc, AddressingModes.ZERO_PAGE_X, 2, 6),
    0xEE: (CPU.inc, AddressingModes.ABSOLUTE, 3, 6),
    0xFE: (CPU.inc, AddressingModes.ABSOLUTE_X_NO_PAGE, 3, 7),
    # INX
    0xE8: (CPU.inx, AddressingModes.IMPLIED, 1, 2),
    # INY
    0xC8: (CPU.iny, AddressingModes.IMPLIED, 1, 2),
    # JMP
    0x4C: (CPU.jmp, AddressingModes.ABSOLUTE, 3, 3),
    0x6C: (CPU.jmp, AddressingModes.INDIRECT, 3, 5),
    # JSR
    0x20: (CPU.jsr, AddressingModes.ABSOLUTE, 3, 6),
    # LDA
    0xA9: (CPU.lda, AddressingModes.IMMEDIATE, 2, 2),
    0xA5: (CPU.lda, AddressingModes.ZERO_PAGE, 2, 3),
    0xB5: (CPU.lda, AddressingModes.ZERO_PAGE_X, 2, 4),
    0xAD: (CPU.lda, AddressingModes.ABSOLUTE, 3, 4),
    0xBD: (CPU.lda, AddressingModes.ABSOLUTE_X, 3, 4),
    0xB9: (CPU.lda, AddressingModes.ABSOLUTE_Y, 3, 4),
    0xA1: (CPU.lda, AddressingModes.INDIRECT_X, 2, 6),
    0xB1: (CPU.lda, AddressingModes.INDIRECT_Y, 2, 5),
    # LDX
    0xA2: (CPU.ldx, AddressingModes.IMMEDIATE, 2, 2),
    0xA6: (CPU.ldx, AddressingModes.ZERO_PAGE, 2, 2,),
    0xB6: (CPU.ldx, AddressingModes.ZERO_PAGE_Y, 2, 3),
    0xAE: (CPU.ldx, AddressingModes.ABSOLUTE, 3, 4),
    0xBE: (CPU.ldx, AddressingModes.ABSOLUTE_Y, 3, 4),
    # LDY
    0xA0: (CPU.ldy, AddressingModes.IMMEDIATE, 2, 2),
    0xA4: (CPU.ldy, AddressingModes.ZERO_PAGE, 2, 2,),
    0xB4: (CPU.ldy, AddressingModes.ZERO_PAGE_X, 2, 3),
    0xAC: (CPU.ldy, AddressingModes.ABSOLUTE, 3, 4),
    0xBC: (CPU.ldy, AddressingModes.ABSOLUTE_X, 3, 4),
    # LSR
    0x4A: (CPU.lsr, AddressingModes.ACCUMULATOR, 1, 2),
    0x46: (CPU.lsr, AddressingModes.ZERO_PAGE, 2, 5),
    0x56: (CPU.lsr, AddressingModes.ZERO_PAGE_X, 2, 6),
    0x4E: (CPU.lsr, AddressingModes.ABSOLUTE, 3, 6),
    0x5E: (CPU.lsr, AddressingModes.ABSOLUTE_X_NO_PAGE, 3, 7),
    # NOP
    0xEA: (CPU.nop, AddressingModes.IMPLIED, 1, 2),
    # ORA
    0x09: (CPU.ora, AddressingModes.IMMEDIATE, 2, 2),
    0x05: (CPU.ora, AddressingModes.ZERO_PAGE, 2, 3),
    0x15: (CPU.ora, AddressingModes.ZERO_PAGE_X, 2, 4),
    0x0D: (CPU.ora, AddressingModes.ABSOLUTE, 3, 4),
    0x1D: (CPU.ora, AddressingModes.ABSOLUTE_X, 3, 4),
    0x19: (CPU.ora, AddressingModes.ABSOLUTE_Y, 3, 4),
    0x01: (CPU.ora, AddressingModes.INDIRECT_X, 2, 6),
    0x11: (CPU.ora, AddressingModes.INDIRECT_Y, 2, 5),
    # PHA
    0x48: (CPU.pha, AddressingModes.IMPLIED, 1, 3),
    # PHP
    0x08: (CPU.php, AddressingModes.IMPLIED, 1, 3),
    # PLA
    0x68: (CPU.pla, AddressingModes.IMPLIED, 1, 4),
    # PLP
    0x28: (CPU.plp, AddressingModes.IMPLIED, 1, 4),
    # ROL
    0x2A: (CPU.rol, AddressingModes.ACCUMULATOR, 1, 2),
    0x26: (CPU.rol, AddressingModes.ZERO_PAGE, 2, 5),
    0x36: (CPU.rol, AddressingModes.ZERO_PAGE_X, 2, 6),
    0x2E: (CPU.rol, AddressingModes.ABSOLUTE, 3, 6),
    0x3E: (CPU.rol, AddressingModes.ABSOLUTE_X_NO_PAGE, 3, 7),
    # ROL
    0x6A: (CPU.ror, AddressingModes.ACCUMULATOR, 1, 2),
    0x66: (CPU.ror, AddressingModes.ZERO_PAGE, 2, 5),
    0x76: (CPU.ror, AddressingModes.ZERO_PAGE_X, 2, 6),
    0x6E: (CPU.ror, AddressingModes.ABSOLUTE, 3, 6),
    0x7E: (CPU.ror, AddressingModes.ABSOLUTE_X_NO_PAGE, 3, 7),
    # RTI
    0x40: (CPU.rti, AddressingModes.IMPLIED, 1, 6),
    # RTS
    0x60: (CPU.rts, AddressingModes.IMPLIED, 1, 6),
    # SBC
    0xE9: (CPU.sbc, AddressingModes.IMMEDIATE, 2, 2),
    0xE5: (CPU.sbc, AddressingModes.ZERO_PAGE, 2, 3),
    0xF5: (CPU.sbc, AddressingModes.ZERO_PAGE_X, 2, 4),
    0xED: (CPU.sbc, AddressingModes.ABSOLUTE, 3, 4),
    0xFD: (CPU.sbc, AddressingModes.ABSOLUTE_X, 3, 4),
    0xF9: (CPU.sbc, AddressingModes.ABSOLUTE_Y, 3, 4),
    0xE1: (CPU.sbc, AddressingModes.INDIRECT_X, 2, 6),
    0xF1: (CPU.sbc, AddressingModes.INDIRECT_Y, 2, 5),
    # SEC
    0x38: (CPU.sec, AddressingModes.IMPLIED, 1, 2),
    # SED
    0xF8: (CPU.sed, AddressingModes.IMPLIED, 1, 2),
    # SEI
    0x78: (CPU.sei, AddressingModes.IMPLIED, 1, 2),
    # STA
    0x85: (CPU.sta, AddressingModes.ZERO_PAGE, 2, 3),
    0x95: (CPU.sta, AddressingModes.ZERO_PAGE_X, 2, 4),
    0x8D: (CPU.sta, AddressingModes.ABSOLUTE, 3, 4),
    0x9D: (CPU.sta, AddressingModes.ABSOLUTE_X, 3, 5),
    0x99: (CPU.sta, AddressingModes.ABSOLUTE_Y, 3, 5),
    0x81: (CPU.sta, AddressingModes.INDIRECT_X, 2, 6),
    0x91: (CPU.sta, AddressingModes.INDIRECT_Y, 2, 5),
    # STX
    0x86: (CPU.stx, AddressingModes.ZERO_PAGE, 2, 3),
    0x96: (CPU.stx, AddressingModes.ZERO_PAGE_Y, 2, 4),
    0x8E: (CPU.stx, AddressingModes.ABSOLUTE, 3, 4),
    # STX
    0x84: (CPU.sty, AddressingModes.ZERO_PAGE, 2, 3),
    0x94: (CPU.sty, AddressingModes.ZERO_PAGE_Y, 2, 4),
    0x8C: (CPU.sty, AddressingModes.ABSOLUTE, 3, 4),
    # TAX
    0xAA: (CPU.tax, AddressingModes.IMPLIED, 1, 2),
    # TAY
    0xA8: (CPU.tay, AddressingModes.IMPLIED, 1, 2),
    # TSX
    0xBA: (CPU.tsx, AddressingModes.IMPLIED, 1, 2),
    # TXA
    0x8A: (CPU.txa, AddressingModes.IMPLIED, 1, 2),
    # TXS
    0x9A: (CPU.txs, AddressingModes.IMPLIED, 1, 2),
    # TYA
    0x98: (CPU.tya, AddressingModes.IMPLIED, 1, 2),
}