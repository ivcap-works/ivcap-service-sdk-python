#
# Copyright (c) 2023 Commonwealth Scientific and Industrial Research Organisation (CSIRO). All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file. See the AUTHORS file for names of contributors.
#
import logging
import threading
import time
from typing import Dict
from ivcap_sdk_service import (
    Service,
    Parameter,
    PythonWorkflow,
    Type,
    QueueService,
    register_service,
    get_queue_service,
)

SERVICE = Service(
    name="TaskQueue",
    description="A simple task queue for a task scheduler",
    parameters=[
        Parameter(
            name="number_of_tasks",
            type=Type.INT,
            description="Number of tasks to add to the queue",
        ),
    ],
    workflow=PythonWorkflow(
        min_memory="2Gi", min_cpu="500m", min_ephemeral_storage="4Gi"
    ),
)

# We will create a script to simulate a task queue for a simple task scheduler.
# This script will use the `LocalQueueService` class to manage tasks, where tasks
# are represented as strings. The script will simulate adding tasks to the queue,
# processing them, and handling exceptions when trying to retrieve tasks from an empty queue.

# This script demonstrates a multi-threaded task queue where tasks are processed by worker threads.
# It uses the `LocalQueueService` class for thread-safe queue operations, ensuring that tasks are
# processed in a first-in, first-out manner. The script also handles the case where a worker thread
# tries to retrieve a task from an empty queue, demonstrating exception handling in a non-trivial
# use of the queue library.


def process_task(task, logger: logging):
    """
    Function to process a task by simulating task processing time.
    """
    logger.info(f"Processing task: {task}")
    time.sleep(1)  # Simulate task processing time
    logger.info(f"Finished task: {task}")


def worker(
    queue_service: QueueService,
    queue_name: str,
    logger: logging,
    tasks_processed: dict,
    tasks_processed_lock: threading.Lock,
    total_tasks: int,
) -> None:
    """
    Function to simulate a worker that processes tasks from a queue.
    """
    processed_tasks = 0
    while True:
        messages = queue_service.dequeue(queue_name)
        if not messages:
            # Check if all tasks have been processed
            with tasks_processed_lock:
                total_processed = sum(tasks_processed.values())
                if processed_tasks + total_processed >= total_tasks:
                    logger.info("All tasks completed, worker exiting.")
                    break

        for task in messages:
            process_task(task, logger)
            processed_tasks += 1

        # Update the shared counter of processed tasks
        with tasks_processed_lock:
            thread_id = threading.get_ident()
            tasks_processed[thread_id] = processed_tasks


def coordinate(args: Dict, logger: logging):
    """
    Main function to create tasks and add them to the queue.
    """
    queue_service = get_queue_service()
    queue_name = "tasks"
    queue_description = "Store tasks to be processed"
    queue = queue_service.create(queue_name, queue_description)
    logger.info(f"Created queue: {queue}")

    # Add tasks to the queue based on the input parameter args.number_of_tasks
    total_tasks = args.number_of_tasks
    for i in range(total_tasks):
        task_name = f"Task {i + 1}"
        queue_service.enqueue(queue_name, task_name)
    logger.info(f"Added {total_tasks} tasks to the queue.")

    # Create a shared counter for processed tasks
    logger.info("Starting worker threads to process tasks.")
    tasks_processed = {}
    tasks_processed_lock = threading.Lock()

    # Create worker threads
    worker_threads = []
    for _ in range(3):
        worker_thread = threading.Thread(
            target=worker,
            args=(
                queue_service,
                queue_name,
                logger,
                tasks_processed,
                tasks_processed_lock,
                total_tasks,
            ),
        )
        worker_thread.start()
        worker_threads.append(worker_thread)

    for thread in worker_threads:
        thread.join()
    logger.info("All worker threads have completed.")

    # Delete the queue
    queue_service.delete(queue_name)
    logger.info(f"Deleted queue: {queue_name}")


register_service(SERVICE, coordinate)
