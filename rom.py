class Rom(object):
    def __init__(self, file_name):
        self.file_handle = open(file_name, 'rb')
        self.read_header()

    def read_header(self):
        header = self.file_handle.read(3)
        print header
        assert header == 'NES'
        self.prg_size = self.file_handle.read(1)
        self.chr_size = self.file_handle.read(1)

    def get_address(self, address):
        self.file_handle.seek(address + 0x10 - 0x7FE0, 0)
        return ord(self.file_handle.read(1))

    def set_address(self, address, value):
        raise Exception("I can't write to this!")
