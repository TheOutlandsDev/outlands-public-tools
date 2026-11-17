from pathlib import Path
import py_compile, subprocess, sys
root = Path(__file__).resolve().parent
target = root / 'Vern_Analyze_v2.py'
py_compile.compile(str(target), doraise=True)
proc = subprocess.run([sys.executable, str(target), '--help'], capture_output=True, text=True)
print('syntax_ok', True)
print('help_rc', proc.returncode)
text = target.read_text(encoding='utf-8')
print('has_rev3b_gate', 'rev3b_build_sampling_groups' in text)
print('has_qc_summary', 'print_rev3b_qc_summary' in text)
