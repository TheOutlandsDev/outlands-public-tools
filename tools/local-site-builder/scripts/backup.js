require('dotenv').config({path:require('node:path').join(__dirname,'../.env'),quiet:true});
const {dataRoot}=require('../lib/safety');
const {backup,verify,restore}=require('../lib/backup');
async function main(){
  const args=process.argv.slice(2);let result;
  if(args.length===1)result=await backup(dataRoot(),args[0]);
  else if(args[0]==='verify'&&args.length===2)result={status:'verified',files:verify(args[1]).files.length};
  else if(args[0]==='restore'&&args.length===3)result=restore(args[1],args[2]);
  else throw new Error('Usage: backup.js NEW_DIRECTORY | verify BACKUP_DIRECTORY | restore BACKUP_DIRECTORY NEW_DATA_DIRECTORY');
  console.log(JSON.stringify(result));
}
if(require.main===module)main().catch(error=>{console.error('Backup/recovery failed: '+error.message+' Partial new output may remain; existing destinations are never overwritten.');process.exitCode=1;});
