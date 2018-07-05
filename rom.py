class Rom(object):
    def __init__(self, file_name):
        self.file_handle = open(file_name, 'rb')
        self.read_header()

    def read_header(self):
        header = self.file_handle.read(3)
        print header
        assert header == 'NES'
        self.file_handle.read(1) # EOF byte
        self.prg_size = ord(self.file_handle.read(1))
        self.chr_size = ord(self.file_handle.read(1))
        self.flags6 = ord((self.file_handle.read(1)))
        self.flags7 = ord((self.file_handle.read(1)))
        print self.prg_size
        print self.chr_size

    def get_address(self, address):
        if address >= 0x8000:
            if self.prg_size == 1 and address >= 0xC000:
                address -= 0x4000
            self.file_handle.seek(0x10 + address - 0x8000, 0)
            return ord(self.file_handle.read(1))

    def set_address(self, address, value):
        raise Exception("I can't write to this!")
