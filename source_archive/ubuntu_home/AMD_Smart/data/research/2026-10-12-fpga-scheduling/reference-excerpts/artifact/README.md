# Time-Predictable Acceleration of Deep Neural Networks on FPGA SoCs with Multi-Core DPUs (Artifact)

32nd IEEE Real-Time and Embedded Technology and Applications Symposium (RTAS 2026)

**Related Paper**: Federico Aromolo, Niko Salamini, Jacopo Del Granchio, Alessandro Biondi, Mauro Marinoni, Giorgio Buttazzo, "*Time-Predictable Acceleration of Deep Neural Networks on FPGA SoCs with Multi-Core DPUs*," in Proceedings of the 32nd IEEE Real-Time and Embedded Technology and Applications Symposium (RTAS 2026), Saint Malo, France, May 12–14, 2026. IEEE.

## Scope
This artifact enables the reproduction of the experimental results presented in the related paper “Time-Predictable Acceleration of Deep Neural Networks on FPGA SoCs with Multi-Core DPUs”. The paper presents a scheduling and analysis framework designed to achieve time-predictable inference of deep neural networks (DNN) on FPGA-based systems on chip leveraging multi-core configurations of the AMD Deep Learning Processor Unit (DPU). The framework provides timing guarantees by leveraging memory traffic regulation in the DPU inference and priority-driven scheduling of split DNNs to regulate access to the DPU cores. The source code provided in the artifact implements the proposed timing analysis, based on limited-preemptive fixed-priority scheduling, and the related allocation algorithm, which determines suitable assignments of DNN models to the DPU cores. These algorithms were applied in the experimental evaluation to configure the parameters of the evaluated task sets and perform schedulability analysis. The evaluation includes a comparison with the baseline approach obtained by leveraging the default system configuration of a multi-core DPU.

The artifact successfully passed the RTAS 2026 Artifact Evaluation process and was verified as reproducible by the RTAS 2026 Artifact Evaluation Committee.

Specifically, the content of this artifact allows to reproduce the following results presented in the experimental evaluation of the related paper (Sec. VII):
- Schedulability ratios obtained with varying number of tasks and DPU inference workload (Fig. 4(a-e)).
- Average analysis times obtained with varying number of tasks and DPU inference workload (Fig. 4(f)).

The RTAS 2026 Artifact Evaluation process also covered the profiling of inference times of the DNNs on the DPU cores, leveraging the proposed FPGA design integrating bus budgeting units, thus covering the following results presented in the experimental evaluation of the related paper (Sec. VII):
- Profiled execution times for each considered DNN model with different split configurations, including total split execution times obtained on an AMD ZCU102 UltraScale+ board (Table I).
- Observed maximum total inference times of each considered DNN model for different split configurations obtained on an AMD ZCU102 UltraScale+ board (Table II).

Profiling of execution times was performed on a AMD ZCU102 UltraScale+ board. To reproduce the results of Table I (profiled per-block WCETs) and Table II (observed WCETs for each model) for the purpose of artifact evaluation, remote access to a configured AMD ZCU102 UltraScale+ board running the required FPGA design was granted to the evaluators. The board was configured to run the custom FPGA design that is part of the framework, the compiled DNN models for inference on the DPU cores (stored in the form of compiled `xmodel` files), and all relevant scripts to run the evaluation.

## Requirements
The provided source code including the timing analysis and allocation algorithms was tested under the Ubuntu 22.04 operating system on a desktop computer equipped with an AMD Ryzen 7 6800HS processor with eight cores and 16 GiB of main memory. The provided instructions below apply to Ubuntu or similar Linux distributions. The source code for this part mostly consists of Python and Bash scripts, so a workstation or virtual machine with average system characteristics and a Linux operating system should suffice to reproduce the experiments.

## Contents
In addition to the present document, the artifact includes source code, scripts, and data pertaining to the experiments on schedulability analysis, including the workload generation, timing analysis, and allocation algorithms, for the purpose of reproducing the experimental results in Fig. 4(a-f) (schedulability analysis).
Furthermore, it includes source code for the scheduler component of the framework and for the evaluated DNN models (compatible with different splitting schemes).

#### Taskset Generation
The following files are included to generate the tasksets used for the experiments on schedulability evaluation (Fig. 4).

Scripts:
- `generator.py` - Python script used to implement UUniFast-discard on the generation of utilizations vectors.
- `taskset_generator.py` - Python script used to generate a set of tasksets given in input a JSON file describing a list of tasks specified as a taskset.
- `generate_taskset.sh` - bash script to generate a set of tasksets in the tasksets/ folder for each UTILIZATIONS value and TASKSET_SIZES specified in the script.

