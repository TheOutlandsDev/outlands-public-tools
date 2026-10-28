// Portable wrapper only; original application source is unchanged. MIT.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {fork,spawn}=require('node:child_process');
const ROOT=__dirname,APP=path.join(ROOT,'application');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function outside(folder){
  if(!path.isAbsolute(folder))throw Error('Choose an absolute local path.');
  const {plainAncestors}=require('./application/lib/safety');const full=plainAncestors(folder),rel=path.relative(ROOT,full);
  if(!rel||(!rel.startsWith('..'+path.sep)&&rel!=='..'&&!path.isAbsolute(rel)))throw Error('Private storage must be outside the extracted application.');
  return full;
}
function health(){
  if(process.platform!=='win32'||process.arch!=='x64'||process.versions.node!=='24.22.2'||path.resolve(process.execPath).toLowerCase()!==path.join(ROOT,'runtime/node.exe').toLowerCase())throw Error('Use the bundled Windows x64 launcher.');
  const manifest=JSON.parse(fs.readFileSync(path.join(ROOT,'PACKAGE-MANIFEST.json'))),seen=new Set();
  for(const row of manifest.files){
    if(!row.path||row.path.split('/').some(x=>!x||x==='..'||x==='.')||/[\\:]/.test(row.path)||seen.has(row.path.toLowerCase()))throw Error('Invalid package manifest.');seen.add(row.path.toLowerCase());
    const full=path.join(ROOT,...row.path.split('/'));require('./application/lib/safety').plainAncestors(full);const b=fs.readFileSync(full);
    if(b.length!==row.bytes||sha(b)!==row.sha256)throw Error('Package changed or incomplete. Extract a fresh verified ZIP; keep your private workspace.');
  }
  const Database=require('./application/node_modules/better-sqlite3');const db=new Database(':memory:');const sqlite=db.prepare('select sqlite_version() as v').get().v;db.close();
  return {status:'PASS',runtime:process.versions.node,abi:process.versions.modules,sqlite,bundled_runtime:true};
}
function browser(url){
  if(!/^http:\/\/127\.0\.0\.1:\d+\/admin$/.test(url))throw Error('Only the generated loopback editor URL can be opened.');
  const system=process.env.SystemRoot||process.env.SYSTEMROOT;if(!system)throw Error('Windows SystemRoot unavailable. Open the printed URL manually.');
  const child=spawn(path.join(system,'System32/rundll32.exe'),['url.dll,FileProtocolHandler',url],{stdio:'ignore',windowsHide:true});
  child.on('error',()=>console.error('Open the printed editor URL in your browser.'));child.unref();
}
async function password(){
  if(!process.stdin.isTTY)throw Error('First launch needs an interactive console. Advanced automation can use --setup-stdin.');
  const readline=require('node:readline'),{Writable}=require('node:stream');
  const input=readline.createInterface({input:process.stdin,output:new Writable({write(_c,_e,done){done();}}),terminal:true});
  const ask=prompt=>new Promise(resolve=>{process.stdout.write(prompt);input.question('',answer=>{process.stdout.write('\n');resolve(answer);});});
  try{const a=await ask('New admin password (hidden, 14+ characters, at most 72 UTF-8 bytes): '),b=await ask('Confirm password (hidden): ');if(a!==b)throw Error('Passwords did not match. No settings were created.');return a;}finally{input.close();}
}
function environment(settings,data){
  const values=require('./application/node_modules/dotenv').parse(fs.readFileSync(settings));
  if(!/^\$2[aby]\$/.test(values.ADMIN_PASSWORD_HASH||'')||(values.SESSION_SECRET||'').length<32)throw Error('Private settings incomplete. Preserve them and see START-HERE.txt.');
  const env={};for(const [k,v] of Object.entries(process.env))if(['SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','TMPDIR','LOCALAPPDATA'].includes(k.toUpperCase()))env[k]=v;
  env.PATH=path.join(process.env.SystemRoot||process.env.SYSTEMROOT,'System32');
  return {...env,ADMIN_USERNAME:values.ADMIN_USERNAME||'admin',ADMIN_PASSWORD_HASH:values.ADMIN_PASSWORD_HASH,SESSION_SECRET:values.SESSION_SECRET,HOST:'127.0.0.1',PORT:'0',SITE_DATA_DIR:data,EMAIL_SERVICE_ENABLED:'false'};
}
async function main(args=process.argv.slice(2)){
  const options={};while(args.length){const k=args.shift();if(['--workspace','--data','--backup','--verify-backup','--restore'].includes(k)){if(options[k]||!args[0])throw Error('Missing or repeated option.');options[k]=args.shift();}else if(['--check','--no-browser','--setup-stdin','--stop-stdin'].includes(k))options[k]=true;else throw Error('Unknown option. See START-HERE.txt.');}
  const checked=health();
  if(options['--check']){console.log(JSON.stringify(checked));return;}
  const local=process.env.LOCALAPPDATA;if(!options['--workspace']&&!local)throw Error('LOCALAPPDATA unavailable; use --workspace with a new trusted absolute local path.');
  const workspace=outside(options['--workspace']||path.join(local,'Outlands/LocalSiteBuilder'));
  const data=outside(options['--data']||path.join(workspace,'data')),settings=path.join(workspace,'.env');
  const {plainAncestors}=require('./application/lib/safety');plainAncestors(settings);
  const modes=['--backup','--verify-backup','--restore'].filter(k=>options[k]);if(modes.length>1)throw Error('Choose one maintenance action.');
  if(options['--verify-backup']){const m=require('./application/lib/backup').verify(outside(options['--verify-backup']));console.log(JSON.stringify({status:'verified',files:m.files.length}));return;}
  if(options['--restore']){if(!options['--data'])throw Error('Restore needs --data with an explicit new destination.');const result=require('./application/lib/backup').restore(outside(options['--restore']),data);console.log(JSON.stringify(result));return;}
  if(options['--backup']){const result=await require('./application/lib/backup').backup(data,outside(options['--backup']));console.log(JSON.stringify(result));return;}
  const exists=fs.existsSync(settings);
  if(options['--setup-stdin']&&exists)throw Error('Settings already exist; passwords are never replaced.');
  if(!exists){
    if(fs.existsSync(data))throw Error('Data exists without settings. Preserve it and restore its private settings separately; no reset or new account was made.');
    let value;if(options['--setup-stdin']){let b='';for await(const chunk of process.stdin){b+=chunk;if(Buffer.byteLength(b)>1024)throw Error('Input too long.');}value=b.replace(/\r?\n$/,'');}else value=await password();
    plainAncestors(workspace);fs.mkdirSync(workspace,{recursive:true,mode:0o700});await require('./application/scripts/setup').setup(value,workspace);
    console.log('Created private settings outside the app. Username: admin. Keep your password and .env private.');
    if(options['--setup-stdin'])return;
  }
  const env=environment(settings,data);
  const child=fork(path.join(APP,'server.js'),[],{cwd:APP,env,execPath:process.execPath,execArgv:[],stdio:['ignore','pipe','pipe','ipc']});
  let ready=false,buffer='',stopping=false;child.stderr.on('data',b=>process.stderr.write(b));
  child.stdout.on('data',b=>{buffer+=b.toString();const m=buffer.match(/http:\/\/127\.0\.0\.1:\d+/);if(m&&!ready){ready=true;const url=m[0]+'/admin';console.log('Editor: '+url);console.log('Username: admin. Stop with Ctrl+C in this console. Data: '+data);if(!options['--no-browser'])browser(url);}});
  function stop(){if(stopping)return;stopping=true;if(child.connected)child.send('shutdown');}
  process.on('SIGINT',stop);process.on('SIGTERM',stop);process.on('message',message=>{if(message==='shutdown')stop();});
  if(options['--stop-stdin']){process.stdin.setEncoding('utf8');process.stdin.on('data',s=>{if(s.trim()==='stop')stop();});process.stdin.resume();}
  child.on('exit',code=>{process.stdin.pause();if(process.connected)process.disconnect();process.exitCode=code===0?0:1;});
  child.on('error',()=>{console.error('Could not start bundled editor. Keep private data; see START-HERE.txt.');process.exitCode=1;});
}
if(require.main===module)main().catch(error=>{console.error('Local Site Builder: '+error.message);process.exitCode=1;});
module.exports={main,browser,outside,health};
