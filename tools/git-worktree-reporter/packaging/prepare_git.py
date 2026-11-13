"""Prepare a separately licensed, hash-pinned Git in a new external directory."""
if not __debug__:raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')
import argparse,hashlib,json,os,stat,subprocess,sys,tarfile,urllib.parse,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='2.56.1'
PINS={
 'win32':dict(filename='MinGit-2.56.1-64-bit.zip',url='https://github.com/git-for-windows/git/releases/download/v2.56.1.windows.1/MinGit-2.56.1-64-bit.zip',sha256='4a92850b6e917da4fd010669b614b55dccf5b0ec333a534cc4be4700dfefdafd',version='git version 2.56.1.windows.1'),
 'linux':dict(filename='git-2.56.1.tar.xz',url='https://www.kernel.org/pub/software/scm/git/git-2.56.1.tar.xz',sha256='f0b0bf89264b9bd2e1c640363e7529643989da76281600473c50745cd34a607f',version='git version 2.56.1')}
FLAGS=['NO_CURL=YesPlease','NO_EXPAT=YesPlease','NO_GETTEXT=YesPlease','NO_TCLTK=YesPlease','NO_PERL=YesPlease','NO_PYTHON=YesPlease']
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
 assert sys.platform in PINS and (sys.platform!='win32' or os.environ.get('PROCESSOR_ARCHITECTURE','').upper()=='AMD64')
 for path in (a.out,a.report):
  assert path.is_absolute() and path.parent.is_dir() and not os.path.lexists(path)
  assert not path.resolve().is_relative_to(ROOT.resolve())
  assert path.parent.resolve()==path.parent and not path.parent.is_symlink() and not getattr(path.parent,'is_junction',lambda:False)()
 pin=PINS[sys.platform];a.out.mkdir();archive=a.out/pin['filename']
 request=urllib.request.Request(pin['url'],headers={'User-Agent':'OUTLANDS-pinned-Git-preparation'})
 with urllib.request.urlopen(request,timeout=60) as response:
  final=urllib.parse.urlsplit(response.url);assert final.scheme=='https' and final.hostname in {'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com','www.kernel.org','kernel.org','cdn.kernel.org'}
  raw=response.read(160_000_001)
 assert len(raw)<=160_000_000 and sha(raw)==pin['sha256'],'PINNED_GIT_ARCHIVE_DIFFERS'
 with archive.open('xb') as out:out.write(raw)
 if sys.platform=='win32':
  install=a.out/'git';install.mkdir()
  with zipfile.ZipFile(archive) as z:
   names=z.namelist();assert len(names)==len(set(names)) and len(names)<20000 and sum(i.file_size for i in z.infolist())<600_000_000
   for i in z.infolist():assert not i.filename.startswith(('/', '\\')) and '..' not in i.filename.split('/') and ':' not in i.filename and '\\' not in i.filename and not stat.S_ISLNK(i.external_attr>>16)
   z.extractall(install)
  executable=install/'ucrt64/bin/git.exe';flags=[]
 else:
  assert ' ' not in str(a.out),'SOURCE_BUILD_REQUIRES_SPACE_FREE_BUILD_PREFIX'
  source=a.out/'source';source.mkdir()
  with tarfile.open(archive,'r:xz') as t:
   members=t.getmembers();assert len(members)<20000 and sum(m.size for m in members)<600_000_000
   assert all(m.name.startswith('git-2.56.1/') or m.name=='git-2.56.1' for m in members)
   t.extractall(source,filter='data')
  install=a.out/'install';flags=FLAGS
  env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','MAKEFLAGS','MFLAGS','CFLAGS','CPPFLAGS','LDFLAGS'))}
  done=subprocess.run(['make','-j2','prefix='+str(install),*flags,'install'],cwd=source/'git-2.56.1',env=env,capture_output=True,timeout=900)
  (a.out/'build-private.log').write_bytes(done.stdout+done.stderr)
  assert done.returncode==0,'PINNED_GIT_SOURCE_BUILD_FAILED'
  executable=install/'bin/git'
 assert executable.is_file() and not executable.is_symlink() and not getattr(executable,'is_junction',lambda:False)()
 version=subprocess.check_output([str(executable),'--version'],timeout=15,text=True).strip();assert version==pin['version']
 digest=sha(executable.read_bytes())
 if sys.platform=='win32':assert digest=='9bf8ee81d79f38a11eaf7799499a634c46a718e009a4a9b2b20b115804643302'
 value=dict(schema=1,platform=sys.platform,version=version,archive=pin,executable_relative=executable.relative_to(a.out).as_posix(),executable_sha256=digest,build_flags=flags,preparation_helper_sha256=sha(Path(__file__).read_bytes()),binary_reproducibility_claimed=False,global_install_performed=False)
 with a.report.open('x',encoding='utf-8',newline='\n') as out:out.write(json.dumps(value,indent=2)+'\n')
 print(json.dumps(value))
if __name__=='__main__':main()
