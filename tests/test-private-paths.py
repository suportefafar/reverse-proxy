#!/usr/bin/env python3
"""Exercise the production security snippet against real Caddy routing."""
from pathlib import Path
import subprocess, tempfile, urllib.request, urllib.error, json, time
source=Path(__file__).resolve().parents[1]/'web-server/Caddyfile.olympus.prod'
snippet=source.read_text().split('(securityHeaders) {',1)[1].split('\n(siteLogs)',1)[0]
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp);root.chmod(0o755)
 config=root/'Caddyfile';config.write_text('(securityHeaders) {'+snippet+'\n:80 {\n import securityHeaders\n respond "public route" 200\n}\n')
 run=lambda *a:subprocess.check_output(['docker',*a],text=True).strip()
 cid=run('run','-d','--rm','-p','127.0.0.1::80','--mount',f'type=bind,source={config},target=/etc/caddy/Caddyfile,readonly','--entrypoint','caddy','olympus-reverse-proxy','run','--config','/etc/caddy/Caddyfile','--adapter','caddyfile')
 try:
  info=json.loads(run('inspect',cid))[0];base='http://127.0.0.1:'+info['NetworkSettings']['Ports']['80/tcp'][0]['HostPort']
  def status(path):
   try:return urllib.request.urlopen(base+path,timeout=3).status
   except urllib.error.HTTPError as e:return e.code
  for _ in range(40):
   try:status('/');break
   except (urllib.error.URLError,ConnectionError):time.sleep(.1)
  for path in ['/.git/HEAD','/wp-content/plugins/custom/.git/config','/.GIT/HEAD','/%2egit/HEAD','/.env','/nested/.env.production','/wp-config.php.bak','/.htaccess','/wp-content/.svn/entries']:
   assert status(path)==404,path
  for path in ['/','/cemed-2/','/wp-json/','/assets/git.svg','/wp-content/uploads/document.pdf']:
   assert status(path)==200,path
  print('PASS: private paths, encoded and nested paths denied; public routes preserved')
 finally:run('rm','-f',cid)
