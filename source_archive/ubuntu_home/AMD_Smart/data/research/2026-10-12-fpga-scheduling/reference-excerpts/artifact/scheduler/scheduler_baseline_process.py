import cv2
import numpy as np
import vart
import xir
import argparse
import time
import os
import re
import sys
import json
import pdb
from multiprocessing import Process, Queue, Barrier, Value
from glob import glob
import ctypes

#################################################################
# RANDOM IMAGE GENERATORS
#################################################################

# RESNET50, RESNET18, MOBILENET, CIFAR-10
def random_image_224(img_size=224, fix_scale=127):
    """Generate a random int8 CHW image"""
    img = np.random.randint(0, 224, (3, img_size, img_size), dtype=np.uint8)
    img = img.astype(np.float32)/255.0
    img = img * fix_scale
    return img.astype(np.int8)

# INCEPTION
def random_image_299(img_size=299, fix_scale=127):
    """Generate a random int8 CHW image"""
    img = np.random.randint(0, 256, (3, img_size, img_size), dtype=np.uint8)
    img = img.astype(np.float32) / 255.0   # normalize to [0, 1]
    img = (img - 0.5) * 2.0                # normalize to [-1, 1]
    img = img * fix_scale                  # scale to [-127, 127]
    return img.astype(np.int8)

# others
def random_image(img_size=32, fix_scale=127):
    """Generate a random int8 CHW image"""
    img = np.random.randint(0, 224, (3, img_size, img_size), dtype=np.uint8)
    img = img.astype(np.float32)/255.0
    img = img * fix_scale
    return img.astype(np.int8)


#################################################################
# DPU CORE ALLOCATOR CLASS
#################################################################

def get_child_subgraph_dpu(graph):
    root_subgraph = graph.get_root_subgraph()
    child_subgraphs = root_subgraph.toposort_child_subgraph()
    return [cs for cs in child_subgraphs if cs.has_attr("device") and cs.get_attr("device").upper() == "DPU"]

def runDPU(dpu, img):
    inputTensors = dpu.get_input_tensors()
    outputTensors = dpu.get_output_tensors()
    input_ndim = tuple(inputTensors[0].dims)
    output_ndim = tuple(outputTensors[0].dims)

    # input data
    inputData = [np.empty(input_ndim, dtype=np.int8, order="C")]
    inputData[0][0, ...] = img.reshape(input_ndim[1:])

    # output data
    outputData = [np.empty(output_ndim, dtype=np.int8, order="C")]

    # executing the job
    job_id = dpu.execute_async(inputData, outputData) # crashes here
    dpu.wait(job_id)

    return outputData[0]

class DPU_Core_Allocator:

    def __init__(self, n_cores, dummy_model_path):
        self.n_cores =  n_cores
        self.current_core_id = 0
        self.dummy_model_path = dummy_model_path

    def allocation(self, core_id, xmodel_path):
        counter = 0
        while self.current_core_id != core_id:
            dummy_graph = xir.Graph.deserialize(self.dummy_model_path)
            dummy_subgraphs = get_child_subgraph_dpu(dummy_graph)
            dpu_runner = vart.Runner.create_runner(dummy_subgraphs[0], "run")
            self.current_core_id = (self.current_core_id + 1) % self.n_cores
            counter += 1
        
        print(f"Allocation required {counter} iterations")
        
        # print info
        print(f"Assigned {xmodel_path} to core {core_id}")

        # configure the runner for the model
        graph = xir.Graph.deserialize(xmodel_path)
        subgraph = get_child_subgraph_dpu(graph)
        runner = vart.Runner.create_runner(subgraph[0], "run")

        # since we created the runner for the xmodel_path, the counter must be incremented
        self.current_core_id = (self.current_core_id + 1) % self.n_cores

        return runner, graph

#################################################################
# AI TASK CLASS
#################################################################

