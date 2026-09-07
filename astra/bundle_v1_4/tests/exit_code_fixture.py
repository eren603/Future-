"""TEST FIXTURE ONLY: exits non-zero after writing a declared code to stderr."""
import sys

sys.stdin.buffer.read()
sys.stderr.write((sys.argv[1] if len(sys.argv) > 1 else "SOME_CODE") + "\ndetail line\n")
raise SystemExit(2)
