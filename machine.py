# -*- coding: utf-8 -*-
# Mockup class for machine Pin

class Pin:
    ID_TYPE = 0

    def __init__(self, id):
        self._port = None
        self._pin = None
        if self.ID_TYPE == 0:
            raise NotImplementedError
        elif self.ID_TYPE == 1 and isinstance(id, int):
            self._pin = id
        elif self.ID_TYPE == 2 and isinstance(id, str):
            self._pin = id
        elif self.ID_TYPE == 3 and isinstance(id, tuple) and\
                isinstance(id[0], str) and isinstance(id[1], int):
            self._port = id[0]
            self._pin = id[1]
        else:
            raise TypeError

    def __eq__(self, other):
        return self._port == other._port and\
               self._pin == other._pin

    def name(self):
        return self._pin

    def port(self):
        return self._port

    def pin(self):
        return self._pin
