import os

from golem_sci.chains import RINKEBY as _RINKEBY
from .base import *  # noqa # pylint: disable=unused-import

# ETH

ETHEREUM_NODE_LIST = [
    'https://rinkeby.golem.network:55555',
    'http://188.165.227.180:55555',
    'http://94.23.17.170:55555',
    'http://94.23.57.58:55555',
]

ETHEREUM_CHAIN = _RINKEBY
ETHEREUM_FAUCET_ENABLED = True

# P2P

P2P_SEEDS = [
    ('94.23.57.58', 40102),
    ('94.23.57.58', 40104),
    ('94.23.196.166', 40102),
    ('94.23.196.166', 40104),
    ('188.165.227.180', 40102),
    ('188.165.227.180', 40104),
    ('seeds.test.golem.network', 40102),
    ('seeds.test.golem.network', 40104),
]

# APPS

APP_MANAGER_CONFIG_FILES = [
    os.path.join('apps', 'registered.ini'),
    os.path.join('apps', 'registered_test.ini')
]
