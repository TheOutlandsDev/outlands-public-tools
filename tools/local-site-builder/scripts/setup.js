// Original local credential setup. MIT. Never reads an existing .env.
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const bcrypt=require('bcryptjs');
const readline=require('node:readline');
const {Writable}=require('node:stream');
const {plainAncestors}=require('../lib/safety');
async function setup(password,root=path.join(__dirname,'..')){
  if(typeof password!=='string'||password.length<14||Buffer.byteLength(password)>72||/[\r\n\x00]/.test(password))throw new Error('Use a password of at least 14 characters and at most 72 UTF-8 bytes, on one line.');
  plainAncestors(root);
  const hash=await bcrypt.hash(password,12);
  const text=`# Private local settings. Keep this file outside GitHub and shared backups.\nADMIN_USERNAME=admin\nADMIN_PASSWORD_HASH=${hash}\nSESSION_SECRET=${crypto.randomBytes(32).toString('hex')}\nPORT=3000\nEMAIL_SERVICE_ENABLED=false\n`;
  fs.writeFileSync(path.join(root,'.env'),text,{flag:'wx',mode:0o600});
}
async function main(){
  let password;
  if(process.argv.slice(2).join(' ')==='--stdin'){
    const chunks=[];let size=0;
    for await(const chunk of process.stdin){size+=chunk.length;if(size>1024)throw new Error('Input too long.');chunks.push(chunk);}
    password=Buffer.concat(chunks).toString('utf8').replace(/\r?\n$/,'');
  }else if(process.argv.length===2&&process.stdin.isTTY){
    const muted=new Writable({write(_chunk,_encoding,done){done();}});
    const input=readline.createInterface({input:process.stdin,output:muted,terminal:true});
    process.stdout.write('New admin password (hidden, at least 14 characters): ');
    password=await new Promise(resolve=>input.question('',resolve));input.close();process.stdout.write('\n');
  }else throw new Error('Use interactive npm run setup, or --stdin with a private input pipe.');
  await setup(password);console.log('Created a new private .env. Username: admin. Start with npm start.');
}
if(require.main===module)main().catch(error=>{console.error('Setup failed: '+error.message);process.exitCode=1;});
module.exports={setup};
