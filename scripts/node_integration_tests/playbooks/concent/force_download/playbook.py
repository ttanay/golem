from functools import partial

from scripts.node_integration_tests import helpers

from ..concent_base import ConcentTestPlaybook
from ...test_config_base import NodeId


class Playbook(ConcentTestPlaybook):
    forced_download_successful = False

    def step_wait_task_finished(self):
        fail_triggers = ['Concent request failed', ]
        download_trigger = ['Concent results download successful', ]

        log_match_pattern = \
            '.*' + '.*|.*'.join(fail_triggers + download_trigger) + '.*'

        log_match = helpers.search_output(
            self.output_queues[NodeId.requestor],
            log_match_pattern,
        )

        if log_match:
            match = log_match.group(0)
            if any([t in match for t in fail_triggers]):
                self.fail("Requestor<->Concent comms failure: %s " % match)
                return
            if any([t in match for t in download_trigger]):
                print("Concent download successful.")
                self.forced_download_successful = True

        concent_fail = helpers.search_output(
            self.output_queues[NodeId.provider],
            ".*Concent request failed.*|.*Can't receive message from Concent.*",
        )

        if concent_fail:
            print("Provider: ", concent_fail.group(0))
            self.fail()
            return

        return super().step_wait_task_finished(node_id=NodeId.requestor)

    def step_verify_forced_download_happened(self):
        if self.forced_download_successful:
            self.next()
        else:
            self.fail(
                "The task might have finished but "
                "we didn't notice the Requestor<->Concent communicating."
            )

    steps = ConcentTestPlaybook.initial_steps + (
        partial(ConcentTestPlaybook.step_create_task, node_id=NodeId.requestor),
        partial(ConcentTestPlaybook.step_get_task_id, node_id=NodeId.requestor),
        partial(ConcentTestPlaybook.step_get_task_status,
                node_id=NodeId.requestor),
        step_wait_task_finished,
        step_verify_forced_download_happened,
        ConcentTestPlaybook.step_verify_output,
        partial(ConcentTestPlaybook.step_get_subtasks,
                node_id=NodeId.requestor),
        partial(ConcentTestPlaybook.step_verify_node_income,
                node_id=NodeId.provider, from_node=NodeId.requestor),
    )
