"""Experimental exact-kernel replay for OmniVoice forward; no quant/step changes."""
from collections import OrderedDict
import time
import memory_schedule_probe as experiment


class ForwardGraph:
    def __init__(self,forward):
        self.forward=forward;self.cache=OrderedDict();self.captures=0;self.replays=0;self.capture_ms=0.;self.warmed_key=None

    def __call__(self,*args,**kwargs):
        import torch
        if args or set(kwargs)!={'input_ids','audio_mask','attention_mask'}:
            raise ValueError('Unexpected forward contract; no silent approximation')
        key=tuple((name,tuple(t.shape),str(t.dtype),str(t.device)) for name,t in sorted(kwargs.items()))
        if key not in self.cache:
            # The first diffusion step is the shape warmup itself. Capture on
            # the second step instead of computing two extra forward passes.
            if self.warmed_key!=key:
                output=self.forward(**kwargs)
                self.warmed_key=key
                return output
            started=time.perf_counter()
            if len(self.cache)>=2:
                self.cache.popitem(last=False)
                torch.cuda.empty_cache()
            static={name:t.clone() for name,t in kwargs.items()}
            stream=torch.cuda.Stream()
            stream.wait_stream(torch.cuda.current_stream())
            graph=torch.cuda.CUDAGraph()
            with torch.cuda.graph(graph,stream=stream):
                output=self.forward(**static)
            self.cache[key]=(static,graph,output)
            self.captures+=1
            self.capture_ms+=(time.perf_counter()-started)*1000
        self.cache.move_to_end(key)
        static,graph,output=self.cache[key]
        for name,t in kwargs.items():static[name].copy_(t)
        graph.replay();self.replays+=1
        return output


class GraphVoice(experiment.DirectVoice):
    def __init__(self,synth):
        super().__init__(synth)
        self.original=synth.model.forward
        self.graph=ForwardGraph(self.original)

    def configure(self,mode):
        assert mode in ('resident','cuda_graph')
        self.synth.model.forward=self.graph if mode=='cuda_graph' else self.original

    def generate(self,text):
        captures,replays,ms=self.graph.captures,self.graph.replays,self.graph.capture_ms
        result=super().generate(text)
        self.metrics.update(new_graphs=self.graph.captures-captures,replays=self.graph.replays-replays,capture_ms=round(self.graph.capture_ms-ms,2))
        return result


experiment.RESULT_PATH=experiment.HERE/'cuda_graph.json'
experiment.MODES=('resident','cuda_graph','cuda_graph','resident')
experiment.RUN_INDEX=8
experiment.VOICE_CLASS=GraphVoice
experiment.probe_dflash.REPORT_PATH=experiment.HERE/'cuda_graph_runner.json'
if __name__=='__main__':
    try:experiment.main()
    except BaseException as exc:
        experiment.REPORT.update(status='FAILED_NOT_DEPLOYED',error=type(exc).__name__+': '+str(exc))
        experiment.save();raise
