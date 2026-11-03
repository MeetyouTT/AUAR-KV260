"""Archive safety fixtures only; no compilation, installation or native load."""
import tarfile

import pytest

from build_webrtcvad_isolated import SOURCE_PROFILES, checked_archive_members


def member(name,kind=tarfile.REGTYPE):
    item = tarfile.TarInfo(name); item.type = kind; item.size = 1 if kind == tarfile.REGTYPE else 0
    return item


@pytest.mark.parametrize('version',['2.0.14','2.0.10'])
def test_only_selected_release_root_is_accepted(version):
    root = SOURCE_PROFILES[version]['tar_root']
    entries = [member(root,tarfile.DIRTYPE),member(root+'/setup.py'),member(root+'/webrtcvad.py')]
    assert checked_archive_members(entries,root) == entries
    other = SOURCE_PROFILES['2.0.10' if version == '2.0.14' else '2.0.14']['tar_root']
    with pytest.raises(ValueError,match='layout'):
        checked_archive_members([member(other+'/setup.py')],root)


@pytest.mark.parametrize('name,kind',[
    ('/absolute/setup.py',tarfile.REGTYPE),
    ('webrtcvad_wheels-2.0.14/../outside.py',tarfile.REGTYPE),
    ('webrtcvad_wheels-2.0.14/sub/./same.py',tarfile.REGTYPE),
    ('webrtcvad_wheels-2.0.14/link',tarfile.SYMTYPE),
    ('webrtcvad_wheels-2.0.14/hardlink',tarfile.LNKTYPE),
    ('webrtcvad_wheels-2.0.14/device',tarfile.CHRTYPE),
])
def test_archive_cannot_escape_alias_or_create_links_and_devices(name,kind):
    with pytest.raises(ValueError,match='layout'):
        checked_archive_members([member(name,kind)],SOURCE_PROFILES['2.0.14']['tar_root'])


def test_archive_duplicate_and_extraction_size_are_rejected():
    root = SOURCE_PROFILES['2.0.14']['tar_root']
    with pytest.raises(ValueError,match='layout'):
        checked_archive_members([member(root+'/setup.py'),member(root+'/setup.py')],root)
    huge = member(root+'/huge'); huge.size = 16*1024*1024+1
    with pytest.raises(ValueError,match='size'):
        checked_archive_members([huge],root)
