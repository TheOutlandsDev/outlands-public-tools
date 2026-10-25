// Original offline backup and new-directory recovery. MIT.
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const Database=require('better-sqlite3');
const {plainAncestors,lock}=require('./safety');
const MAX_FILES=5000,MAX_BYTES=512*1024*1024;
function digest(data){return crypto.createHash('sha256').update(data).digest('hex');}
function portable(name){
  if(typeof name!=='string'||name.length>240||!name.split('/').every(x=>/^[a-zA-Z0-9_. -]+$/.test(x)&&x!=='.'&&x!=='..'&&!/[. ]$/.test(x)&&! /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)/i.test(x)))throw new Error('Unsupported backup member path.');
  if(!['db','uploads','site','logs'].includes(name.split('/')[0]))throw new Error('Unexpected backup member.');
}
function list(root){
  const files=[];let bytes=0;
  function visit(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){
    const p=path.join(dir,entry.name);plainAncestors(p);const stat=fs.lstatSync(p);
    if(stat.isDirectory())visit(p);
    else if(stat.isFile()){
      const name=path.relative(root,p).split(path.sep).join('/');portable(name);
      bytes+=stat.size;if(bytes>MAX_BYTES||files.length>=MAX_FILES||stat.size>64*1024*1024)throw new Error('Backup limits exceeded.');
      files.push({name,p,stat});
    }else throw new Error('Special files cannot be backed up.');
  }}
  for(const dir of ['db','uploads','site','logs'])if(fs.existsSync(path.join(root,dir)))visit(path.join(root,dir));
  return files.sort((a,b)=>a.name.localeCompare(b.name));
}
function readStable(file){
  plainAncestors(file.p);
  const data=fs.readFileSync(file.p);const now=fs.lstatSync(file.p);
  if(data.length!==file.stat.size||now.size!==file.stat.size||now.mtimeMs!==file.stat.mtimeMs||now.ino!==file.stat.ino)throw new Error('Backup input changed.');
  return data;
}
function newOutside(destination,source){
  const target=plainAncestors(destination),origin=plainAncestors(source);
  const rel=path.relative(origin,target);
  if(rel===''||(!rel.startsWith('..'+path.sep)&&rel!=='..'&&!path.isAbsolute(rel)))throw new Error('Choose an output outside the input.');
  if(fs.existsSync(target))throw new Error('Output already exists; choose a new directory.');
  if(!fs.statSync(path.dirname(target)).isDirectory())throw new Error('Output parent must exist.');
  return target;
}
function checkDb(file){const db=new Database(file,{readonly:true,fileMustExist:true});try{if(db.pragma('integrity_check',{simple:true})!=='ok')throw new Error('SQLite integrity check failed.');}finally{db.close();}}
async function backup(root,output){
  root=plainAncestors(root);const target=newOutside(output,root);
  if(!fs.existsSync(path.join(root,'db/site.sqlite')))throw new Error('No site database to back up.');
  const release=lock(root);
  try{
    const files=list(root);
    if(files.some(file=>file.name.endsWith('.sqlite-wal')&&file.stat.size>0))throw new Error('Uncheckpointed SQLite journal: start the editor and stop it cleanly before backup.');
    fs.mkdirSync(target,{mode:0o700});const records=[];
    for(const file of files){
      const dest=path.join(target,...file.name.split('/'));fs.mkdirSync(path.dirname(dest),{recursive:true});
      if(file.name==='db/site.sqlite'){
        // The stopped editor has checkpointed WAL. Copy stable bytes without opening
        // or modifying the input DB; finalize only the exclusively created snapshot.
        fs.writeFileSync(dest,readStable(file),{flag:'wx',mode:0o600});
        const snapshot=new Database(dest,{fileMustExist:true});
        try{snapshot.pragma('journal_mode = DELETE');}finally{snapshot.close();}
        checkDb(dest);
      }else if(/\.sqlite-(wal|shm)$/.test(file.name))continue;
      else fs.writeFileSync(dest,readStable(file),{flag:'wx',mode:0o600});
      const data=fs.readFileSync(dest);records.push({path:file.name,bytes:data.length,sha256:digest(data)});
    }
    const manifest={schema:'outlands-site-backup/1',created:new Date().toISOString(),credentials_included:false,files:records};
    fs.writeFileSync(path.join(target,'manifest.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx',mode:0o600});
    verify(target);return {status:'verified',files:records.length};
  }finally{release();}
}
function verify(root){
  root=plainAncestors(root);const manifestPath=path.join(root,'manifest.json');plainAncestors(manifestPath);
  if(fs.statSync(manifestPath).size>2*1024*1024)throw new Error('Manifest too large.');
  const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
  if(manifest.schema!=='outlands-site-backup/1'||manifest.credentials_included!==false||!Array.isArray(manifest.files)||manifest.files.length>MAX_FILES)throw new Error('Invalid backup manifest.');
  const actual=list(root);if(actual.length!==manifest.files.length)throw new Error('Backup inventory differs.');
  if(fs.readdirSync(root).some(x=>!['manifest.json','db','uploads','site','logs'].includes(x)))throw new Error('Unexpected backup root member.');
  const seen=new Set();
  for(const row of manifest.files){
    portable(row.path);const key=row.path.toLowerCase();if(seen.has(key))throw new Error('Duplicate backup member.');seen.add(key);
    if(!Number.isSafeInteger(row.bytes)||row.bytes<0||!/^[a-f0-9]{64}$/.test(row.sha256))throw new Error('Invalid backup record.');
    const file=actual.find(x=>x.name===row.path);if(!file)throw new Error('Backup member missing.');
    const data=readStable(file);if(data.length!==row.bytes||digest(data)!==row.sha256)throw new Error('Backup member checksum differs.');
  }
  if(!seen.has('db/site.sqlite'))throw new Error('Site database is missing.');
  checkDb(path.join(root,'db/site.sqlite'));return manifest;
}
function restore(backupRoot,output){
  const manifest=verify(backupRoot),target=newOutside(output,backupRoot);
  fs.mkdirSync(target,{mode:0o700});
  for(const row of manifest.files){
    const source=path.join(backupRoot,...row.path.split('/'));plainAncestors(source);
    const data=fs.readFileSync(source);if(data.length!==row.bytes||digest(data)!==row.sha256)throw new Error('Backup changed during restore.');
    const dest=path.join(target,...row.path.split('/'));fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,data,{flag:'wx',mode:0o600});
  }
  checkDb(path.join(target,'db/site.sqlite'));return {status:'restored',files:manifest.files.length};
}
module.exports={backup,verify,restore};
