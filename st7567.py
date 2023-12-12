
from framebuf import FrameBuffer, MONO_VLSB
from micropython import const
from time import sleep_ms

DEFAULT_I2C_ADDR = const(0x3f)

COMMAND__DISPLAY_ON = const(0xaf)
COMMAND__DISPLAY_OFF = const(0xae)
COMMAND__RESET = const(0xe2)
COMMAND__BIAS_0 = const(0xa2)
COMMAND__ALL_PIXEL_ON_NORMAL = const(0xa0)
COMMAND__COM_DIRECTION_NORMAL = const(0xc8)
COMMAND__READ_MODIFY_WRITE = const(0xe0)
COMMAND__END = const(0xee)


class ST7567_I2C:
    def __init__(self, i2c, address=DEFAULT_I2C_ADDR):
        self._address = address
        self._i2c = i2c

    def _write(self, data):
        return self._i2c.writeto(self._address, data)

    def write_command(self, command_byte):
        self._write(bytes([0x00]) + command_byte)

    def write_data(self, data_byte):
        self._write(bytes([0x40]) + data_byte)

    def clear(self, invert=False):
        for x in range(8):
            self.write_command(bytes([0xb0 + x]))

            self.write_command(bytes([0x10]))
            self.write_command(bytes([0x00]))

            for _ in range(128):
                if invert:
                    self.write_data(bytes([0xff]))
                else:
                    self.write_data(bytes([0x00]))

    def init(self, invert=False):
        self.write_command(bytes([COMMAND__RESET]))

        sleep_ms(10)

        self.write_command(bytes([COMMAND__BIAS_0]))

        self.write_command(bytes([COMMAND__ALL_PIXEL_ON_NORMAL]))
        self.write_command(bytes([COMMAND__COM_DIRECTION_NORMAL]))

        # Adjust Display Brightness
        self.write_command(bytes([0x25]))
        self.write_command(bytes([0x81]))
        self.write_command(bytes([0x20]))

        # Internal Power Supply Control
        self.write_command(bytes([0x2c]))
        self.write_command(bytes([0x2e]))
        self.write_command(bytes([0x2f]))

        self.clear(invert)

        self.write_command(bytes([0xaf]))
        self.write_command(bytes([0x40]))

    def write_pixel(self, x, y):
        self.write_command(bytes([0xb0 + y//8]))
        self.write_command(bytes([0x10 + x//16]))
        self.write_command(bytes([x%16]))

        self.write_command(bytes([COMMAND__READ_MODIFY_WRITE]))

        data = b""

        for _ in range(2):
            data = self._i2c.readfrom(self._address, 2)
            if len(data) > 1:
                data = data[-1]

        data = int(data) | (1<<(y%8))
        self.write_data(bytes([data]))
        self.write_command(bytes([COMMAND__END]))

    def write_buffer(self, buffer):
        self.write_command(bytes([0x40 | 0x00]))
        for pagcnt in range(8):
            self.write_command(bytes([0xb0|pagcnt, 0x10 | 0x00, 0x00]))
            self.write_data(buffer[(128*pagcnt):(128*pagcnt+128)])


class ST7567_I2C_FB(FrameBuffer):
    def __init__(self, i2c, address=DEFAULT_I2C_ADDR):
        self._display = ST7567_I2C(i2c, address)
        self._buffer = bytearray(128*64//8)
        super().__init__(self._buffer, 128, 64, MONO_VLSB)

    def init(self, invert=False):
        self.fill(int(invert))
        self._display.init(invert)

    def clear(self, invert=False):
        self.fill(int(invert))
        self._display.clear(invert)

    def show(self):
        self._display.write_buffer(self._buffer)
