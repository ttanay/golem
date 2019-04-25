from functools import partial
from pathlib import Path
import re
import sys
import tempfile
import time
import traceback
import typing

from twisted.internet import reactor, task
from twisted.internet.error import ReactorNotRunning
from twisted.internet import _sslverify  # pylint: disable=protected-access

from scripts.node_integration_tests.rpc.client import RPCClient
from scripts.node_integration_tests import helpers, tasks

from golem.rpc.cert import CertificateError

from .test_config_base import NodeId

if typing.TYPE_CHECKING:
    from queue import Queue
    from subprocess import Popen
    from .test_config_base import TestConfigBase, NodeConfig


_sslverify.platformTrust = lambda: None


def print_result(result):
    print(f"Result: {result}")


def print_error(error):
    print(f"Error: {error}")


class NodeTestPlaybook:
    INTERVAL = 1

    start_time: float

    _loop: task.LoopingCall

    nodes_root: typing.Optional[Path] = None

    exit_code = None
    current_step = 0
    known_tasks = None
    task_id = None
    started = False
    nodes_started = False
    task_in_creation = False
    output_path = None
    subtasks = None

    reconnect_attempts_left = 7
    reconnect_countdown_initial = 10
    reconnect_countdown = None

    @property
    def task_settings_dict(self) -> dict:
        return tasks.get_settings(self.config.task_settings)

    @property
    def output_extension(self):
        return self.task_settings_dict.get('options', {}).get('format')

    @property
    def current_step_method(self):
        try:
            return self.steps[self.current_step]
        except IndexError:
            return None

    @property
    def current_step_name(self) -> str:
        return repr(self.current_step_method)

    @property
    def time_elapsed(self):
        return time.time() - self.start_time

    def fail(self, msg: typing.Optional[str] = None):
        print(msg or "Test run failed after {} seconds on step {}: {}".format(
                self.time_elapsed, self.current_step, self.current_step_name))

        for node_id, output_queue in self.output_queues.items():
            if self.config.dump_output_on_fail or (
                    self.config.dump_output_on_crash
                    and self.nodes_exit_codes[node_id] is not None):
                helpers.print_output(output_queue, node_id.value)

        self.stop(1)

    def _success(self):
        print("Test run completed in {} seconds after {} steps.".format(
            self.time_elapsed, self.current_step + 1, ))
        self.stop(0)

    def next(self):
        if self.current_step == len(self.steps) - 1:
            self._success()
            return
        self.current_step += 1

    def previous(self):
        assert (self.current_step > 0), "Cannot move back past step 0"
        self.current_step -= 1

    def _wait_gnt_eth(self, node_id: NodeId, result):
        gnt_balance = helpers.to_ether(result.get('gnt'))
        gntb_balance = helpers.to_ether(result.get('av_gnt'))
        eth_balance = helpers.to_ether(result.get('eth'))
        if gnt_balance > 0 and eth_balance > 0 and gntb_balance > 0:
            print("{} has {} total GNT ({} GNTB) and {} ETH.".format(
                node_id.value, gnt_balance, gntb_balance, eth_balance))
            self.next()

        else:
            print("Waiting for {} GNT(B)/converted GNTB/ETH ({}/{}/{})".format(
                node_id.value, gnt_balance, gntb_balance, eth_balance))
            time.sleep(15)

    def step_wait_node_gnt(self, node_id: NodeId):
        def on_success(result):
            return self._wait_gnt_eth(node_id, result)
        return self.call(node_id, 'pay.balance', on_success=on_success)

    def step_get_node_key(self, node_id: NodeId):
        def on_success(result):
            print(f"{node_id.value} key: {result}")
            self.nodes_keys[node_id] = result
            self.next()

        def on_error(_):
            print(f"Waiting for the {node_id.value} node...")
            time.sleep(3)

        return self.call(node_id, 'net.ident.key',
                         on_success=on_success, on_error=on_error)

    def step_configure_node(self, node_id: NodeId):
        opts = self.config.current_nodes[node_id].opts
        if not opts:
            self.next()
            return

        def on_success(_):
            print(f"Configured {node_id.value}")
            self.next()

        def on_error(_):
            print(f"failed configuring {node_id.value}")
            self.fail()

        return self.call(node_id, 'env.opts.update', opts,
                         on_success=on_success, on_error=on_error)

    def step_get_node_network_info(self, node_id: NodeId):
        def on_success(result):
            if result.get('listening') and result.get('port_statuses'):
                port = list(result.get('port_statuses').keys())[0]
                self.nodes_ports[node_id] = port
                print(f"{node_id.value}'s port: {port}")
                self.next()
            else:
                print(f"Waiting for {node_id.value}'s network info...")
                time.sleep(3)

        return self.call(node_id, 'net.status', on_success=on_success)

    def step_ensure_node_network(self, node_id: NodeId):
        def on_success(result):
            if result.get('listening') and result.get('port_statuses'):
                port = list(result.get('port_statuses').keys())[0]
                print(f"{node_id.value}'s port: {port}")
                self.next()
            else:
                print("Waiting for {node_id.value}'s network info...")
                time.sleep(3)

        return self.call(node_id, 'net.status', on_success=on_success)

    def step_connect_nodes(self, node_id: NodeId, target_node: NodeId):
        def on_success(result):
            print("Peer connection initialized.")
            self.reconnect_countdown = self.reconnect_countdown_initial
            self.next()
        return self.call(node_id, 'net.peer.connect',
                         ("localhost", self.nodes_ports[target_node]),
                         on_success=on_success)

    def step_verify_peer_connection(self, node_id: NodeId, target_node: NodeId):
        def on_success(result):
            if len(result) > len(self.config.current_nodes):
                print("Too many peers")
                self.fail()
                return
            elif len(result) > 0:
                expected_peer_key = self.nodes_keys[target_node]
                if expected_peer_key not in [peer['key_id'] for peer in result]:
                    print(f"Expected peer: {expected_peer_key} not in connected"
                          " peers: {result}")
                    self.fail()
                    return

                print(f"{node_id.value} connected with {target_node.value}.")
                self.next()
            else:
                if self.reconnect_countdown <= 0:
                    if self.reconnect_attempts_left > 0:
                        self.reconnect_attempts_left -= 1
                        print("Retrying peer connection.")
                        self.previous()
                        return
                    else:
                        self.fail("Could not sync nodes despite trying hard.")
                        return
                else:
                    self.reconnect_countdown -= 1
                    print("Waiting for nodes to sync...")
                    time.sleep(10)

        return self.call(node_id, 'net.peers.connected', on_success=on_success)

    def step_get_known_tasks(self, node_id: NodeId):
        def on_success(result):
            self.known_tasks = set(map(lambda r: r['id'], result))
            print(f"Got current tasks list from the {node_id.value}.")
            self.next()

        return self.call(node_id, 'comp.tasks', on_success=on_success)

    def step_create_task(self, node_id: NodeId):
        print("Output path: {}".format(self.output_path))
        print("Task dict: {}".format(self.config.task_dict))

        def on_success(result):
            if result[0]:
                print("Created task.")
                self.task_in_creation = False
                self.next()
            else:
                msg = result[1]
                if re.match('Not enough GNT', msg):
                    print(f"Waiting for {node_id.value}'s GNTB...")
                    time.sleep(30)
                    self.task_in_creation = False
                else:
                    print("Failed to create task {}".format(msg))
                    self.fail()

        if not self.task_in_creation:
            self.task_in_creation = True
            return self.call(node_id, 'comp.task.create', self.config.task_dict,
                             on_success=on_success)

    def step_get_task_id(self, node_id: NodeId):

        def on_success(result):
            tasks = set(map(lambda r: r['id'], result))
            new_tasks = tasks - self.known_tasks
            if len(new_tasks) != 1:
                print("Cannot find the new task ({})".format(new_tasks))
                time.sleep(30)
            else:
                self.task_id = list(new_tasks)[0]
                print("Task id: {}".format(self.task_id))
                self.next()

        return self.call(node_id, 'comp.tasks', on_success=on_success)

    def step_get_task_status(self, node_id: NodeId):
        def on_success(result):
            print("Task status: {}".format(result['status']))
            self.next()

        return self.call(node_id, 'comp.task', self.task_id,
                         on_success=on_success)

    def step_wait_task_finished(self, node_id: NodeId):
        def on_success(result):
            if result['status'] == 'Finished':
                print("Task finished.")
                self.next()
            elif result['status'] == 'Timeout':
                self.fail("Task timed out :( ... ")
            else:
                print("{} ... ".format(result['status']))
                time.sleep(10)

        return self.call(node_id, 'comp.task', self.task_id,
                         on_success=on_success)

    def step_verify_output(self):
        settings = self.task_settings_dict
        output_file_name = settings.get('name') + '.' + self.output_extension

        print("Verifying output file: {}".format(output_file_name))
        found_files = list(
            Path(self.output_path).glob(f'**/{output_file_name}')
        )

        if len(found_files) > 0 and found_files[0].is_file():
            print("Output present :)")
            self.next()
        else:
            print("Failed to find the output.")
            self.fail()

    def step_get_subtasks(self, node_id: NodeId):
        def on_success(result):
            self.subtasks = {
                s.get('subtask_id')
                for s in result
                if s.get('status') == 'Finished'
            }
            if not self.subtasks:
                self.fail("No subtasks found???")
            self.next()

        return self.call(node_id, 'comp.task.subtasks', self.task_id,
                         on_success=on_success)

    def step_verify_node_income(self, node_id: NodeId, from_node: NodeId):
        def on_success(result):
            payments = {
                p.get('subtask')
                for p in result
                if p.get('payer') == self.nodes_keys[from_node]
            }
            unpaid = self.subtasks - payments
            if unpaid:
                print("Found subtasks with no matching payments: %s" % unpaid)
                self.fail()
                return

            print("All subtasks accounted for.")
            self.next()

        return self.call(node_id, 'pay.incomes', on_success=on_success)

    def step_stop_nodes(self):
        if self.nodes_started:
            print("Stopping nodes")
            self.stop_nodes()

        time.sleep(10)
        self._poll_exit_codes()
        if any(exit_code is None
               for exit_code in self.nodes_exit_codes.values()):
            print("...")
            return

        if any(exit_code != 0 for exit_code in self.nodes_exit_codes.values()):
            for node_id, exit_code in self.nodes_exit_codes.items():
                if exit_code != 0:
                    print(f"Abnormal termination {node_id.value}: {exit_code}")
            self.fail()
            return

        print("Stopped nodes")
        self.next()

    def step_restart_nodes(self):
        print("Starting nodes again")
        self.config.use_next_nodes()

        self.task_in_creation = False
        time.sleep(60)

        self.start_nodes()
        print("Nodes restarted")
        self.next()

    initial_steps: typing.Tuple = (
        partial(step_get_node_key, node_id=NodeId.provider),
        partial(step_get_node_key, node_id=NodeId.requestor),
        partial(step_configure_node, node_id=NodeId.provider),
        partial(step_configure_node, node_id=NodeId.requestor),
        partial(step_get_node_network_info, node_id=NodeId.provider),
        partial(step_ensure_node_network, node_id=NodeId.requestor),
        partial(step_connect_nodes, node_id=NodeId.requestor,
                target_node=NodeId.provider),
        partial(step_verify_peer_connection, node_id=NodeId.requestor,
                target_node=NodeId.provider),
        partial(step_wait_node_gnt, node_id=NodeId.provider),
        partial(step_wait_node_gnt, node_id=NodeId.requestor),
        partial(step_get_known_tasks, node_id=NodeId.requestor),
    )

    steps: typing.Tuple = initial_steps + (
        partial(step_create_task, node_id=NodeId.requestor),
        partial(step_get_task_id, node_id=NodeId.requestor),
        partial(step_get_task_status, node_id=NodeId.requestor),
        partial(step_wait_task_finished, node_id=NodeId.requestor),
        step_verify_output,
        partial(step_get_subtasks, node_id=NodeId.requestor),
        partial(step_verify_node_income, node_id=NodeId.provider,
                from_node=NodeId.requestor),
    )

    @staticmethod
    def _call_rpc(method, *args, port, datadir, on_success, on_error, **kwargs):
        try:
            client = RPCClient(
                host='localhost',
                port=port,
                datadir=datadir,
            )
        except CertificateError as e:
            on_error(e)
            return

        return client.call(method, *args,
                           on_success=on_success,
                           on_error=on_error,
                           **kwargs)

    def call(self, node_id: NodeId, method: str, *args,
             on_success=print_result,
             on_error=print_error,
             **kwargs):
        node_config = self.config.current_nodes[node_id]
        return self._call_rpc(
            method,
            port=node_config.rpc_port,
            datadir=node_config.datadir,
            *args,
            on_success=on_success,
            on_error=on_error,
            **kwargs,
        )

    def start_nodes(self):
        for node_id, node_config in self.config.current_nodes.items():
            print(f"{node_id.value} config: {repr(node_config)}")
            node = helpers.run_golem_node(
                node_config.script,
                node_config.make_args(),
                nodes_root=self.nodes_root,
            )
            self.nodes[node_id] = node
            self.output_queues[node_id] = helpers.get_output_queue(node)

        self.nodes_started = True

    def stop_nodes(self):
        if not self.nodes_started:
            return

        for node_id, node in self.nodes.items():
            helpers.gracefully_shutdown(node, node_id.value)

        self.nodes_started = False

    def _poll_exit_codes(self):
        self.nodes_exit_codes = {
            node_id: node.poll()
            for node_id, node
            in self.nodes.items()
        }

    def run(self):
        if self.nodes_started:
            self._poll_exit_codes()
            if any(exit_code is not None
                   for exit_code in self.nodes_exit_codes.values()):
                for node_id, exit_code in self.nodes_exit_codes.items():
                    helpers.report_termination(exit_code, node_id.value)
                self.fail("A node exited abnormally.")

        try:
            method = self.current_step_method
            if callable(method):
                return method(self)
            else:
                self.fail("Ran out of steps after step {}".format(
                    self.current_step))
                return
        except Exception as e:  # noqa pylint:disable=too-broad-exception
            e, msg, tb = sys.exc_info()
            print("Exception {}: {} on step {}: {}".format(
                e.__name__, msg, self.current_step, self.current_step_name))
            traceback.print_tb(tb)
            self.fail()
            return

    def __init__(self, config: 'TestConfigBase') -> None:
        self.config = config

        def setup_datadir(
                node_id: NodeId,
                node_configs:
                'typing.Union[NodeConfig, typing.List[NodeConfig]]') \
                -> None:
            if isinstance(node_configs, list):
                datadir: typing.Optional[str] = None
                for node_config in node_configs:
                    if node_config.datadir is None:
                        if datadir is None:
                            datadir = helpers.mkdatadir(node_id.value)
                        node_config.datadir = datadir
            else:
                if node_configs.datadir is None:
                    node_configs.datadir = helpers.mkdatadir(node_id.value)

        for node_id, node_configs in self.config.nodes.items():
            setup_datadir(node_id, node_configs)

        self.output_path = tempfile.mkdtemp(
            prefix="golem-integration-test-output-")
        helpers.set_task_output_path(self.config.task_dict, self.output_path)

        self.nodes: 'typing.Dict[NodeId, Popen]' = {}
        self.output_queues: 'typing.Dict[NodeId, Queue]' = {}
        self.nodes_ports: typing.Dict[NodeId, int] = {}
        self.nodes_keys: typing.Dict[NodeId, typing.Any] = {}
        self.nodes_exit_codes: typing.Dict[NodeId, typing.Optional[int]] = {}

        self.start_nodes()
        self.started = True

    @classmethod
    def start(cls: 'typing.Type[NodeTestPlaybook]', config: 'TestConfigBase') \
            -> 'NodeTestPlaybook':
        playbook = cls(config)
        playbook.start_time = time.time()
        playbook._loop = task.LoopingCall(playbook.run)
        d = playbook._loop.start(cls.INTERVAL, False)
        d.addErrback(lambda x: print(x))

        reactor.addSystemEventTrigger(
            'before', 'shutdown', lambda: playbook.stop(2))
        reactor.run()

        return playbook

    def stop(self, exit_code):
        if not self.started:
            return

        self.started = False
        try:
            reactor.stop()
        except ReactorNotRunning:
            pass

        self.stop_nodes()
        self.exit_code = exit_code