class AI_Task:
    _id_counter = 0 # class variable shared by all instances
    def __init__(self, U, wcets, D, response_time, task_id: int, core_id: int, num_chunks: int, period_ms: int, xmodels_list, dpu_core_allocator):
        """
        Initialize a Task instance.

        Args:
            task_id (int): Unique identifier of the task.
            core_id (int): ID of the core the task is pinned to.
            num_chunks (int): Total number of chunks in the task.
            period (int): The task period.
        """
        # unique id
        self.unique_id = AI_Task._id_counter
        AI_Task._id_counter += 1

        # other class members
        self.U = U
        self.C = wcets
        self.D = D
        self.R = response_time
        self.task_id = task_id
        self.core_id = core_id
        self.num_chunks = num_chunks
        self.period = period_ms * 1e6 # period defined as ns
        self.current_chunk_idx = 0  # starts from 0
        self.current_input = 0 # the output for the next chunk
        self.xmodels_list = xmodels_list
        self.dpu_graphs = []
        self.dpu_runners = []
        self.input_fixpos = 0
        self.input_scale  = 0
        self.dpu_core_allocator = dpu_core_allocator
        self.input_images = []
        self.n_images = 10
        self.curr_image_idx = 0
        self.deadline_misses = 0
        self.ready = 1
        self.coin_owner = 0

    def set_core(self):
        for i, xmodel_chunk_path in enumerate(self.xmodels_list):
            runner, graph = self.dpu_core_allocator.allocation(self.core_id, xmodel_chunk_path)
            self.dpu_graphs.append(graph)
            self.dpu_runners.append(runner)
            if i == 0:
                self.input_fixpos = runner.get_input_tensors()[0].get_attr("fix_point")
                self.input_scale  = 2**self.input_fixpos

                # set dummy input images for this model
                inputTensors = runner.get_input_tensors()
                input_tensor = inputTensors[0]
                _, H, W, C = input_tensor.dims

                # Choose the appropriate random image function
                if H == 224 and W == 224:
                    rand_img_func = random_image_224
                elif H == 299 and W == 299:
                    rand_img_func = random_image_299
                else:
                    rand_img_func = random_image
                self.input_images = [rand_img_func(img_size=H, fix_scale=self.input_scale) for _ in range(self.n_images)]
                
                # initialize current_input with the first image
                self.current_input = self.input_images[0]
                
    def exec_next_chunk(self) -> int:
        # print(f"[Task {self.task_id}] Executing chunk {self.current_chunk_id} / {self.num_chunks - 1}")
        # print(f"[Task {self.task_id}] Current input image index: {self.curr_image_idx}")

        is_complete = 0
        if self.current_chunk_idx == (self.num_chunks-1):
            is_complete = 1
        
        # Run the chunk on the DPU
        self.current_input = runDPU(self.dpu_runners[self.current_chunk_idx], self.current_input)
        
        # Update chunk index
        self.current_chunk_idx = (self.current_chunk_idx + 1) % self.num_chunks

        # Overwrite the last output if we've completed a full round of chunks
        if self.current_chunk_idx == 0:
            # print(f"[Task {self.task_id}] Completed all chunks. Moving to next input image.")
            self.current_input = self.input_images[self.curr_image_idx]
            # print(f"[Task {self.task_id}] New current input image index: {self.curr_image_idx}")
            self.curr_image_idx = (self.curr_image_idx + 1) % len(self.input_images)
        
        return is_complete

    def __repr__(self):
        return (f"Task(id={self.task_id}, core={self.core_id}, period={self.period}, "
                f"chunks={self.num_chunks}, current_chunk={self.current_chunk_idx}, "
                f"current_input={self.current_input}, xmodels_list={self.xmodels_list})")



# def update_task_state(task, t_now, start_time_ns):
#     next_activation = task.next_activation_time_ns
#     period = task.period
#     job_counter = task.job_counter
#     last_end = task.last_job_end_time

#     # Check if next activation time is outdated
#     if t_now >= next_activation:
#         task.ready = 1

