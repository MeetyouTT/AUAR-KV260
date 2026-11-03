"""Summarize actual current-runtime records; no device access."""
import csv
from collections import Counter
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent


def lines(name):
    return [json.loads(s) for s in (HERE/name).read_text(encoding="utf-8").splitlines() if s.strip()]


def stats(values):
    v=sorted(x for x in values if type(x) in (int,float) and math.isfinite(x))
    return {"n":len(v),"mean":statistics.mean(v),"median":statistics.median(v),"min":min(v),"max":max(v),"p95_nearest_rank":v[math.ceil(len(v)*.95)-1]} if v else {"n":0}


def main():
    status=json.loads((HERE/"STATUS.json").read_text(encoding="utf-8"))
    assert status["phase"]=="FINISHED" and status["exit_code"]==0,"Measurement is not closed"
    rows=lines("board_model_gui.jsonl");host=lines("windows_gpu_health.jsonl")
    llm=[r for r in rows if r.get("event")=="LLM_RESULT"]
    tts=[r for r in rows if r.get("event")=="TTS_RESULT"]
    gui=[r for r in rows if r.get("event")=="GUI_SAMPLE"]
    start=next(r for r in rows if r.get("event")=="START");end=next(r for r in rows if r.get("event")=="END")
    goodllm=[r for r in llm if r.get("ok")];goodtts=[r for r in tts if r.get("ok")]
    with (HERE/"llm_cases.csv").open("w",newline="",encoding="utf-8-sig") as f:
        names=["case","rpc_ms","first_content_ms","first_json_closed_ms","backend_done_ms","prompt_eval_count","prompt_eval_cached_count","eval_count","prompt_eval_duration_ms","eval_duration_ms","total_duration_ms","decode_tokens_per_second","reply_characters","host_received_utc"]
        w=csv.DictWriter(f,fieldnames=names);w.writeheader()
        for r in goodllm:
            m=r["metrics"];m["decode_tokens_per_second"]=m["eval_count"]/(m["eval_duration_ms"]/1000)
            w.writerow({k:r.get(k,m.get(k)) for k in names})
    with (HERE/"tts_cases.csv").open("w",newline="",encoding="utf-8-sig") as f:
        names=["case","text_characters","rpc_ms","audio_seconds","rpc_real_time_factor","samples","sample_rate","cache_hit","host_received_utc"]
        w=csv.DictWriter(f,fieldnames=names);w.writeheader();w.writerows({k:r.get(k) for k in names} for r in goodtts)
    with (HERE/"windows_gpu_timeseries.csv").open("w",newline="",encoding="utf-8-sig") as f:
        names=["host_utc","host_mono","used_mib","free_mib","utilization_pct","memory_utilization_pct","temperature_c","power_w","sm_mhz"]
        w=csv.DictWriter(f,fieldnames=names);w.writeheader()
        for r in host:w.writerow({k:r.get(k,(r.get("gpu") or {}).get(k)) for k in names})
    L={k:stats([r.get(k,r["metrics"].get(k)) for r in goodllm]) for k in ["rpc_ms","first_content_ms","first_json_closed_ms","backend_done_ms","decode_tokens_per_second","prompt_eval_count","prompt_eval_cached_count","eval_count","reply_characters"]}
    T={k:stats([r.get(k) for r in goodtts]) for k in ["rpc_ms","audio_seconds","rpc_real_time_factor","text_characters"]}
    G={k:stats([(r.get("gpu") or {}).get(k) for r in host]) for k in ["used_mib","free_mib","utilization_pct","temperature_c","power_w"]}
    s={"schema":"aura-current-model-performance-results-1","created_host_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"run_id":status["run_id"],
       "scope":"AXIS_STOPPED_PERFORMANCE_MEASUREMENT_NOT_FULL_JOINT_FUNCTION_ACCEPTANCE",
       "model":"aura-qwen3.8-27b-abliterated:iq4_xs","model_parameter_size":"27.3B","quantization":"IQ4_XS","context_length":2048,"num_predict":120,"think":False,"output_format":"json",
       "tts":"OmniVoice","num_step":16,"sample_rate_hz":24000,"channels":1,"pcm_encoding":"s16le",
       "host_start_utc":status["host_started_utc"],"host_end_utc":status["host_ended_utc"],"board_start_monotonic_s":start["board_mono"],"board_end_monotonic_s":end["board_mono"],"actual_seconds":end["elapsed_seconds"],
       "llm_success":len(goodllm),"llm_attempted":len(llm),"tts_success":len(goodtts),"tts_attempted":len(tts),"planned_each":6,"skipped_cases":[r for r in rows if r.get("event")=="CASE_SKIPPED"],
       "llm":L,"tts_metrics":T,"windows_gpu":G,"host_sample_count":len(host),"gui_sample_count":len(gui),
       "all_tts_cache_hit_false":len(goodtts)>0 and all(r.get("cache_hit") is False for r in goodtts),
       "llm_accepted_deltas":[(r["health_after"]["counts"].get("accepted_llm",0)-r["health_before"]["counts"].get("accepted_llm",0)) for r in goodllm],
       "tts_generated_deltas":[(r["health_after"]["tts_counts"].get("generated",0)-r["health_before"]["tts_counts"].get("generated",0)) for r in goodtts],
       "gui_fault_max":max((r.get("gui_fault_count",0) for r in gui),default=None),"axis_following_samples":sum(r.get("pan",{}).get("automatic_following") is True for r in gui),
       "gui_page_counts":dict(Counter(r.get("ui_page") for r in gui)),"listening_state_counts":dict(Counter(r.get("hf_state") for r in gui)),
       "listening_enabled_samples":sum(r.get("hf_enabled") is True for r in gui),"microphone_open_samples":sum(r.get("microphone_open") is True for r in gui),
       "final_gui_phase":end["final"].get("phase"),"final_listening_state":end["final"].get("hf_state"),"errors":end["errors"],
       "definitions":{"first_content_ms":"Host stream first nonempty JSON content after model request start; not first spoken word or RPC response arrival.",
           "decode_tokens_per_second":"Ollama eval_count divided by eval_duration; includes complete JSON output tokens.",
           "rpc_ms":"Board monotonic request-to-complete-response; includes LAN, admission, inference and transfer.",
           "rpc_real_time_factor":"Complete TTS RPC seconds divided by returned PCM seconds; includes transfer/admission overhead, not isolated GPU kernel time.",
           "gpu_memory":"1-second nvidia-smi device samples; total device usage includes desktop and other processes, not isolated model allocation or guaranteed peak.",
           "warm_state":"Both original models already resident; no cold start/unload performed. Prefix cache was retained as production runtime normally uses it.",
           "statistics":"Six public input cases each; median/range are descriptive, P95 nearest rank with small N equals the maximum. No accuracy or stability guarantee.",
           "scope_exclusions":"No microphone ASR, real conversation context/memory, playback/acoustic first sound, motion, or visual artifact stability acceptance in these synthetic model requests."},
       "sources":[{"file":n,"sha256":hashlib.sha256((HERE/n).read_bytes()).hexdigest()} for n in ["CONTRACT.json","STATUS.json","board_model_gui.jsonl","windows_gpu_health.jsonl","measure_runtime.py"]]}
    (HERE/"RESULTS.json").write_text(json.dumps(s,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    def span(x,scale=1,digits=3):return f"{x['median']/scale:.{digits}f}（范围 {x['min']/scale:.{digits}f}–{x['max']/scale:.{digits}f}，n={x['n']}）"
    text=["2026-11-02 当前运行版本性能实测",f"运行编号：{s['run_id']}",f"实际窗口：{s['host_start_utc']} 至 {s['host_end_utc']}，板端历时 {s['actual_seconds']:.3f} 秒。",
      f"条件：KV260原视觉管线、主页面和转轴停止；实际GUI监听状态计数为 {s['listening_state_counts']}，开麦样本 {s['microphone_open_samples']}，不能写为持续监听负载。Windows RTX 5090 Laptop GPU，原27B IQ4_XS/2048上下文/120输出上限/think=false，原OmniVoice16。模型已驻留，无冷启动或参数调优。",
      f"LLM：成功 {s['llm_success']}/{s['llm_attempted']}；完整RPC中位数 {span(L['rpc_ms'],1000)} 秒；首个非空JSON内容中位数 {span(L['first_content_ms'],1000)} 秒；输出解码 {span(L['decode_tokens_per_second'])} token/s。",
      f"TTS：成功 {s['tts_success']}/{s['tts_attempted']}；完整RPC中位数 {span(T['rpc_ms'],1000)} 秒；生成PCM时长 {span(T['audio_seconds'])} 秒；RPC实时时间比 {span(T['rpc_real_time_factor'])}。所有本次TTS cache_hit=false：{s['all_tts_cache_hit_false']}。",
      f"GPU：{s['host_sample_count']}点，设备总显存占用中位 {span(G['used_mib'],1024)} GiB，最少空闲 {G['free_mib']['min']:.0f} MiB。每秒采样可能遗漏瞬时峰值。",
      f"GUI元数据：{s['gui_sample_count']}点，最大fault计数 {s['gui_fault_max']}；末状态 {s['final_gui_phase']}/{s['final_listening_state']}。",
      "口径：LLM首内容是软件流式首个JSON片段，并非扬声器首声；tok/s计入JSON字段和标点。TTS的RTF包含准入、推理和完整PCM返回，不是单独内核耗时。",
      "本轮是公开输入的小样本运行性能，不是全功能联合验收；未重测ASR/真实记忆上下文/声学延迟/转轴/视觉重影稳定性。DPU结果由报告窗口独立180秒采样给出。",
      "原始记录、逐次CSV、时间序列及SHA256来源见同目录。"]
    (HERE/"RESULTS.txt").write_text("\n\n".join(text)+"\n",encoding="utf-8")
    print(json.dumps({"run_id":s['run_id'],"actual_seconds":s['actual_seconds'],"llm_success":s['llm_success'],"tts_success":s['tts_success'],"llm":L,"tts":T,"gpu":G},ensure_ascii=False))


if __name__=="__main__":main()
