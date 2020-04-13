import logging as _logging

logger = _logging.getLogger(__name__)
logger.setLevel(_logging.DEBUG)
logger.addHandler(_logging.NullHandler())