#         # Compute how many activations have passed
#         activations_passed = (t_now - next_activation) // period + 1
#         job_counter += activations_passed
#         outdated_activation_time_ns = next_activation
#         next_activation = start_time_ns + job_counter * period

#         # Deadline miss conditions
#         if activations_passed == 1:
#             if last_end > (outdated_activation_time_ns + period):
#                 task.deadline_misses += 1
#         else:
#             task.deadline_misses += activations_passed

#         # Write back updated fields
#         task.job_counter = job_counter
#         task.next_activation_time_ns = next_activation

#     else:
#         # Active job check
#         task.ready = 1 if task.serving_job_idx < task.job_counter else 0

def update_task_state(task, t_now, start_time_ns):
    next_activation_time_ns = task.next_activation_time_ns
    period = task.period
    job_counter = task.job_counter
    last_end = task.last_job_end_time

    # Check if next activation time is outdated
    if t_now >= next_activation_time_ns:
        task.ready = 1

        # update to the new activation time
        activations_counter = 0
        outdated_activation_time_ns = next_activation_time_ns
        while t_now >= next_activation_time_ns:
            job_counter += 1
            activations_counter += 1
            next_activation_time_ns = start_time_ns + (job_counter*period)
        
        # if there is one new activation only
        if activations_counter == 1 and last_end > (outdated_activation_time_ns):
            task.deadline_misses += 1
            print("deadline miss")

        # check if deadline miss occurred 
        if activations_counter > 1:
            task.deadline_misses += activations_counter 
            print("deadline miss")

        # Write back updated fields
        task.job_counter = job_counter
        task.next_activation_time_ns = next_activation_time_ns

    else:
        # the task has an active job
        if task.serving_job_idx < job_counter:
            task.ready = 1
        else:
            task.ready = 0

def task_function(task, simulation_time_ns, start_time_ns_shared, barrier, result_queue):

    # Hello
    print(f"Hello from task: {task.task_id}")

    # Init statistics and parameters
    task.ready = 1
    task.deadline_misses = 0
    task.response_times_ns = []
    task.serving_job_idx = 0
    task.job_counter = 1
    task.last_job_end_time = 0

    # Wait for all to reach here
    barrier.wait()

    # Wait for main process to set start time
    barrier.wait()
    start_time_ns = start_time_ns_shared.value  # all read the same timestamp

    # setting next_activation_period
    task.next_activation_time_ns = start_time_ns + task.period
    t_now = start_time_ns 
    inference_times = []
    # print(f"Difference with now: {(time.time_ns()-start_time_ns)/1e6}")

    # Task loop
    while t_now - start_time_ns < simulation_time_ns:
        if task.ready == 1:
            start_time_inf = time.time_ns()
            task.exec_next_chunk()
            inference_times.append((time.time_ns()-start_time_inf)/1e6)

            # add response time
            t_now = time.time_ns() 
            task.response_times_ns.append(
                t_now - (start_time_ns + (task.period * task.serving_job_idx))
            )
            task.last_job_end_time = t_now
            task.serving_job_idx += 1

            # update task state
            t_now = time.time_ns()
            update_task_state(task, t_now, start_time_ns) 
        
        else: 
            t_now = time.time_ns()
            sleep_time = max(0, (task.next_activation_time_ns - t_now) / 1e9)
            time.sleep(sleep_time)
            t_now = time.time_ns()
            update_task_state(task, t_now, start_time_ns) 
    
    # end
    result_queue.put({
        "task_id": task.task_id,
        "deadline_misses": task.deadline_misses,
        "avg_response_ms": np.mean(task.response_times_ns) / 1e6,
        "max_response_ms": np.max(task.response_times_ns) / 1e6
    })

    # print max inference time
    max_inference_times = np.max(inference_times)
    print(f"Max Inference Time {task.task_id}: {max_inference_times}")

