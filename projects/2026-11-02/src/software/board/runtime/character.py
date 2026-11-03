"""Selected public character; user identities and archived voice text stay exact."""
from common.character_profile import selected_profile

_PROFILE = selected_profile()
CHARACTER_NAME = _PROFILE.display_name
CHARACTER_DESCRIPTION = _PROFILE.description
ADDRESS_NAMES = _PROFILE.address_names
ASR_ALIASES = _PROFILE.asr_aliases
GREETING = _PROFILE.greeting

DEMO_LINES = (
    {'id':'greeting','label':CHARACTER_NAME+'问候','text':GREETING,'emotion':'friendly','action':''},
    {'id':'happy','label':'开心回应','text':'太好了，这次终于跑通啦！我们又往前走了一步！','emotion':'happy','action':'ack_nod'},
    {'id':'gentle','label':'轻声安慰','text':'没关系，我会在这里陪你。我们慢慢来，一起把问题解决。','emotion':'sad','action':''},
    {'id':'explanation','label':'长句演示','text':'我正在检查我们的项目。现在可以实时切换表情，也可以随时打断我。说话时，嘴部会随着声音自然开合，眨眼也会独立运行。','emotion':'neutral','action':''},
)
