from pathlib import Path
import importlib.util
import subprocess
import sys

SKILL = Path('C:/Users/uuh56/.codex/plugins/cache/openai-primary-runtime/documents/26.905.11957/skills/documents')
spec = importlib.util.spec_from_file_location('canonical_docx_renderer', SKILL / 'render_docx.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
POPPLER = 'C:/Users/uuh56/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin'
native_script = Path(__file__).with_name('export_word.ps1')

def native_word_conversion(doc_path, user_profile, convert_tmp_dir, stem, verbose):
    pdf_path = str(Path(convert_tmp_dir) / (stem + '.pdf'))
    proc = subprocess.run([
        'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(native_script),
        '-SourcePath', str(Path(doc_path).resolve()), '-PdfPath', pdf_path,
    ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
    if proc.returncode != 0:
        return '', proc.stdout + proc.stderr
    print(proc.stdout.strip(), flush=True)
    return pdf_path, 'Microsoft Word native PDF export; no LibreOffice used'

original_convert = renderer.convert_from_path
def bundled_raster(*args, **kwargs):
    kwargs['poppler_path'] = POPPLER
    return original_convert(*args, **kwargs)

renderer.convert_to_pdf = native_word_conversion
renderer.convert_from_path = bundled_raster
renderer.main()