# import taskset from json file
def import_tasksets(json_file, dpu_core_allocator):
    with open(json_file) as file:
        jdata = json.load(file)

    ts = []
    task_names = []
    core_id = 0
    num_procs = 3
    for jtask in jdata["taskset"]:
        # search for the xmodel of this task
        xmodel_paths = [os.path.join(jtask["Name"], f) for f in os.listdir(jtask["Name"])
            if os.path.isfile(os.path.join(jtask["Name"], f)) and f.endswith('.xmodel')]
        xmodel_paths.sort(key=lambda f: int(re.search(r'_p(\d+)\.xmodel$', f).group(1)))
        # __init__(self, wcets, D, response_time, task_id: int, core_id: int, num_chunks: int, period_ms: int, xmodels_list, dpu_core_allocator):
        task = AI_Task(jtask["U"], jtask["C"], jtask["D"], 0, jtask["Name"], core_id, len(xmodel_paths), jtask["T"], xmodel_paths, dpu_core_allocator) # only one xmodel
        task.set_core()
        ts.append(task)
        core_id = (core_id + 1) % num_procs

    return ts

def to_json(taskset, output_file):
    """
    Serialize a taskset (list of Task objects) to JSON, 
    including deadline_misses, avg_response_ms, and max_response_ms.
    """

    # ensure folder creation
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    data = {"taskset": []}

    for task in taskset:
        task_dict = {
            "C": task.C,
            "T": int(task.period / 1e6),
            "D": task.D,
            "U": task.U,
            "Name": task.task_id,
            "deadline_misses": getattr(task, "deadline_misses", 0),
            "avg_response_ms": getattr(task, "avg_response_ms", 0.0),
            "max_response_ms": getattr(task, "max_response_ms", 0.0)
        }
        data["taskset"].append(task_dict)

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

# ---------------------------
# Main launcher
# ---------------------------
def main(argv):

    # json file
    if len(sys.argv) < 2:
        print("Required arguments: json_file")
        exit()
    
    # arguments
    print("Arguments", sys.argv)
    json_file = sys.argv[1]
    simulation_time_ns = 30_000_000_000  # run for 30 seconds

    # dummy xmodel path
    dummy_model_path = "./dummy.xmodel"

    # define dpu_core_allocator
    num_procs = 3
    dpu_core_allocator = DPU_Core_Allocator(num_procs, dummy_model_path)

    # Import tasks
    tasks = import_tasksets(json_file, dpu_core_allocator)

    # define the barriers, one for each process and one for the main
    n_tasks = len(tasks)
    barrier = Barrier(n_tasks + 1)  # +1 for main process
    start_time_ns_shared = Value(ctypes.c_longlong, 0)  # shared 64-bit timestamp

    # Define the processes
    queues = []
    processes = []

    # Create all processes first
    for task in tasks:
        q = Queue()
        queues.append(q)
        p = Process(target=task_function, args=(task, simulation_time_ns, start_time_ns_shared, barrier, q))
        processes.append(p)
        p.start()

    # Wait until all are ready
    barrier.wait()

    # Now record and broadcast start time
    start_time_ns_shared.value = time.time_ns()

    # Release all tasks simultaneously
    barrier.wait()

    # Optionally wait for them
    for p in processes:
        p.join()

    # Collect results directly from the corresponding queue
    for task, q in zip(tasks, queues):
        if not q.empty():
            result = q.get()
            task.deadline_misses = result["deadline_misses"]
            task.avg_response_ms = result["avg_response_ms"]
            task.max_response_ms = result["max_response_ms"]

    # print task stats
    for task in tasks:
        # print schedule info
        print(f"Core_id: {task.core_id}, "
              f"Task {task.task_id}: Deadline misses = {task.deadline_misses}, "
              f"Avg response time = {task.avg_response_ms:.3f} ms, Max response time = {task.max_response_ms:.3f} ms, "
              f"Deadline: {task.D}, "
              f"Period: {task.period}")
    
    # print the taskset to a new json file
    new_name = json_file.replace(".json", "")
    new_name = new_name.replace("./tasksets/", "")
    output_file = "./output/" + new_name + "_output.json"
    to_json(tasks, output_file)

if __name__ == "__main__":
    main(sys.argv)