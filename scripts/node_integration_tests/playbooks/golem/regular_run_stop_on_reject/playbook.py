from functools import partial
import typing

from scripts.node_integration_tests import helpers

from ...base import NodeTestPlaybook
from ...test_config_base import NodeId


class Playbook(NodeTestPlaybook):
    def step_wait_task_finished(self):
        verification_rejected = helpers.search_output(
            self.output_queues[NodeId.provider], '.*SubtaskResultsRejected.*'
        )

        if verification_rejected:
            self.fail(verification_rejected.group(0))
            return

        return super().step_wait_task_finished(NodeId.requestor)

    steps: typing.Tuple = NodeTestPlaybook.initial_steps + (
        partial(NodeTestPlaybook.step_create_task, node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_get_task_id, node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_get_task_status,
                node_id=NodeId.requestor),
        step_wait_task_finished,
        NodeTestPlaybook.step_verify_output,
        partial(NodeTestPlaybook.step_get_subtasks, node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_verify_node_income,
                node_id=NodeId.provider, from_node=NodeId.requestor),
    )
