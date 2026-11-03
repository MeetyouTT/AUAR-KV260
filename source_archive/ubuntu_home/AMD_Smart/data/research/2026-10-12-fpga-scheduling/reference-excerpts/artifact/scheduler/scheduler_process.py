import json
import vart
import xir
import sys
import threading
import time
import os
import re
import cv2
import numpy as np
from multiprocessing import Process, Queue, Barrier, Value
from glob import glob
import pdb
from types import SimpleNamespace

"""
This module implements the scheduler. At the beginning, all the models/chunks are bound to one of the available cores.
The scheduler can preempt a task (chunks are always atomic) if there is one with a higher priority.
"""

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

    # print("INPUT TENSOR DIMS:", inputTensors[0].dims)
    # print("INPUT TENSOR NDIM tuple:", tuple(inputTensors[0].dims))
    # print("INPUT TENSOR dtype attr:", getattr(inputTensors[0], "dtype", None))
    # print("INPUT TENSOR has_attr('dtype')?:", inputTensors[0].has_attr("dtype") if hasattr(inputTensors[0], "has_attr") else None)
    # print("input_ndim:", input_ndim)
    # print("img.shape:", img.shape, "img.dtype:", img.dtype, "contiguous:", img.flags['C_CONTIGUOUS'])

    # print info about the shapes
    # print(f"[runDPU] input shape: {input_ndim}, output shape: {output_ndim}, img shape: {img.shape}")

    # input data
    inputData = [np.empty(input_ndim, dtype=np.int8, order="C")]
    inputData[0][0, ...] = img.reshape(input_ndim[1:])

    # output data
    outputData = [np.empty(output_ndim, dtype=np.int8, order="C")]

    # executing the job
    job_id = dpu.execute_async(inputData, outputData) 
    dpu.wait(job_id)

    return outputData[0]

class DPU_Core_Allocator:

    def __init__(self, n_cores, dummy_model_path):
        self.n_cores =  n_cores
        self.current_core_id = 0
        self.dummy_model_path = dummy_model_path

    def allocation(self, core_id, xmodel_path):
        while self.current_core_id != core_id:
            dummy_graph = xir.Graph.deserialize(self.dummy_model_path)
            dummy_subgraphs = get_child_subgraph_dpu(dummy_graph)
            dpu_runner = vart.Runner.create_runner(dummy_subgraphs[0], "run")
            self.current_core_id = (self.current_core_id + 1) % self.n_cores
        
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
    def __init__(self, wcets, D, response_time, task_id: int, core_id: int, num_chunks: int, period_ms: int, xmodels_list, dpu_core_allocator):
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

# import taskset from json file
def import_tasksets(json_file, dpu_core_allocator):
    with open(json_file) as file:
        jdata = json.load(file)

    ts = []
    for jtask in jdata["taskset"]:

        # search for the xmodels of the chunks of this task
        xmodel_paths = [os.path.join(jtask["Name"], f) for f in os.listdir(jtask["Name"])
                    if os.path.isfile(os.path.join(jtask["Name"], f)) and f.endswith('.xmodel')]
        xmodel_paths.sort(key=lambda f: int(re.search(r'_p(\d+)\.xmodel$', f).group(1)))

        # create the task
        task = AI_Task(jtask["C"], jtask["D"], jtask["R"], jtask["Name"], jtask["A"], len(jtask["C"]), jtask["D"], xmodel_paths, dpu_core_allocator)
        ts.append(task)

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
            "A": task.core_id,
            "R": task.R,
            "Name": task.task_id,
            "deadline_misses": getattr(task, "deadline_misses", 0),
            "avg_response_ms": getattr(task, "avg_response_ms", 0.0),
            "max_response_ms": getattr(task, "max_response_ms", 0.0)
        }
        data["taskset"].append(task_dict)

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)


def update_task_state(task, t_now, start_time_ns, core_i):

    # check if next_activation_time is outdated
    if t_now >= task.next_activation_time_ns:

        # task is now ready
        task.ready = 1

        # update to the new activation time
        activations_counter = 0
        outdated_activation_time_ns = task.next_activation_time_ns
        while t_now >= task.next_activation_time_ns:
            task.job_counter += 1
            activations_counter += 1
            task.next_activation_time_ns = start_time_ns + (task.job_counter*task.period)
        
        # if there is one new activation only
        if activations_counter == 1 and task.last_job_end_time > (outdated_activation_time_ns):
            task.deadline_misses += 1
            print("deadline miss")

        # check if deadline miss occurred 
        if activations_counter > 1:
            task.deadline_misses += activations_counter  
            print("deadline miss")

    # if next_activation_time is not outdated
    else:

        # the task has an active job
        if task.serving_job_idx < task.job_counter:
            task.ready = 1
        else:
            task.ready = 0
        


