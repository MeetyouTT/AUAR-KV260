"""A single noisy in-zone image must not grant a new correction budget."""


class BoundaryRearm:
    def __init__(self,minimum_ms=250,minimum_sources=3):
        if type(minimum_ms) is not int or not 100<=minimum_ms<=1000:
            raise ValueError('A bounded stable-inside interval required')
        if type(minimum_sources) is not int or not 3<=minimum_sources<=20:
            raise ValueError('At least three distinct images required')
        self.minimum_ms,self.minimum_sources=minimum_ms,minimum_sources
        self.reset()

    def reset(self):
        self.start=self.last=None;self.count=0

    def observe(self,source,inside):
        if (not isinstance(source,tuple) or len(source)!=2
                or any(type(value) is not int for value in source)):
            raise ValueError('Admitted actual image identifier and timestamp required')
        if self.last is not None and (source[0]<=self.last[0] or source[1]<=self.last[1]):
            return False
        if self.last is not None and source[1]-self.last[1]>=250:self.reset()
        self.last=source
        if not inside:self.start=None;self.count=0;return False
        if self.start is None:self.start=source[1]
        self.count+=1
        return self.count>=self.minimum_sources and source[1]-self.start>=self.minimum_ms

    def status(self):
        elapsed=0 if self.start is None or self.last is None else self.last[1]-self.start
        return dict(required_stable_inside_ms=self.minimum_ms,required_distinct_images=self.minimum_sources,
                    stable_inside_ms=elapsed,distinct_inside_images=self.count)
