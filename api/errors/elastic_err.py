# Defines helpful Exception classes that will clarify certain errors
# within the < es.elastic > module

class ElasticError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(args)
        msg = kwargs.get("msg", None)
        if msg:
            self.msg = msg

    def __str__(self):
        return "{}: {}".format(self.__class__.__name__, self.msg)
