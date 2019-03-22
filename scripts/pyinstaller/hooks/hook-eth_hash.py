from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('eth_hash') + \
                collect_submodules('eth_hash.backends')
