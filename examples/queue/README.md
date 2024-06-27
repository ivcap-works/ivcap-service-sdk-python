# Task Queue Example

This example demonstrates how to create a simple task queue service using the IVCAP SDK. The task queue is designed to simulate a task scheduler, where tasks are represented as strings and processed by worker threads.

## Overview

The `task_queue.py` script defines a service called "TaskQueue" with a single parameter `number_of_tasks`. When executed, the service creates a queue, adds the specified number of tasks to the queue, starts multiple worker threads to process the tasks, and then deletes the queue upon completion.

## Prerequisites

- Python 3.x
- IVCAP SDK installed and configured

## Running the Example

1. Make sure you have the IVCAP SDK installed and your environment is set up correctly.
2. Clone or download this repository.
3. Navigate to the directory containing the `task_queue.py` script.
4. Run the following command to execute the script with 50 tasks:

```
make run
```

This command sets the `PYTHONPATH` to the IVCAP SDK source directory and runs the `task_queue.py` script with the `--number_of_tasks` parameter set to 50.
