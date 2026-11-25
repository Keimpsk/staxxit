"""Stateless text protocol adapter for the C++ engine used by the tests."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reference'))
from oracle import stack_tokens, indexed


class Cpp:
    def __init__(self, executable):
        self.process = subprocess.Popen([str(Path(executable).resolve()), '--protocol'],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, bufsize=1)
        self.requests = 0

    def query(self, state, variant, action=None):
        tokens = [variant, str(state.side), *map(str,state.reserve), *stack_tokens(state)]
        if action is not None:
            tokens.extend(map(str,indexed(action)))
        self.process.stdin.write(' '.join(tokens) + '\n')
        self.process.stdin.flush()
        response = self.process.stdout.readline()
        if not response:
            raise RuntimeError('C++ protocol stopped: ' + self.process.stderr.read())
        self.requests += 1
        value = json.loads(response)
        if 'error' in value:
            raise RuntimeError(value['error'])
        return value

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            self.process.wait(timeout=10)
        self.process.stdout.close()
        errors = self.process.stderr.read()
        self.process.stderr.close()
        if self.process.returncode:
            raise RuntimeError(f'C++ exit {self.process.returncode}: {errors}')
