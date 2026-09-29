"""Run the unchanged capture protocol through system curl's local-network access."""
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
sys.path.insert(0,str(Path('benchmarks/accuracy').resolve()))
import capture

class SystemCurl:
    def open(self, request, timeout=30):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'body'
            command=['/usr/bin/curl','--noproxy','*','--silent','--show-error',
                     '--max-time',str(timeout),'--max-filesize',str(capture.LIMIT),
                     '--output',str(output),'--write-out','%{http_code}']
            if request.data is not None:
                command += ['--header','Content-Type: application/x-www-form-urlencoded','--data-binary','@-']
            command += [request.full_url]
            result=subprocess.run(command,input=request.data,capture_output=True)
            if result.returncode:
                raise urllib.error.URLError(result.stderr.decode(errors='replace'))
            code=int(result.stdout)
            if code != 200:
                raise urllib.error.HTTPError(request.full_url,code,'System curl HTTP response',{},None)
            return io.BytesIO(output.read_bytes())

urllib.request.build_opener=lambda *args:SystemCurl()
capture.main()
