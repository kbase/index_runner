"""
Tests for the index_runner.py worker
"""
import os  # TODO remove
import unittest
import zmq
from src.index_runner.es_indexer import ESIndexer
from src.utils.worker_group import WorkerGroup
from src.utils.config import get_config

_CONFIG = get_config()


@unittest.skip('x')  # TODO remove
class TestESIndexer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        inp_sock_url = "ipc:///tmp/test_indexer_inp"
        out_sock_url = "ipc:///tmp/test_indexer_out"
        cls.inp_sock = zmq.Context.instance().socket(zmq.PUSH)
        cls.inp_sock.bind(inp_sock_url)
        cls.out_sock = zmq.Context.instance().socket(zmq.PULL)
        cls.out_sock.bind(out_sock_url)
        cls.inp_sock.setsockopt(zmq.LINGER, 0)
        cls.out_sock.setsockopt(zmq.LINGER, 0)
        cls.ir = WorkerGroup(fn=ESIndexer, args=(inp_sock_url, out_sock_url,), count=1)

    @classmethod
    def tearDownClass(cls):
        cls.ir.kill()

    def test_run_indexer_valid(self):
        # TODO remove prints
        print('tmp!', os.listdir('/tmp'))  # nosec
        print('test run indexer sending..')
        self.inp_sock.send_json({"wsid": 41347, "evtype": "NEW_VERSION", "objid": 5})
        print('Trying to receive from sock..')
        rep = self.out_sock.recv_json()
        self.assertEqual(rep['_action'], 'index')
        self.assertEqual(rep['doc']['narrative_title'], 'Test Narrative Name')
        self.assertEqual(rep['index'], 'narrative:1')
        self.assertEqual(rep['id'], 'WS::41347:5')
