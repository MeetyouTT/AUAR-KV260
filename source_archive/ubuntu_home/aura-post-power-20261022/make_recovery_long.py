"""Use the reviewed AST extension, preserving older trial manifests."""
from pathlib import Path
base=Path(__file__).with_name('make_long_trial.py')
source=base.read_text()
old="'long-'+group+'-'+str(seconds)+'-manifest.json'"
new="'recovery50-long-'+group+'-'+str(seconds)+'-manifest.json'"
assert source.count(old)==1
source=source.replace(old,new)
exec(compile(source,str(base),'exec'),{'__file__':str(base),'__name__':'__main__'})
