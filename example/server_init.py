import sys
import logging

sys.path.insert(0, '..')

log = logging.getLogger('abchat')
handler = logging.StreamHandler()
handler.setLevel(logging.NOTSET)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
log.addHandler(handler)
