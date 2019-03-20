from pathlib import Path

from ..base import NodeTestPlaybook


THIS_DIR: Path = Path(__file__).resolve().parent


class DisabledVerification(NodeTestPlaybook):
    provider_node_script = 'provider/debug'
    requestor_node_script = 'requestor/debug'

    provider_opts = {
        'overwrite_results': str(THIS_DIR / "fake_result.png"),
    }

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.task_dict['x-run-verification'] = 'disabled'
