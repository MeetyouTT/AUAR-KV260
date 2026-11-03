"""Current character identity; archival voice-reference transcripts stay exact."""
CHARACTER_NAME = '汐蓝'
CHARACTER_DESCRIPTION = 'DeepSeek 鲸鱼娘'
GREETING = '你好呀，我是汐蓝。很高兴见到你，今天想聊点什么？'

DEMO_LINES = (
    {'id':'greeting','label':'汐蓝问候','text':GREETING,'emotion':'friendly','action':''},
    {'id':'happy','label':'开心回应','text':'太好了，这次终于跑通啦！我们又往前走了一步！','emotion':'happy','action':'ack_nod'},
    {'id':'gentle','label':'轻声安慰','text':'没关系，我会在这里陪你。我们慢慢来，一起把问题解决。','emotion':'sad','action':''},
    {'id':'explanation','label':'长句演示','text':'我正在检查我们的项目。现在可以实时切换表情，也可以随时打断我。说话时，嘴部会随着声音自然开合，眨眼也会独立运行。','emotion':'neutral','action':''},
)
