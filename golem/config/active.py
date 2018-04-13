import os

if os.environ.get('GOLEM_ENVIRONMENT') == 'mainnet':
    from golem.config.environments.mainnet import *  # noqa # pylint: disable=unused-import
else:
    from golem.config.environments.testnet import *  # noqa # pylint: disable=unused-import

# Put your local settings here
