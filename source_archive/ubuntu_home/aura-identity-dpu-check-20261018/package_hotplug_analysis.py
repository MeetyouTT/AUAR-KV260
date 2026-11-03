"""Publish only filtered diagnostic evidence and verify measured comparisons."""
import hashlib,json,re,shutil
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables')
OUT=BASE/'2026-10-21_hdmi_hotplug_analysis'
(OUT/'evidence').mkdir(parents=True,exist_ok=True)
(OUT/'src').mkdir(exist_ok=True)
provenance={}
def read(path):return json.loads(path.read_text())
def write(name,value):
 (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def latest(phase):
 s=read(HERE/('latest-'+phase+'.json'));assert s['complete'] and s['console_echo_restored']
 p=Path(s['evidence'])/'response.json'
 provenance[phase]={'evidence_path':str(p),'source_sha256':s['source_sha256'],'filtered_response_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 return read(p)
def old(folder,name):
 p=BASE/folder/'evidence'/(name+'.json')
 provenance[name]={'source_path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 return read(p)
recovery=old('2026-10-21_blackflash_recovery','blackflash-recovery-once-v3')
normal=old('2026-10-21_physical_hdmi_recovery','physical-hdmi-recovery-confirmed')
depth=old('2026-10-21_coldboot_flicker','coldboot-blackflash-scanout')
later_bad=old('2026-10-21_hdmi_original_baseline','original-baseline-after-manual-power')
assert recovery['boot_id']==normal['boot_id']==depth['boot_id']
assert recovery['before_edid']['bytes']==recovery['after_edid']['bytes']==0
assert normal['before']['edid_bytes']==normal['after']['edid_bytes']==128
assert recovery['after_units']==normal['before']['units']['text']==normal['after']['units']['text']
assert recovery['before_scanout']==recovery['after_scanout']
historical={'boot_id':normal['boot_id'],'software_cycle':recovery,
 'physical_hotplug_followup':normal,'failure_scanout_and_depth':depth,
 'user_report_before_physical':'整个屏幕黑闪','user_report_after_physical':'刚才插拔hdmi，画面已经正常',
 'exact_physical_event_time_captured':False,
 'separate_counterexample':{'boot_id':later_bad['boot_id'],'edid_bytes':later_bad['edid_bytes'],'edid_sha256':later_bad['edid_sha256'],'display':later_bad['display'],'user_feedback':'目前还是一样，依旧条形屏闪后是缓慢屏闪'}}
write('evidence/historical-comparison.json',historical)
reprobe=latest('display-reprobe-status-02')
diagnostic=latest('display-reprobe-service-diagnostic')
reprobe['subsequent_service_check']={k:diagnostic[k] for k in ['boot_id','uptime','units']}
reprobe['subsequent_baseline']=latest('original-baseline-after-manual-power')
reprobe['user_feedback_after_recovery']='仍然存在'
write('evidence/display-reprobe-and-recovery.json',reprobe)
write('evidence/power-baseline.json',latest('hotplug-power-baseline'))
wake=latest('hotplug-wake-once')
assert wake['before']['connector']['dpms']=='Off' and wake['after']['connector']['dpms']=='On'
assert wake['before']['units']==wake['after']['units']
assert wake['before']['edid_bytes']==wake['after']['edid_bytes']==0
assert '\tactive=0\n' in wake['before']['drm_state'] and '\tactive=1\n' in wake['after']['drm_state']
assert any(s.split()[0]=='dp_video_ref' and s.split()[4]=='48999993' and s.split()[-1]=='Y' for s in wake['after']['display_clocks'])
write('evidence/separate-dpms-wake.json',wake)
ready=latest('hdmi-physical-hotplug-v2')
assert ready['before']['cached_after_query']['dpms']=='On'
assert 'enable=1' in ready['before']['scanout'] and 'active=1' in ready['before']['scanout']
write('evidence/new-observation-ready.json',ready)
observation=latest('hotplug-observation-result')
if 'result.json' in observation:
 result=observation['result.json']
 assert result['before']['hashes']==result['after']['hashes']
 assert result['before']['units']==result['after']['units']
 observation['actual_kernel_drm_event_headers']=[s for s in result['events'] if re.match(r'^KERNEL\s*\[',s)]
 observation['monitor_banner_excluded_from_actual_events']=True
write('evidence/current-observation.json',observation)
splitter=latest('splitter-control-inventory')
assert splitter['board_model'].startswith('ZynqMP SMK-K26 Rev1/B/A')
assert splitter['root_compatible'].startswith('xlnx,zynqmp-sk-kv260-rev1')
assert splitter['i2c_adapters']['rc']==0 and 'i2c-1' in splitter['i2c_adapters']['text']
assert not any(d['device'].endswith('-0073') for d in splitter['i2c_clients'])
assert splitter['i2c_transactions_to_splitter']==splitter['gpio_writes']==0
assert not splitter['gpioinfo'].get('text')
write('evidence/splitter-control-inventory.json',splitter)
carrier=latest('carrier-fru-readonly')
assert carrier['device']=='1-0051' and carrier['driver']=='at24'
assert carrier['hardware_writes']==carrier['bus_scan']==0 and carrier['serial_or_mac_emitted'] is False
assert carrier['fields']['product_name']=='SCK-KV-G' and carrier['fields']['revision']=='2'
assert carrier['common_checksum_ok'] and carrier['board_checksum_ok']
write('evidence/carrier-fru-readonly.json',carrier)
identity_records=[]
for record_name,command in [('getinfo',0x40)]+[('getdeviceid'+str(i),0x30) for i in range(8)]:
 result_path=HERE/('gprobe-if02-'+record_name+'-once-result.json')
 raw_path=HERE/('gprobe-if02-'+record_name+'-once.rx')
 value=read(result_path)
 raw=raw_path.read_bytes()
 assert value['request_frames_sent']==1 and value['request_bytes_sent']==4 and value['retries']==0
 assert len(raw)==raw[0] and raw[1]==command and sum(raw)%256==0
 assert value['reply']['checksum_valid'] and hashlib.sha256(raw[2:-1]).hexdigest()==value['reply']['payload_sha256']
 assert all(value[k]==0 for k in ['reset_commands','register_reads_or_writes','spi_flash_reads_or_writes','i2c_transactions','gpio_writes'])
 identity_records.append(value)
identity={'transport':'FTDI interface 02, CDBUS0/1 through U65 to STDP4320 UART (B03 schematic page 9)',
 'mapping_verified_by_visual_schematic_trace':True,'previous_interface_03_mapping_incorrect':True,
 'previous_interface_03_no_reply_not_stdp_evidence':True,
 'requests':identity_records,'request_frames':len(identity_records),
 'request_bytes':sum(v['request_bytes_sent'] for v in identity_records),
 'response_bytes':sum(v['total_rx_bytes'] for v in identity_records),
 'all_replies_validated_from_private_recordings':True,
 'identity_string_semantics_and_application_firmware_version_confirmed':False,
 'identity_strings_do_not_prove_hdmi_output_is_healthy':True,
 'resets_or_register_gpio_flash_writes':0,
 'query_source':'https://github.com/radareorg/radare2/blob/master/libr/io/p/io_gprobe.c',
 'upstream_source_sha256':hashlib.sha256((HERE/'io_gprobe_upstream_reference.c').read_bytes()).hexdigest()}
write('evidence/gprobe-uart-c-readonly.json',identity)
old_query=read(OUT/'evidence/gprobe-getinfo-preflight.json')
old_query.update(result='wrong_interface_no_reply_superseded',transport='FTDI interface 03 (D), not the STDP UART',
 use_as_stdp_probe_evidence=False,
 interpretation='Wrong physical endpoint. B03 page 9 connects STDP UART to CDBUS0/1 (interface 02), where valid GProbe replies were subsequently obtained without reset.')
write('evidence/gprobe-getinfo-preflight.json',old_query)
checkpoints={phase:latest(phase) for phase in ['hdmi-cached-checkpoint-uart-c-correction','hdmi-cached-checkpoint-after-identities']}
write('evidence/current-uart-c-checkpoints.json',{'checkpoints':checkpoints,'board_wallclock_trusted':False,
 'host_capture_times_in_provenance':True,'new_boot_since_prior_hotplug_observation':True,
 'physical_screen_result':'not_reported','note':'First checkpoint On/active; later checkpoint DPMS Off/inactive. No physical intervention is inferred.'})
schematic=Path('/home/ghmd/Win共享文件/tmp/j2_pinout_sources/kv260_b03.pdf')
assert schematic.exists()
path_analysis={
 'carrier_fru':{'product':carrier['fields']['product_name'],'part_number':carrier['fields']['part_number'],'revision':carrier['fields']['revision'],'checksums_valid':carrier['common_checksum_ok'] and carrier['board_checksum_ok'],'full_structure_parser_complete':carrier['board_structure_ok']},
 'schematic_reference':{'local_file':str(schematic),'sha256':hashlib.sha256(schematic.read_bytes()).hexdigest(),'title':'ML Starter Kit Carrier Card','revision':'B03','exact_match_to_fru_revision_proven':False,'host_i2c_7bit_address_label':'0x73','hdmi_controls':['STDP4320_GPIO5_HDMI_OE_B','STDP4320_GPIO6_HDMI_DDC_EN','STDP4320_GPIO7_HDMI_PWR_ON','STDP4320_GPIO8_HDMI_PWR_FLT_B'],'external_spi_flash':['U31','SST25VF020B'],'scope':'design reference; not board-revision proof'},
 'official_linux_source':{'carrier_overlay':'revB includes rev2/rev1 compatible and leaves STDP4320 as a comment, not an I2C client','som_dts_legacy_firmware_addresses':['0x5C','0x5D','0x70','0x72','0x76'],'expected_fixed_firmware_address':'0x73','source':'https://github.com/Xilinx/linux-xlnx/blob/master/arch/arm64/boot/dts/xilinx/zynqmp-sm-k26-revA.dts'},
 'chip_documentation':{'host_interface_registers_exist':True,'register_map_available_in_public_datasheet':False,'firmware_stored_in_external_spi_flash':True,'isp_supported_transport':['UART','I2C','DisplayPort AUX','HDMI DDC'],'isp_tool':'GProbe required; vendor procedure/tool requested','uart_identity_can_be_read_without_reset_measured':True,'source':'https://www.mouser.com/datasheet/2/936/STDP4320_03c-3105399.pdf'},
 'current_runtime':{'registered_0x73_i2c_client':False,'splitter_bus_probe_or_read':False,'splitter_register_write':False,'spi_flash_read_or_write':False,'gpio_write':False,'gprobe_uart_interface':'02','gprobe_identity_replies_valid':True,'application_firmware_version_confirmed':False},
 'conclusion':'Physical hotplug likely changes STDP4320 downstream HPD/DDC/HDMI enable or power state without necessarily changing the upstream DP mode. This is an inference supported by the historical same-boot recovery and design path; actual pin transitions and internal firmware state were not captured.',
 'next_safe_gate':'UART identity communication is now verified without vendor tooling or reset. Obtain the matching status/control register map or a documented HDMI control command before writing anything; continue the independent-screen-power field comparison separately.'}
write('evidence/splitter-path-analysis.json',path_analysis)
field={'last_confirmed_user_state':'条纹仍然存在（源端完整重探测后）',
 'screen_usb_source':'KV260 USB，用户确认位置没变',
 'independent_screen_power_test_performed':False,
 'separate_dpms_wake_physical_result':'awaiting_user',
 'new_physical_hdmi_test_action':'not_confirmed_by_user',
 'new_physical_hdmi_test_result':'awaiting_user',
 'historical_physical_hotplug_recovery_confirmed':True,
 'new_monitoring_is_not_proof_of_physical_action':True,
 'latest_readonly_boot':checkpoints['hdmi-cached-checkpoint-after-identities']['boot_id'],
 'latest_checkpoint_output_dpms':'Off','latest_boot_physical_flicker_result':'not_reported',
 'gprobe_uart_identity_connection_verified':True,
 'independent_power_or_hdmi_action_in_this_continuation_confirmed':False}
write('evidence/field-status.json',field)
for name in ['board_hotplug_wake_once.py','hdmi_physical_hotplug_observer_v2.py','board_hotplug_observation_result.py','hdmi_display_reprobe_once.py','board_hdmi_display_reprobe_launch.py','board_hdmi_display_reprobe_status.py','board_splitter_control_inventory.py','board_carrier_fru_readonly.py','board_stdp_gprobe_getinfo_once.py','board_hdmi_cached_checkpoint.py']:
 shutil.copyfile(HERE/name,OUT/'src'/name)
write('evidence/provenance.json',provenance)
checks={'historical_same_boot_verified':True,'historical_same_service_pids_verified':True,
 'historical_software_cycle_did_not_change_timing':True,
 'dpms_wake_crtc_and_clock_verified':True,
 'current_hotplug_baseline_active_verified':True,
 'new_physical_action_confirmed':False,'physical_flicker_fixed':False,
 'splitter_control_client_registered':False,'splitter_i2c_or_gpio_write_performed':False,
 'carrier_fru_identified_sck_kv_g_revision_2':True,'carrier_fru_checksums_valid':True,
 'carrier_fru_full_field_structure_parser_complete':carrier.get('board_structure_ok') is True,
 'splitter_host_address_and_gpio_pins_found_in_design_reference':path_analysis['schematic_reference']['host_i2c_7bit_address_label']=='0x73',
 'vendor_gprobe_required_for_flash_isp':path_analysis['chip_documentation']['isp_tool']=='GProbe required; vendor procedure/tool requested',
 'correct_uart_c_identity_replies_verified':identity['all_replies_validated_from_private_recordings'],
 'wrong_uart_d_previous_conclusion_superseded':old_query['use_as_stdp_probe_evidence'] is False,
 'current_boot_first_mode_native_1024x600_verified':any('initial mode 1024x600' in s for s in checkpoints['hdmi-cached-checkpoint-after-identities']['xorg_initial_modes']),
 'current_boot_protected_hashes_match_between_checkpoints':len({json.dumps(c['protected_hashes'],sort_keys=True) for c in checkpoints.values()})==1,
 'new_current_boot_latest_output_is_off':list(checkpoints['hdmi-cached-checkpoint-after-identities']['connectors'].values())[0]['dpms']=='Off',
 'source_reprobe_readiness_timeout_preserved':bool(reprobe['result.json'].get('error')),
 'source_reprobe_independent_recovery_verified':reprobe['driver_bound'] and 'ActiveState=inactive' in reprobe['timer'],
 'observation_finished':'result.json' in observation}
for p in (OUT/'src').glob('*.py'):compile(p.read_bytes(),str(p),'exec')
files={str(p.relative_to(OUT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='verification.json'}
write('verification.json',{'generated_utc':datetime.now(timezone.utc).isoformat(),'files':files,**checks})
for name,meta in files.items():
 assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==meta['sha256']
print(json.dumps({'delivery':str(OUT),'verified_files':len(files),'checks':checks},ensure_ascii=False))
