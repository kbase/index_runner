# Adding sample indexing to the index runner

## Reusable code

* The event loop in `main.py`
* The logging code in `main.py`
* `config.py` (currently some code in `main.py` could probably be moved into `config.py` for
  separation of concerns reasons)
* The Kafka code in `main.py` with configurable topics

## Non-reusable code

* `_handle_message` in `main.py` and the methods it calls

## Refactoring to avoid (nearly) duplicate code for sample indexing

* Refactor the event loop so that the message handling function can be passed into the event loop
* Separate the workspace specific code into its own module with a `main()` method that
  starts the event loop and passes an event handler function to the event loop.
* Move all config updating code into `config.py` from `main.py`
* Move Kafka related stuff into own module, including `_produce` and sub methods
* Move `init_logger` into its own module (?)

## Design

* Main a new `sample_indexer.py` class that is the equivalent of `main.py`, but handles samples
* Should look something like this:

```
def _handle_sample_message(msg: Dict):
    '''
    handle any kafka sample messages.
    '''

def main():
    kafka = kakfa_client.init_kafka(config()['topics']['sample'])
    event_loop.start_loop(_handle_sample_message)



if __name__ == '__main__':
    # Set up the logger
    # Make the urllib debug logs less noisy
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    index_logger.init_logger()
    # Run the main thread
    main()
```

* This allows reuse of the configuration mechanism, kafka code, and event loop.