Data:
- `ai_taskset.json` - a JSON file describing the set of AI tasks, preloaded with the profiled WCETs specified in Table I for use in the experiments on schedulability analysis. Fields in the file include: `C{1,2,3,4}`, which specifies the WCETs of each chunk for each split configuration; `T` and `D`, which specify the initial period and deadline for the task sets (ignored in `taskset_generator.py`, since they are derived from the utilization vector of the generator).
- `tasksets` - folder containing the outputs of the `generate_taskset.sh` script, i.e., the set of tasksets generated by the taskset generation script.
- `tasksets.zip` - compressed folder containing the taskset data that was used to produce the results in Fig. 4 of the related paper.

#### Analysis and schedulability ratios
The following files are included to run the allocation and schedulability analysis algorithms used for the experiments on schedulability evaluation and measurement of analysis runtimes (Fig. 4).

Scripts:
- `rta_fifo.py`,`RT_fifo.py`,`rta.py`,`RT.py` - Python scripts performing the analysis on a single taskset for the baseline approach (FIFO scheduling) and the proposed approach (fixed-priority limited-preemptive scheduling).
- `launch_analysis.sh` - bash script to launch the analysis on the set of generated tasksets (located in the `tasksets/` folder) for both the baseline and the proposed approach, using the `rta_fifo.py` and `rta.py` scripts, respectively. The output is saved in the `analysis` folder.
- `schedulability_ratio_or.py`,`schedulability_ratio.py`, `compare_schedulability_csv.py` - Python scripts to generate and compare the schedulability ratios based on the results of the analysis (stored in the `analysis` folder). The output is saved in the corresponding folders: `analysis/fifo/schedulability_ratios.csv`,`analysis/limited_preemption/<n_chunks>/schedulability_ratios.csv`, `analysis/limited_preemption/schedulability_ratios_or.csv`. 
- `schedulability_ratio_plots.sh` - bash script to generate plots including the schedulability ratios with the proposed and baseline approaches, corresponding to the results in Figure 4(a-e) of the related paper. The plots are saved in the `comparison_plots/` folder.

Data:
- `analysis/fifo/utilization_<utilization>/<n_tasks>/*_output.json`,`analysis/limited_preemption/<n_chunks>/utilization_<utilization>/<n_tasks>/*_output.json` - JSON files including the results of the analysis for a specific taskset. The file name of each output file matches the name of the corresponding file that includes the analyzed taskset (located in the `tasksets` folder), with “`_output`” appended to the name. For each taskset, the JSON file includes the `all_schedulable` parameter, which specifies the schedulability status of the task set (a value of 1 indicates that the taskset was deemed schedulable by the analysis, a value of 0 indicates that it was deemed not schedulable). For each task in the taskset, `C` contains the WCET of the chunks, `T` is the task period, `D` is the task deadline, `A`: indicate the index of the DPU core to which the task is assigned, `R` indicates the response time reported by the analysis (in ms), `schedulable` indicates if a task is schedulable based on the analysis (1) or not (0), `Name`: name of the task, corresponding to the name of a specific DNN model which the task executes on the DPU.

#### Analysis runtime estimation
The following scripts are included to run the evaluation of analysis and allocation runtimes (Fig. 4(f)):
- `test_time_analysis.sh` - bash script to measure the runtime of the analysis for the baseline approach and the proposed approach (respectively, `rta_fifo.py` and `rta.py`). Results are stored in CSV files located in the `execution_time_analysis` folder.
- `plot_execution_times_analysis.py` - Python script to plot the runtimes of the analysis, corresponding to the results in Fig. 4(f) of the related paper. Inputs are taken from the CSV files in the `execution_time_analysis` folder.

#### DNN models
Source code for the evaluated DNN models, compatible with different splitting schemes, is provided in the `models` folder.

#### Scheduler
Source code for the scheduler component of the proposed framework is provided in the `scheduler` folder.

### Format of CSV data files
The following is the format of CSV data files storing the results of the experiments.
- `analysis/fifo/schedulability_ratios.csv`, `analysis/limited_preemption/{2,3,4}/schedulability_ratios.csv`, `analysis/limited_preemption/schedulability_ratios_or.csv` - These files contain the schedulability ratio for the baseline (FIFO) and proposed (limited-preemption) approaches. Format is as follows:
	- `Utilization`: utilization of the set of tasksets;
	- `N_task`: number of tasks in each taskset;
	- `Schedulability_ratio`: schedulability ratio derived from the file of the analysis.

