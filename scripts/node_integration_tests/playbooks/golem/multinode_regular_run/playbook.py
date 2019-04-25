from functools import partial, reduce
from operator import or_
import typing

from ...base import NodeTestPlaybook
from .test_config import NodeId


class Playbook(NodeTestPlaybook):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.paid_subtasks: typing.Dict[NodeId, typing.Set[str]] = {}

    def step_get_paid_subtasks(self, node_id: NodeId, from_node: NodeId):
        def on_success(result):
            self.paid_subtasks[node_id] = {
                p.get('subtask')
                for p in result
                if p.get('payer') == self.nodes_keys[from_node]
            }
            self.next()

        return self.call(node_id, 'pay.incomes', on_success=on_success)

    def step_verify_incomes(self):
        paid_subtasks = reduce(or_, self.paid_subtasks.values())
        unpaid = self.subtasks - paid_subtasks

        if unpaid:
            print("Found subtasks with no matching payments: %s" % unpaid)
            self.fail()
            return

        print("All subtasks accounted for.")
        self.next()

    initial_steps: typing.Tuple = (
        partial(NodeTestPlaybook.step_get_node_key, node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_get_node_key, node_id=NodeId.provider),
        partial(NodeTestPlaybook.step_get_node_key, node_id=NodeId.provider2),

        partial(NodeTestPlaybook.step_get_node_network_info,
                node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_ensure_node_network,
                node_id=NodeId.provider),
        partial(NodeTestPlaybook.step_ensure_node_network,
                node_id=NodeId.provider2),

        partial(NodeTestPlaybook.step_connect_nodes, node_id=NodeId.provider,
                target_node=NodeId.requestor),
        partial(NodeTestPlaybook.step_connect_nodes, node_id=NodeId.provider2,
                target_node=NodeId.requestor),

        partial(NodeTestPlaybook.step_verify_peer_connection,
                node_id=NodeId.requestor, target_node=NodeId.provider),
        partial(NodeTestPlaybook.step_verify_peer_connection,
                node_id=NodeId.requestor, target_node=NodeId.provider2),

        partial(NodeTestPlaybook.step_wait_node_gnt, node_id=NodeId.requestor),

        partial(NodeTestPlaybook.step_get_known_tasks,
                node_id=NodeId.requestor),
    )

    steps: typing.Tuple = initial_steps + (
        partial(NodeTestPlaybook.step_create_task, node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_get_task_id, node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_get_task_status,
                node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_wait_task_finished,
                node_id=NodeId.requestor),
        NodeTestPlaybook.step_verify_output,
        partial(NodeTestPlaybook.step_get_subtasks, node_id=NodeId.requestor),
        partial(step_get_paid_subtasks, node_id=NodeId.provider,
                from_node=NodeId.requestor),
        partial(step_get_paid_subtasks, node_id=NodeId.provider2,
                from_node=NodeId.requestor),
        step_verify_incomes,
    )
