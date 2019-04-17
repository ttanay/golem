from functools import partial
import typing

from ...base import NodeTestPlaybook
from ...test_config_base import NodeId


class Playbook(NodeTestPlaybook):
    def step_restart_task_frame(self):
        def on_success(result):
            print(f'Restarted frame from task: {self.task_id}.')
            self.next()

        return self.call(NodeId.requestor,
                         'comp.task.subtasks.frame.restart',
                         self.task_id,
                         '1',
                         on_success=on_success)

    def step_success(self):
        self.success()

    steps: typing.Tuple = NodeTestPlaybook.initial_steps + (
        partial(NodeTestPlaybook.step_create_task, node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_get_task_id, node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_get_task_status,
                node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_wait_task_finished,
                node_id=NodeId.requestor),
        NodeTestPlaybook.step_stop_nodes,
        NodeTestPlaybook.step_restart_nodes,
    ) + NodeTestPlaybook.initial_steps + (
        partial(NodeTestPlaybook.step_get_known_tasks,
                node_id=NodeId.requestor),
        step_restart_task_frame,
        partial(NodeTestPlaybook.step_get_task_id, node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_get_task_status,
                node_id=NodeId.requestor),
        partial(NodeTestPlaybook.step_wait_task_finished,
                node_id=NodeId.requestor),
        NodeTestPlaybook.step_verify_output,
        step_success,
    )
