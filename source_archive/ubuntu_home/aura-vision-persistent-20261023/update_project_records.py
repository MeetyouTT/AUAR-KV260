"""Append this completed stage to Ubuntu-owned project/handoff records."""
from pathlib import Path

SHARED=Path('/home/ghmd/Win共享文件')
MARKER='<!-- persistent-vision-recovery-final-20261023 -->'
NOTES=[
    (SHARED/'后续任务_先读这里.md',
     '**最新已持久启用视觉恢复与准入修复：** [当前版本、4源补丁、验证与回退](语音共享文件/deliverables/2026-10-23_vision_recovery_and_admission/README.md)。camera29563/GUI29588/X1077、boot008f3e1b…、原unit297…保持，新增持久camera覆盖。SFace独立10s冷却/2轮600s/3次探测、前两Deferred；optional至少30ms预算＋5ms guard准入。237软件0失败/2私有ELF跳过，最终68板隔离与60秒9.966/3.897Hz通过。两次真实YuNet33.68/32.96ms硬超限均同进程自动恢复、故障保留；第二次直接证实native中14.01ms CPU排队与GIL重获8.42ms睡眠叠加，长尾尚未根治。最新约5万调用/2故障2恢复/gap0，约112分钟快照间无新增。CPU48.55%/DPU任务busy4.93%为15秒点测，SFace新增请求0。GUI175源/身份配置库保持、回退核对过，探针/统计清理、nice回0。真人恢复/精度、实际冷启与持续交互仍待验，Windows接收未代填。下方临时版本和旧boot停用状态属于历史阶段。'),
    (SHARED/'协作任务/2026-10-18_双机联调/Ubuntu_执行回执.md',
     '**2026-10-23视觉恢复/准入已持久启用（UTC10-24最终续查）：** [源码、163条SHA与完整实证](../../语音共享文件/deliverables/2026-10-23_vision_recovery_and_admission/README.md)。最新单终端约束后由root串行完成。SFace独立受限恢复、30ms保守准入/5ms guard、boot/重启保护承接及持久覆盖/回退落地；4源变更，原模型/库/阈值/硬cap保持。当前camera29563/GUI29588/X1077，原unit297…，持久覆盖zzzz-aura-vision-recovery-c76110abefc304bb.conf。237软件0失败/2跳过、68板隔离及60秒YOLO9.966/face3.897Hz通过，业务窗0新增超限/gap/USB，startup primary+1另记。两次实际YuNet33.678/32.964ms hardcap-only均自动恢复；第二次native16.239ms含14.006ms runqueue，GIL重获8.698ms含8.415ms睡眠，wait native0.009ms。当前约5万调用/fault2 recovery2/gap0，6739秒同PID计数续查无新增；SFace新增0、真实恢复与精度未验。资源CPU48.55%、DPU busy4.934%为非配对点测。Nice短试收益不稳定已回0，probe/instance/timer及CU统计清理、GUI175源/配置/库与回退检查通过。外部新boot原因未知且非本轮发起、旧boot拒绝传输和3次版本切换均留档。164文件/163SHA、97Python AST/44JSON核验，无权重/ELF/UART/生物数据共享。Windows回执未改；后续集成以本包4源和持久覆盖为基线。'),
    (Path('/home/ghmd/AMD_Smart/PROJECT_BOOK_INDEX.md'),
     '2026-10-23[视觉受限恢复、保守准入与持久启用](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_vision_recovery_and_admission/README.md)：camera29563/GUI29588、boot008f3e1b…、原unit297…保持，4源修复持久保留。237软件0失败/2跳过、68板隔离与60秒9.966/3.897Hz通过；两次真实YuNet超限均自动恢复，第二次证实CPU排队与GIL重获睡眠叠加，长尾未根治。最新约5万调用/2fault2recovery/gap0，112分钟计数续查无新增。CPU48.55/DPU busy4.93为点测，SFace新增0；真人恢复/精度/冷启/持续交互待验。163SHA/164文件封存、探针和统计清理过；[日志](logs/daily/2026-10-23-VISION-RECOVERY-ADMISSION-PERSISTENT.md)。'),
    (Path('/home/ghmd/AMD_Smart/plan/active/2026-10-21-BOARD-CPU-DPU-COOPERATIVE-PRIORITY.md'),
     '**2026-10-23恢复/准入持久版已启用：** [源码/实测/回退](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_vision_recovery_and_admission/README.md)。camera29563/GUI29588；SFace受限恢复/前两探测不发布、30ms预算＋5ms guard准入、worker前保护交接和新boot独立窗口已完成。4源/237软件0失败2跳过/68板隔离，60秒YOLO9.966/face3.897Hz通过；原unit/GUI/库/模型/阈值保持。真实两次YuNet硬超限均已自动恢复，CPU runnable排队与GIL重获睡眠会叠加，尚未完全根治。Nice未获稳定收益已回默认，所有探针/统计已清理。下一顺序：真人SFace恢复门复验→实际冷启→陌生人/多人精度和持续真实交互→匹配负载的CPU/调度收益；保持30ms/5ms/TTL，资源点测和SFace ready不代替满负载验收。')
]

def main():
    for path,note in NOTES:
        content=path.read_text();assert MARKER not in content
        head,tail=content.split('\n',1)
        path.write_text(head+'\n\n'+MARKER+'\n'+note+'\n<!-- /persistent-vision-recovery-final-20261023 -->\n'+tail)
    progress=SHARED/'协作任务/2026-10-18_双机联调/SFace受限恢复_执行状态_20261023.md'
    content=progress.read_text();head,tail=content.split('\n',1)
    note='**最终更新：恢复、准入与持久启用均已接受，当前camera29563/GUI29588。** 完整源码、163条SHA和真实故障/自动恢复见[最终交付](../../语音共享文件/deliverables/2026-10-23_vision_recovery_and_admission/README.md)。同新进程2次硬超限均恢复，约112分钟后续计数无新增；SFace仍0新请求，真人恢复/精度和实际冷启未验。最新状态以包内CURRENT_STATE与final-audit为准。'
    progress.write_text(head+'\n\n'+note+'\n\n## 以下为22:30时的历史阶段记录\n'+tail)
    print('Updated shared entry, Ubuntu receipt, project index, active plan and stage note.')

if __name__=='__main__':main()
