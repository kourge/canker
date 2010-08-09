#!/usr/bin/python

from datetime import datetime

class Key(object):
    class InvalidKeyLengthError(Exception):
        pass

    class OctetOutOfRangeError(Exception):
        pass

    BUILDINGS = [
        None, 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'K', 'L', 'M', 'N',
        'P', 'R', 'S'
    ]

    def __init__(self, created, building, room, id=0x54071030, key=None):
        if not isinstance(created, datetime):
            raise ValueError("'created' should be a datetime")

        if not building in self.BUILDINGS:
            raise IndexError("'building' is invalid")

        if int(room, 16) > 0xFFF:
            raise ValueError("'room' is invalid")

        if id > 0xFFFFFFFF:
            raise ValueError("'id' is invalid")

        self.created = created
        self.building = building
        self.room = room
        self.id = id
        self.key = self.dump() if key is None else key

    def is_valid(self):
        checksum = self.key[11]
        return reduce(lambda x, y: x ^ y, self.key[0:11]) == checksum

    def dump(self):
        ops = ((0xFF000000, 24), (0xFF0000, 16), (0xFF00, 8), (0xFF, 0))
        id = [(self.id & mask) >> shift for mask, shift in ops]

        c = self.created
        y, m, d, h, n, s = c.year, c.month, c.day, c.hour, c.minute, c.second
        p = 1 if c.hour > 12 else 0
        h -= (12 * p)
        y -= 2000
        timestamp = (y << 28) + (m << 24) + (d << 18) + (h << 13) + (n << 7) + \
                    (s << 1) + p
        created = [(timestamp & mask) >> shift for mask, shift in ops]

        building = self.BUILDINGS.index(self.building) << 12
        room = int(self.room, 16)
        location = building + room
        ops = ((0xFF0000, 16), (0xFF00, 8), (0xFF, 0))
        location = [(location & mask) >> shift for mask, shift in ops]

        run = id + created + location
        checksum = reduce(lambda x, y: x ^ y, run)
        return run + [checksum] + ([0] * 4)

    def dump_readable(self):
        return ' '.join(['%02X' % n for n in self.dump()])

    def dump_stream(self):
        return ''.join([chr(n) for n in self.dump()])

    def __repr__(self):
        info = {
            'class': self.__class__.__name__,
            'id': '0x%08X' % self.id,
            'created': self.created,
            'building': self.building,
            'room': self.room
        }
        return '%(class)s(id=%(id)s, created=%(created)r, building=%(building)r, room=%(room)r)' % info

    def __eq__(self, other):
        return self.key == other.key

    @classmethod
    def parse(cls, key):
        if not len(key) == 16:
            raise cls.InvalidKeyLengthError()

        if not all([n >= 0 and n < 256 for n in key]):
            raise cls.OctetOutOfRangeError()

        id = sum([byte << n for byte, n in zip(key[0:4], (24, 16, 8, 0))])

        timestamp = sum([c << n for c, n in zip(key[4:8], (24, 16, 8, 0))])
        yearmonth = timestamp >> 24
        year = (yearmonth >> 4) + 2000
        month = yearmonth & 0xF
        d = (timestamp & 0b011111000000000000000000) >> 18
        h = (timestamp & 0b000000111110000000000000) >> 13
        n = (timestamp & 0b000000000001111110000000) >> 7
        s = (timestamp & 0b000000000000000001111110) >> 1
        p = timestamp & 1
        if p:
            h += 12
        created = datetime(year, month, d, h, n, s)

        location = sum([byte << n for byte, n in zip(key[8:11], (16, 8, 0))])
        building = cls.BUILDINGS[location >> 12]
        room = '%x' % (location & 0xFFF)

        return cls(id=id, created=created, building=building, room=room, key=key)


    @classmethod
    def parse_readable(cls, readable):
        if not isinstance(readable, str):
            raise ValueError("'readable' should be a string")

        return cls.parse([int(n, 16) for n in readable.strip().split(' ')])

    @classmethod
    def parse_stream(cls, stream):
        if not isinstance(stream, str):
            raise ValueError("'readable' should be a string")

        return cls.parse([ord(c) for c in stream])

    @classmethod
    def parse_file(cls, file):
        data = file.read(16)
        file.close()
        return cls.parse_stream(data)

