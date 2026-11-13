"""Build pinned Expat into matching pyexpat in a new owned standalone Python."""
if not __debug__:raise RuntimeError('OPTIMIZED_PYTHON_UNSUPPORTED')
import argparse,hashlib,json,os,platform,re,subprocess,sys,tarfile,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FACTS="""import hashlib,json,sys,sysconfig,pyexpat
from pathlib import Path
from xml.parsers import expat
assert pyexpat.version_info==expat.version_info
p=expat.ParserCreate();p.Parse(b'<svg/>',True)
print(json.dumps(dict(python=sys.version.split()[0],expat_version=list(expat.version_info),expat_version_text=expat.EXPAT_VERSION,executable_sha256=hashlib.sha256(Path(sys._base_executable).read_bytes()).hexdigest(),pyexpat_sha256=hashlib.sha256(Path(pyexpat.__file__).read_bytes()).hexdigest(),pyexpat_file=str(Path(pyexpat.__file__).resolve()),include=sysconfig.get_paths()['include'],suffix=sysconfig.get_config_var('EXT_SUFFIX'))))
"""
def sha(raw):return hashlib.sha256(raw).hexdigest()
def run(command,cwd,log,timeout=600):
 env={k:v for k,v in os.environ.items() if not k.upper().startswith(('PYTHON','PIP_')) and k.upper() not in {'LD_LIBRARY_PATH','DYLD_LIBRARY_PATH','DYLD_FALLBACK_LIBRARY_PATH'}};env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
 done=subprocess.run(command,cwd=cwd,env=env,capture_output=True,timeout=timeout)
 with log.open('xb') as out:out.write(done.stdout+done.stderr)
 assert done.returncode==0,'RUNTIME_PREPARATION_CHILD_FAILED'
 return done.stdout
