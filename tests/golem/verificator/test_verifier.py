from datetime import datetime
from unittest import TestCase

from freezegun import freeze_time

from golem.verificator.verifier import StateVerifier, SubtaskVerificationState


class VerifierTest(TestCase):

    @staticmethod
    def test_task_timeout():
        subtask_id = 'abcde'

        with freeze_time():
            time = datetime.utcnow()

            sv = StateVerifier()
            res_subtask_id, res_state, res_answer = sv.task_timeout(subtask_id)

        assert res_subtask_id == subtask_id
        assert res_state == SubtaskVerificationState.TIMEOUT
        assert res_answer['time_started'] == time
        assert res_answer['time_ended'] == time