def task_scheduler(tasks_core, core_i, simulation_time_ns, result_queue):

    # Scheduler executes only if at least one task is assigned
    if not tasks_core:
        print(f"No Tasks for Core {core_i}, returning...")
        return

    # Hello From Core Scheduler
    print(f"Hello From Thread of Core {core_i}")
    max_chunk_execution = 10000000000
    
    # Initialize locks and start threads  
    for task in tasks_core:
        # init statistics and parameters
        task.deadline_misses = 0
        task.response_times_ns = []
        task.serving_job_idx = 0
        task.job_counter = 1
        task.last_job_end_time = 0
        # tasks are all ready 
        task.ready = 1
    
    # sort the ready queue for the first time
    ready_queue = []
    ready_queue = sorted(
        [t for t in tasks_core if t.ready == 1],
        key=lambda t: t.period
    )
    
    # set start time and next activation periods
    start_time_ns = time.time_ns() 
    for task in tasks_core:
        task.next_activation_time_ns = start_time_ns + task.period

    # Scheduler loop
    t_now = start_time_ns   # the first schedule is based on the start_time
    while t_now - start_time_ns < simulation_time_ns:

        # snapshot of the ready_queue
        ready_queue = sorted(
            [t for t in tasks_core if t.ready == 1],
            key=lambda t: t.period
        )

        # at least one task is ready
        if ready_queue:
            scheduled_task = ready_queue[0]
            # print(f"Scheduling Task: {scheduled_task.task_id}")
            is_complete = scheduled_task.exec_next_chunk()
            if is_complete == 1:
                # print(f"Completing task: {scheduled_task.task_id}, scheduled_task.serving_job_idx: {scheduled_task.serving_job_idx}, scheduled_task.job_counter: {scheduled_task.job_counter}")
                t_now = time.time_ns() 
                scheduled_task.response_times_ns.append(
                    t_now - (start_time_ns + (scheduled_task.period * scheduled_task.serving_job_idx))
                )
                scheduled_task.last_job_end_time = t_now
                scheduled_task.serving_job_idx += 1
            
            # SYNC STATE
            # update: the ready state, the job counter, next_activations, deadline_misses of all the tasks 
            t_now = time.time_ns()
            for task in tasks_core:
                update_task_state(task, t_now, start_time_ns, core_i)

        
        # wait for the closest next activation
        else:
            closest_activation = min(task.next_activation_time_ns for task in tasks_core)
            t_now = time.time_ns()
            sleep_time = max(0, (closest_activation - t_now) / 1e9)
            time.sleep(sleep_time)
            # SYNC STATE
            # update: the ready state, the job counter, next_activations, deadline_misses of all the tasks 
            for task in tasks_core:
                update_task_state(task, closest_activation, start_time_ns, core_i) # task state updated at the closest activation
        
        # t_now (HERE)
        t_now = time.time_ns()

    for task in tasks_core:
        task.avg_response_ms = np.mean(task.response_times_ns)/1e6 if task.response_times_ns else 0
        task.max_response_ms = np.max(task.response_times_ns)/1e6 if task.response_times_ns else 0
        print(f"Task {task.task_id}: Deadline misses = {task.deadline_misses}, "
              f"Avg response time = {task.avg_response_ms:.3f} ms, Max response time = {task.max_response_ms:.3f} ms")
        result_queue.put({
            "unique_id": task.unique_id,
            "task_id": task.task_id,
            "deadline_misses": task.deadline_misses,
            "avg_response_ms": task.avg_response_ms,
            "max_response_ms": task.max_response_ms
        })

def main(argv):

    # checking the argv size 
    if len(sys.argv) < 4:
        print("Required arguments: json_file, num_procs, dummy_model")
        exit()
    
    # arguments
    print("Arguments", sys.argv)
    json_file = sys.argv[1]
    num_procs = int(sys.argv[2])
    dummy_model_path = sys.argv[3]
    simulation_time_ns = 30_000_000_000  # run for 30 seconds

    # define dpu_core_allocator
    dpu_core_allocator = DPU_Core_Allocator(num_procs, dummy_model_path)

    # read the configuration file and init class with the dpu_allocator
    tasks = import_tasksets(json_file, dpu_core_allocator)

    # one Process for each core
    processes = []
    queues = []
    for i in range(num_procs):
        tasks_core = []
        for task in tasks:
            if task.core_id == i:
                # create runners and bind them to core i
                task.set_core()
                # append the task to the task_core structure
                tasks_core.append(task)
        # Queue
        q = Queue()
        queues.append(q)

        # Process
        p = Process(target=task_scheduler, args=(tasks_core, i, simulation_time_ns, q))
        processes.append(p)
    
    # start all processes
    for p in processes:
        p.start()
    
    # Wait for processes to finish
    for p in processes:
        p.join()

    # Collect results directly from the queues
    for q in queues:
        results = []
        while not q.empty():
            results.append(q.get())

        # Update corresponding tasks
        for r in results:
            for task in tasks:
                if r["unique_id"] == task.unique_id:
                    task.deadline_misses = r["deadline_misses"]
                    task.avg_response_ms = r["avg_response_ms"]
                    task.max_response_ms = r["max_response_ms"]


    # print the taskset to a new json file
    new_name = json_file.replace(".json", "")
    new_name = new_name.replace("./tasksets/", "")
    output_file = "./output/" + new_name + "_output.json"
    to_json(tasks, output_file)

if __name__ == "__main__":
    main(sys.argv)