- `execution_time_analysis/fifo_analysis_times.csv, execution_time_analysis/limited_preemption_analysis_times{2,3,4}.csv` - These files contain the analysis runtime (in milliseconds) for the set of tasksets across different values of the system utilization. Format is as follows:
	- `Utilization`: utilization of the set of tasksets;
	- `Analysis_time_ms`: runtime of the analysis (in ms).

## Running the experiments

### Reproducing the experiments in the paper
#### Schedulability analysis and analysis runtimes
The experiments on schedulability analysis (corresponding to the results in Fig. 4 in the paper) can be performed on a local machine.

First, change directory to `schedulability`:

```bash
cd schedulability
```

Then, unzip the `tasksets.zip` folder, which is preloaded with the generated tasksets that were used to produce the results in Fig. 4 of the paper:

```bash
unzip tasksets.zip
```

To run the analysis algorithms and reproduce the results in Fig. 4(a,b,c,d,e) of the paper, first launch the analysis on the set of generated tasksets for both the baseline (FIFO) and proposed (limited-preemption) approaches: 

```bash
./launch_analysis.sh
```
The expected runtime is approximately 30 minutes.

The output data, including schedulability for each analyzed taskset, will be stored in:
`analysis/limited_preemption/{2,3,4}/utilization_{1.0,1.2,1.4,1.6,1.8,2.0,2.2,2.4,2.8}/{4,6,8,10,12}/*_output.json` and `analysis/fifo/utilization_{1.0,1.2,1.4,1.6,1.8,2.0,2.2,2.4,2.8}/{4,6,8,10,12}/*_output.json`.

Then, calculate the schedulability ratio for both cases and generate the plots corresponding to those in Fig.4(a,b,c,d,e):

```bash
./schedulability_ratio_plots.sh
```
The expected runtime is approximately 10 seconds.

The outputs will be stored in:
- `analysis/fifo/schedulability_ratios.csv`
- `analysis/limited_preemption/2/schedulability_ratios.csv`
- `analysis/limited_preemption/3/schedulability_ratios.csv`
- `analysis/limited_preemption/4/schedulability_ratios.csv`
- `analysis/limited_preemption/schedulability_ratios_or.csv`
- `comparison_plots/schedulability_comparison_4.png`
- `comparison_plots/schedulability_comparison_6.png`
- `comparison_plots/schedulability_comparison_8.png`
- `comparison_plots/schedulability_comparison_10.png`
- `comparison_plots/schedulability_comparison_12.png`

Specifically, the plots included in the PNG files in the `comparison_plots` folder correspond, respectively, to those in Figure 4(a,b,c,d,e) of the paper, while the CSV files in the `analysis` folder contain the corresponding data.

To measure the runtime of the analysis (necessary to reproduce the results in Fig.4(f)), launch the following command:

```bash
./test_time_analysis.sh
```
The expected runtime is approximately 7 minutes.

The outputs will be stored in:
- `execution_time_analysis/fifo_analysis_times.csv`
- `execution_time_analysis/limited_preemption_analysis_times2.csv`
- `execution_time_analysis/limited_preemption_analysis_times3.csv`
- `execution_time_analysis/limited_preemption_analysis_times4.csv`
- `comparison_plots/execution_times_analysis_compare.png`

Specifically, the plot stored in the `comparison_plots/execution_times_analysis_compare.png` PNG file corresponds to that in Figure 4(f) of the paper, whereas the CSV files contain in the `execution_time_analysis` folder include the corresponding data. The results may differ from those in the paper, as they are dependent on the characteristics of the machine that is used to run the experiments.

#### Generating a new set of tasksets for the schedulability analysis experiments (OPTIONAL)
The `tasksets.zip` folder is preloaded with the generated tasksets that were used to produce the results in Fig. 4 of the paper. It is possible to randomly generate a new set of tasksets to evaluate using the schedulability analysis algorithms.

When launched from the `schedulability` folder, the following command can be used to populate the `schedulability/tasksets` folder with a new set of tasksets.

```bash
./generate_taskset.sh ai_taskset.json
```

Given this new data, it is possible to repeat the experiments of the LOCAL folder with this new set of tasksets and analyze the schedulability ratios and the execution times of the analysis following the same procedure described above to generate results similar to those in Fig.4 of the related paper.
