"""Offline bounded journal parser; never connects to board or discovers USB.

The caller MUST revalidate current USB identity, address and xHCI slot/context
for EACH window. Device address is not assumed to equal xHCI slot number.
All outputs are filtered scalar evidence. A journal tail is not a lossless log.
"""
import argparse
import json
from pathlib import Path
import re

WARNING = re.compile(r"HC couldn't access mem fast enough for slot ([0-9]+) ep ([0-9]+)")


def boot(value):
    if not isinstance(value,str):raise ValueError('Current boot id required')
    value=value.replace('-','').lower()
    if not re.fullmatch(r'[0-9a-f]{32}',value):raise ValueError('Invalid boot id')
    return value


def current_mapping(value,boot_id,end_us):
    if not isinstance(value,dict):return None
    try:
        if (value.get('verified_current_boot_device') is not True or boot(value.get('boot_id'))!=boot_id
                or value.get('mapping_basis')!='READ_CURRENT_USB_AND_XHCI_CONTEXTS'
                or type(value.get('observed_mono_us')) is not int
                or not 0<=end_us-value['observed_mono_us']<=5000000
                or type(value.get('slot_id')) is not int or not 1<=value['slot_id']<=255
                or type(value.get('device_address')) is not int or not 1<=value['device_address']<=127
                or type(value.get('endpoint_index')) is not int or not 1<=value['endpoint_index']<=31
                or type(value.get('endpoint_address')) is not int or not 1<=value['endpoint_address']<=15
                or value.get('direction')!='out' or value.get('transfer_type')!='isochronous'
                or value['endpoint_index']!=2*value['endpoint_address']-1
                or not re.fullmatch(r'[0-9a-f]{4}',value.get('usb_vid',''))
                or not re.fullmatch(r'[0-9a-f]{4}',value.get('usb_pid',''))):
            return None
        return value
    except (ValueError,TypeError):return None


def parse_window(lines,*,boot_id,since_us,until_us,mapping,max_entries=128):
    boot_id=boot(boot_id)
    if (type(since_us) is not int or type(until_us) is not int or not 0<=since_us<until_us
            or until_us-since_us>10000000 or type(max_entries) is not int or not 16<=max_entries<=256):
        raise ValueError('Bounded monotonic journal window required')
    mapped=current_mapping(mapping,boot_id,until_us)
    result={'schema_version':'aura-bounded-kernel-window-1',
            'scope':'JOURNAL_MONOTONIC_TAIL_ONLY_NOT_USB_PLAYBACK_ACCEPTANCE',
            'since_mono_us':since_us,'until_mono_us':until_us,'max_entries':max_entries,
            'mapping_verified_by_caller':mapped is not None,
            'entries_parsed':0,'malformed_entries':0,'old_or_future_entries':0,'other_boot_entries':0,
            'new_entries':0,'matching_warning_entries':0 if mapped else None,
            'other_device_warning_entries':0,'first_matching_mono_us':None,'last_matching_mono_us':None,
            'input_saturated':False,'observation_complete':False,'usb_playback_health':'UNVERIFIED',
            'reported_count_is_lower_bound':True,'mapping_discovered_by_this_tool':False}
    for index,line in enumerate(lines):
        if index>=max_entries:
            result['input_saturated']=True
            break
        result['entries_parsed']+=1
        try:
            if not isinstance(line,str) or len(line)>32768:raise ValueError()
            entry=json.loads(line)
            if boot(entry.get('_BOOT_ID'))!=boot_id:
                result['other_boot_entries']+=1
                continue
            stamp=entry.get('__MONOTONIC_TIMESTAMP')
            if not isinstance(stamp,str) or not re.fullmatch(r'[0-9]{1,18}',stamp):raise ValueError()
            stamp=int(stamp)
            if not since_us<stamp<=until_us:
                result['old_or_future_entries']+=1
                continue
            result['new_entries']+=1
            message=entry.get('MESSAGE')
            if not isinstance(message,str):raise ValueError()
            match=WARNING.search(message)
            if match and mapped:
                if (int(match[1]),int(match[2]))==(mapped['slot_id'],mapped['endpoint_index']):
                    result['matching_warning_entries']+=1
                    old=result['first_matching_mono_us']
                    result['first_matching_mono_us']=stamp if old is None else min(old,stamp)
                    old=result['last_matching_mono_us']
                    result['last_matching_mono_us']=stamp if old is None else max(old,stamp)
                else:result['other_device_warning_entries']+=1
        except (ValueError,TypeError,AttributeError):result['malformed_entries']+=1
    result['input_saturated'] |= result['entries_parsed']>=max_entries
    result['status']=('MAPPING_UNVERIFIED' if not mapped else
        'INCOMPLETE_SATURATED_TAIL' if result['input_saturated'] else
        'INCOMPLETE_MALFORMED_TAIL' if result['malformed_entries'] else 'BOUNDED_JOURNAL_OBSERVATION')
    return result


def main():
    parser=argparse.ArgumentParser(description='Offline numeric journal filtering; no hardware access')
    parser.add_argument('--input-jsonl',type=Path,required=True)
    parser.add_argument('--mapping-json',type=Path,required=True)
    parser.add_argument('--boot-id',required=True)
    parser.add_argument('--since-us',type=int,required=True)
    parser.add_argument('--until-us',type=int,required=True)
    args=parser.parse_args()
    mapping=json.loads(args.mapping_json.read_text())
    with args.input_jsonl.open(encoding='utf-8') as source:
        result=parse_window(source,boot_id=args.boot_id,since_us=args.since_us,until_us=args.until_us,mapping=mapping)
    print(json.dumps(result,allow_nan=False))


if __name__=='__main__':main()
