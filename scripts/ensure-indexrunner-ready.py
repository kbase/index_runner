import os
import time
import sys

STATE_FILE = "/scratch/indexrunner.state"
TIMEOUT = float(os.environ.get('READY_TIMEOUT', "60"))


def pluralize(n, singular_term, plural_term):
    if n is None:
        return f'no {plural_term}'
    elif n == 1:
        return f'1 {singular_term}'
    else:
        return f'{n} {plural_term}'


def check_status():
    if not os.path.exists(STATE_FILE):
        return False

    try:
        with open(STATE_FILE, 'r') as fin:
            content = fin.read()
            if content == 'ready':
                return True
            else:
                return False
    except Exception:
        return False


def main():
    start = time.time()
    while True:
        elapsed = time.time() - start
        if check_status():
            print(f'MONITOR: indexrunner service is ready after {pluralize(elapsed, "second", "seconds")}!')
            exit(0)

        if elapsed >= TIMEOUT:
            sys.stderr.write(f'MONITOR: indexrunner not ready after {pluralize(elapsed, "second", "seconds")}')
            exit(1)

        time.sleep(1)


print(f'MONITOR: waiting up to {pluralize(TIMEOUT, "second", "seconds")} for indexrunner service to be ready')
main()
