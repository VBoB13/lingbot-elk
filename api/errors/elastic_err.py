# Defines helpful Exception classes that will clarify certain errors
# within the < es.elastic > module

class ElasticError(Exception):
    def __init__(self, msg, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.msg = msg if msg else ""

    def __str__(self):
        return "{}: {}".format(self.__class__.__name__, self.msg)
