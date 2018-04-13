import os

from golem_sci.chains import MAINNET as _MAINNET
from .base import *  # noqa # pylint: disable=unused-import

# ETH

ETHEREUM_NODE_LIST = [
    'https://geth.golem.network:55555',
    'https://0.geth.golem.network:55555',
    'https://1.geth.golem.network:55555',
    'https://2.geth.golem.network:55555',
]

ETHEREUM_CHAIN = _MAINNET
ETHEREUM_FAUCET_ENABLED = False

# P2P

P2P_SEEDS = [
    ('seeds.golem.network', 40102),
]

# APPS

APP_MANAGER_CONFIG_FILES = [
    os.path.join('apps', 'registered.ini')
]

# Overrides

IS_MAINNET = True
