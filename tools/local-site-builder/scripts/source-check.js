// Exact source inventory gate. Original MIT code; no private/runtime files read.
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const ROOT=path.resolve(__dirname,'..');
const NAMES=[
  '.gitattributes','.gitignore','.npmrc','.github/ISSUE_TEMPLATE/bug_report.yml',
  '.github/ISSUE_TEMPLATE/feature_request.yml','.github/workflows/checks.yml',
  'LICENSE','README.md','CHANGELOG.md','CONTRIBUTING.md','SECURITY.md','THIRD-PARTY-NOTICES.txt',
  'package.json','package-lock.json','server.js','admin/admin.html','admin/admin.css','admin/admin.js',
  'assets/logo.svg','content/brand.js','content/starter-pages.js','views/render.js',
  'lib/safety.js','lib/backup.js','scripts/setup.js','scripts/backup.js','scripts/export.js',
  'scripts/source-check.js','tests/app.test.js','docs/PROVENANCE.md','docs/VALIDATION.md',
  'docs/DEPENDENCIES.json','examples/WORKSHOP.md'
].sort();
const IGNORED=new Set(['node_modules','data','backups','.git','coverage','test-results','playwright-report']);
function sha(data){return crypto.createHash('sha256').update(data).digest('hex');}
function inventory(){
  const found=[];
  function walk(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){
    if(IGNORED.has(entry.name)||entry.name==='.env'||entry.name.startsWith('.env.'))continue;
    const full=path.join(dir,entry.name),name=path.relative(ROOT,full).split(path.sep).join('/');
    if(entry.isSymbolicLink())throw new Error('Linked source path: '+name);
    if(entry.isDirectory())walk(full);else if(name!=='SOURCE-MANIFEST.json')found.push(name);
  }}walk(ROOT);
  if(JSON.stringify(found.sort())!==JSON.stringify(NAMES))throw new Error('Source list differs from the explicit reviewed allowlist.');
  const rows=[];
  for(const name of NAMES){
    const full=path.join(ROOT,...name.split('/'));
    if(fs.realpathSync(full).toLowerCase()!==full.toLowerCase())throw new Error('Linked source: '+name);
    const data=fs.readFileSync(full);if(data.length>1024*1024||data.includes(0))throw new Error('Unsupported source payload: '+name);
    const text=new TextDecoder('utf-8',{fatal:true}).decode(data);
    if(/(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|[A-Za-z]:[\\/]Users[\\/])/.test(text))throw new Error('Private-source indicator: '+name);
    if(text.toLowerCase().includes(['pure','mama','thyme'].join('')+'.com'))throw new Error('Private brand domain: '+name);
    if(name.endsWith('.js')){const result=spawnSync(process.execPath,['--check',full],{encoding:'utf8'});if(result.status!==0)throw new Error('Syntax error: '+name);}
    if(name.endsWith('.json'))JSON.parse(text);
    if(name.endsWith('.md'))for(const match of text.matchAll(/\]\(([^)]+)\)/g)){
      const target=match[1];if(/^(https?:|#)/.test(target))continue;
      const resolved=path.resolve(path.dirname(full),target.split('#')[0]);
      if(!resolved.startsWith(ROOT+path.sep)||!fs.existsSync(resolved))throw new Error('Broken local doc link: '+name);
    }
    rows.push({path:name,bytes:data.length,sha256:sha(data)});
  }
  return rows;
}
function main(){
  if(process.argv.length>3||process.argv[2]&&!['--write-manifest'].includes(process.argv[2]))throw new Error('Unknown source-check option.');
  const rows=inventory(),manifest=path.join(ROOT,'SOURCE-MANIFEST.json');
  if(process.argv[2]==='--write-manifest')fs.writeFileSync(manifest,JSON.stringify({schema:1,original_source_license:'MIT',files:rows},null,2)+'\n');
  const saved=JSON.parse(fs.readFileSync(manifest,'utf8'));
  if(saved.schema!==1||saved.original_source_license!=='MIT'||JSON.stringify(saved.files)!==JSON.stringify(rows))throw new Error('Source manifest differs from reviewed bytes.');
  console.log(JSON.stringify({status:'PASS',source_files:rows.length,bytes:rows.reduce((n,x)=>n+x.bytes,0),runtime_payloads:0}));
}
if(require.main===module){try{main();}catch(error){console.error(error.message);process.exitCode=1;}}
module.exports={inventory};