def download(row,parent,folder):
 request=urllib.request.Request(row['url'],headers={'User-Agent':'OUTLANDS-pinned-parser-preparation'})
 with urllib.request.urlopen(request,timeout=60) as response:
  u=urllib.parse.urlsplit(response.url);assert u.scheme=='https' and u.hostname in {'github.com','www.python.org','python.org','release-assets.githubusercontent.com','objects.githubusercontent.com'}
  raw=response.read(row['bytes']+1)
 assert len(raw)==row['bytes'] and sha(raw)==row['sha256'],'PINNED_SOURCE_OR_PYTHON_DIFFERS'
 archive=parent/row['filename']
 with archive.open('xb') as out:out.write(raw)
 folder.mkdir()
 with tarfile.open(archive,'r:*') as t:
  members=t.getmembers();assert len(members)<60000 and sum(m.size for m in members)<1_500_000_000
  t.extractall(folder,filter='data')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--minor',required=True,choices=['3.12','3.13','3.14','3.15']);p.add_argument('--out',required=True,type=Path);p.add_argument('--report',required=True,type=Path);a=p.parse_args()
 assert sys.platform in {'win32','linux'} and platform.machine().lower() in {'amd64','x86_64'},'X86_64_RUNTIME_REQUIRED'
 for path in (a.out,a.report):
  assert path.is_absolute() and path.parent.is_dir() and not os.path.lexists(path)
  assert path.parent.resolve()==path.parent and not path.parent.is_symlink() and not getattr(path.parent,'is_junction',lambda:False)()
  assert not path.resolve().is_relative_to(ROOT.resolve())
 lock=json.loads((ROOT/'RUNTIME-LOCK.json').read_text());assert lock['schema']==1 and lock['expat_version']==[2,10,0]
 pin=lock['python_archives'][sys.platform][a.minor];cpy=lock['cpython_sources'][a.minor];expat=lock['expat_source'];a.out.mkdir()
 download(pin,a.out,a.out/'distribution');download(cpy,a.out,a.out/'cpython-source');download(expat,a.out,a.out/'expat-source')
 base=a.out/'distribution/python';python=base/('python.exe' if os.name=='nt' else 'bin/python'+a.minor);python=python.resolve();assert python.is_relative_to(base.resolve())
 original=json.loads(run([str(python),'-I','-B','-c',FACTS],a.out,a.out/'original-parser-private.log',30));assert original['python']==pin['python']
 target=Path(original['pyexpat_file']);assert target.resolve().is_relative_to(base.resolve()) and target.is_file() and not target.is_symlink()
 include=Path(original['include']);assert include.resolve().is_relative_to(base.resolve()) and include.is_dir()
 recipe=ROOT/'packaging/expat-overlay';build=a.out/'native-build';source_cpy=a.out/'cpython-source'/('Python-'+pin['python']);source_expat=a.out/'expat-source/expat-2.10.0'
 cmake_version=subprocess.check_output(['cmake','--version'],text=True,timeout=20).splitlines()[0]
 command=['cmake','-S',str(recipe),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DPY_ROOT='+str(base),'-DPY_INCLUDE='+str(include),'-DCPY_SOURCE='+str(source_cpy),'-DEXPAT_SOURCE='+str(source_expat),'-DPY_DIGITS='+a.minor.replace('.',''),'-DPY_SUFFIX='+original['suffix']]
 generator='Unix Makefiles'
 if os.name=='nt':
  vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
  assert vswhere.is_file() and not vswhere.is_symlink(),'EXISTING_VISUAL_STUDIO_REQUIRED'
  version=subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationVersion'],text=True,timeout=20).strip()
  assert re.fullmatch(r'(17|18)\.[0-9.]+',version),'SUPPORTED_EXISTING_VISUAL_STUDIO_REQUIRED'
  generator={'17':'Visual Studio 17 2022','18':'Visual Studio 18 2026'}[version.split('.')[0]]
 command+=['-G',generator]
 if os.name=='nt':command+=['-A','x64']
 run(command,a.out,a.out/'configure-private.log');run(['cmake','--build',str(build),'--config','Release','--target','pyexpat','--parallel','2'],a.out,a.out/'build-private.log')
 built=build/'Release/pyexpat.pyd' if os.name=='nt' else build/('pyexpat'+original['suffix']);assert built.is_file() and not built.is_symlink()
 backup=a.out/'original-pyexpat.bin'
 with backup.open('xb') as out:out.write(target.read_bytes())
 assert sha(backup.read_bytes())==original['pyexpat_sha256'];target.write_bytes(built.read_bytes())
 current=json.loads(run([str(python),'-I','-B','-c',FACTS],a.out,a.out/'updated-parser-private.log',30))
 assert current['expat_version']==lock['expat_version'] and current['python']==original['python'] and current['executable_sha256']==original['executable_sha256']
 assert current['pyexpat_sha256']==sha(built.read_bytes())==sha(target.read_bytes())
 compiler_files=list((build/'CMakeFiles').glob('*/CMakeCCompiler.cmake'));assert len(compiler_files)==1;compiler=compiler_files[0].read_text()
 def compiler_value(key):
  found=re.findall(r'set\('+re.escape(key)+r' "([^"]+)"\)',compiler);assert len(found)==1;return found[0]
 python_pin={k:current[k] for k in ('python','expat_version','expat_version_text','executable_sha256','pyexpat_sha256')};python_pin.update(actual_parser_import_verified=True,bytes_unchanged=True)
 value=dict(schema=1,platform=sys.platform,minor=a.minor,build_release=lock['build_release'],archives=dict(python=pin,cpython_source=cpy,expat_source=expat),python_pin=python_pin,original_expat_version=original['expat_version'],original_pyexpat_sha256=original['pyexpat_sha256'],executable_relative=python.relative_to(a.out).as_posix(),pyexpat_relative=target.relative_to(a.out).as_posix(),toolchain=dict(cmake=cmake_version,generator=generator,compiler_id=compiler_value('CMAKE_C_COMPILER_ID'),compiler_version=compiler_value('CMAKE_C_COMPILER_VERSION')),preparation_helper_sha256=sha(Path(__file__).read_bytes()),recipe_sha256=sha((recipe/'CMakeLists.txt').read_bytes()),lock_sha256=sha((ROOT/'RUNTIME-LOCK.json').read_bytes()),runtime_update='matching CPython pyexpat.c plus static Expat 2.10.0',original_extension_backed_up=True,global_install_performed=False,binary_reproducibility_claimed=False)
 with a.report.open('x',encoding='utf-8',newline='\n') as out:out.write(json.dumps(value,indent=2)+'\n')
 print(json.dumps(value))
if __name__=='__main__':main()
