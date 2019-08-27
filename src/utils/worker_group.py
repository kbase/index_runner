"""
Small manager of a group of processes with a work queue.
"""
import traceback
from dataclasses import dataclass
from typing import Tuple, Callable
from queue import Empty
from multiprocessing import Process, Queue


@dataclass
class WorkerGroup:
    cls: Callable   # class to run for each worker
    args: Tuple     # arguments for the above class
    count: int = 1  # how many workers to run

    def __post_init__(self):
        """Start the workers."""
        self.name = self.cls.__name__
        self.queue = Queue()  # type: Queue
        # Initialize child workers
        children = {}  # type: dict
        if hasattr(self.cls, 'init_children') and callable(self.cls.init_children):
            children = self.cls.init_children()
        # Start all of the worker processes
        self.workers = [_create_proc(self.cls, self.args, self.queue, children) for _ in range(self.count)]

    def kill(self):
        """Kill all workers."""
        for proc in self.workers:
            proc.kill()


# -- Utilities

def _create_proc(cls, args, queue, children):
    """Create and start a new process from a function and arguments."""
    child_queues = {key: worker.queue for (key, worker) in children.items()}
    proc = Process(target=_run_worker, args=(cls, args, queue, child_queues), daemon=True)
    proc.start()
    return proc


def _run_worker(cls, args, queue, child_queues):
    """Initialize and run an event loop within a child process for a worker class."""
    inst = cls(*args)
    # Link all child worker queues so inst can push work to them
    inst.children = {}
    for (worker_name, child_queue) in child_queues.items():
        inst.children[worker_name] = child_queue
    # Set a timeout in milliseconds for receiving messages, if present
    try:
        timeout = inst.timeout_ms / 1000
    except AttributeError:
        timeout = None
    while True:
        try:
            msg = queue.get(block=True, timeout=timeout)
            try:
                # Send the message to the worker
                inst.receive(msg)
            except Exception as err:
                _report_err(err)
        except Empty:
            # We've hit the timeout
            # If inst has a .timeout method, then run it
            if hasattr(inst, 'timeout') and callable(inst.timeout):
                try:
                    inst.timeout()
                except Exception as err:
                    _report_err(err)


def _report_err(err):
    """Verbosely print an error caught in a worker's event loop."""
    print('=' * 80)
    print(err)
    print('-' * 80)
    traceback.print_exc()
    print('=' * 80)
