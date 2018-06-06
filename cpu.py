class AddressingModes(object):
	IMMEDIATE = 1
	ZERO_PAGE = 2
	ZERO_PAGE_X = 3
	ZERO_PAGE_Y = 4
	ABSOLUTE = 5
	ABSOLUTE_X = 6
	ABSOLUTE_Y = 7
	INDIRECT_X = 8
	INDIRECT_Y = 9
	ACCUMULATOR = 10
	RELATIVE = 11


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
		# Memory
		self.memory = [0] * 0x800
		
		self.cycles = 0
		
	def tick(self):
		if self.cycles > 0:
			self.cycles -= 1
			return
		op_code = self.get_memory(self.program_counter)
		command, addressing_mode, bytes, cycles = INSTRUCTIONS_MAP[op_code]
		operand = get_operand_address(addressing_mode)
		self.program_counter += bytes
		command(self, addressing_mode, operand))
		self.cycles += cycles - 1
		
		
	def execute(self):
		# Get the instruction from the program counter
		line = self.memory[self.program_counter]
		
	def get_memory(self, byte_number):
		return self.memory[byte_number]
		
			
	def set_memory(self, byte_number, value):
		self.memory[byte_number] = value
		
	
	def checkPage(self, address1, address2):
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
			self.checkPage(address, result)
			return result
		elif addressing_mode == AddressingModes.ABSOLUTE_Y:
			address = data * 0xFF + data2
			result = address + self.y
			self.checkPage(address, result)
			return result
		elif addressing_mode == AddressingModes.INDIRECT_X:
			low_byte = self.get_memory((data + self.x) % 0xFF)
			high_byte = self.get_memory((data + self.x +1) % 0xFF) * 0xFF
			return low_byte + high_byte
		elif addressing_mode == AddressingModes.INDIRECT_Y:
			low_byte = self.get_memory(data)
			high_byte = self.get_memory((data + 1) % 0xFF) * 0xFF
			address = low_byte + high_byte
			result = address + self.y
			self.checkPage(address, result)
			return result
		elif addressing_mode == AddressingModes.RELATIVE:
			offset = data
			if offset >= 0x80: # Negative
				offset -= 0x100
			return offset
			
	def updateStatusRegister(self, value):
		if value == 0:
			self.zero = 1
		else:
			self.zero = 0
		
		if value > 0x80:
			self.negative = 1
		else:
			self.negative = 0
			
	def adc(self, address_mode, operand_address):
		""" Add with Carry """
		value_to_add = self.get_memory(operand_address)
		self.accumulator = self.accumulator + value_to_add + self.carry
		if self.accumulator > 0xFF:
			self.carry = 1
			self.accumulator = self.accumulator % 0xFF
		else:
			self.carry = 0
		self.updateStatusRegister(self.accumulator)
		
	def and_(self, address_mode, operand_address):
		operand = self.get_memory(operand_address)
		self.accumulator = self.accumulator & operand
		self.updateStatusRegister(self.accumulator)
		
	def asl(self, address_mode, operand_address):
		if addressing_mode == AddressingModes.ACCUMULATOR:
			self.accumulator *= 2
			if self.accumulator > 0xFF:
				self.carry = 1
				self.accumulator = self.accumulator % 0xFF
			else:
				self.carry = 0
			self.updateStatusRegister(self.accumulator)
		else:
			value = self.get_memory(operand_address))
			value *= 2
			if value > 0xFF:
				self.carry = 1
				value = value % 0xFF
			else:
				self.carry = 0
			self.updateStatusRegister(value)
			self.set_memory(operand_address, value)
			
	def bcc(self, address_mode, offset):
		if self.c == 0:
			self.cycles += 1
			self.checkPage(self.program_counter, self.program_counter+offset)
			self.program_counter += offset
	
	def bcs(self, address_mode, offset):
		if self.c == 1:
			self.cycles += 1
			self.checkPage(self.program_counter, self.program_counter+offset)
			self.program_counter += offset
			
	def beq(self, address_mode, offset):
		if self.z == 1:
			self.cycles += 1
			self.checkPage(self.program_counter, self.program_counter+offset)
			self.program_counter += offset
			
	def bit(self, address_mode, operand_address):
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
	0x1E: (CPU.asl, AddressingModes.ABSOLUTE_X, 3, 7),
	# BCC
	0x90: (CPU.bcc, AddressingModes.RELATIVE, 2, 2),
	# BCS
	0xB0: (CPU.bcs, AddressingModes.RELATIVE, 2, 2),
	# BEQ
	0xB0: (CPU.beq, AddressingModes.RELATIVE, 2, 2),
	# BIT
	0x24: (CPU.bit, AddressingModes.ZERO_PAGE, 2, 3),
	0x2C: (CPU.bit, AddressingModes.ABSOLUTE, 3, 4),
	
	
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

		
		
		
	