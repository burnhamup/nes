from cpu import CPU
from memory import Memory
from rom import Rom


def main():
    rom = Rom('nestest.nes')
    memory = Memory(rom)
    cpu = CPU(memory)
    cpu.program_counter = 0xC000
    cpu.interrupt_disable = 1
    with open('nestest.log') as expected_output_file:
        for debug_args in cpu.tick_debug():
            print "{:X} {:02X} {} {} {} {:04X} \t\tA:{:02X} X:{:02X} Y:{:02X} P:{:02X} SP:{:02X} CYC:{:3d} SL:{:3d}".format(*debug_args)
            expected_output = expected_output_file.readline()
            expected_program_counter = int(expected_output[0:4], 16)
            expected_opcode = int(expected_output[6:8], 16)
            expected_operand = expected_output[9:11]
            expected_operand2 = expected_output[12:14]
            expected_function = expected_output[16:19]
            expected_a = int(expected_output[50:52], 16)
            expected_x = int(expected_output[55:57], 16)
            expected_y = int(expected_output[60:62], 16)
            expected_status_registers = int(expected_output[65:67], 16)
            expected_stack_pointer = int(expected_output[71:73], 16)
            expected_cycles = int(expected_output[78:81])
            assert debug_args[0] == expected_program_counter
            assert debug_args[1] == expected_opcode
            assert debug_args[2] == expected_operand
            assert debug_args[3] == expected_operand2
            assert debug_args[4] == expected_function
            assert debug_args[6] == expected_a
            assert debug_args[7] == expected_x
            assert debug_args[8] == expected_y
            assert debug_args[9] == expected_status_registers
            assert debug_args[10] == expected_stack_pointer
            assert debug_args[11] == expected_cycles
            if debug_args[11] == 188 and debug_args[12] == 212:
                break

if __name__ == '__main__':
    main()