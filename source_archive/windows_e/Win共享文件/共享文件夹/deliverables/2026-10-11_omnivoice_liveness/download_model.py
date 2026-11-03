"""Download official weights to an explicitly specified local experiment root."""
import argparse
import json
import os
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args()
    # Keep cache out of shared project and avoid implicit user-profile downloads.
    os.environ['HF_HOME']=str(args.destination.parent/'hf-cache')
    from huggingface_hub import HfApi,snapshot_download
    revision=HfApi().model_info('k2-fsa/OmniVoice').sha
    args.destination.mkdir(parents=True,exist_ok=True)
    print('MODEL REVISION '+revision,flush=True)
    snapshot_download('k2-fsa/OmniVoice',revision=revision,local_dir=str(args.destination))
    (args.destination/'download_identity.json').write_text(json.dumps(dict(repository='k2-fsa/OmniVoice',revision=revision),indent=2)+'\n',encoding='utf-8')
    print('MODEL READY',flush=True)


if __name__=='__main__':
    main()
