// Original static published-site export; no editor, database, draft or inbox. MIT.
require('dotenv').config({path:require('node:path').join(__dirname,'../.env'),quiet:true});
const fs=require('node:fs');
const path=require('node:path');
const Database=require('better-sqlite3');
const {plainAncestors,lock,dataRoot}=require('../lib/safety');
function exportSite(root,output){
  root=plainAncestors(root);const target=plainAncestors(output),rel=path.relative(root,target);
  if(rel===''||(!rel.startsWith('..'+path.sep)&&rel!=='..'&&!path.isAbsolute(rel))||fs.existsSync(target))throw new Error('Choose a new directory outside the data root.');
  if(!fs.statSync(path.dirname(target)).isDirectory())throw new Error('Output parent must exist.');
  const release=lock(root);let db;
  try{
    const dbPath=path.join(root,'db/site.sqlite');plainAncestors(dbPath);
    const wal=dbPath+'-wal';if(fs.existsSync(wal)&&fs.statSync(wal).size)throw new Error('Stop the editor cleanly before export.');
    db=new Database(dbPath,{readonly:true,fileMustExist:true});
    const rows=db.prepare("SELECT slug,published_html FROM pages WHERE status='published' AND published_html<>''").all();
    if(!rows.length||rows.length>200)throw new Error('No published pages or too many pages.');
    fs.mkdirSync(target,{mode:0o700});const images=new Set();
    for(const row of rows){
      if(!/^[a-z0-9-]{1,80}$/.test(row.slug))throw new Error('Invalid published slug.');
      const html=row.published_html.replace(/<form\b[^>]*data-contact-form[^>]*>[\s\S]*?<\/form>/g,'<p>Contact forms need the local editor server. Use the displayed email link instead.</p>');
      for(const match of html.matchAll(/\/uploads\/images\/([a-f0-9]{32}\.(?:png|jpg|gif|webp))/g))images.add(match[1]);
      const dest=row.slug==='home'?path.join(target,'index.html'):path.join(target,row.slug,'index.html');
      fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,html,{flag:'wx'});
    }
    fs.mkdirSync(path.join(target,'assets'));fs.copyFileSync(path.join(__dirname,'../assets/logo.svg'),path.join(target,'assets/logo.svg'),fs.constants.COPYFILE_EXCL);
    if(images.size)fs.mkdirSync(path.join(target,'uploads/images'),{recursive:true});
    for(const image of images){const source=path.join(root,'uploads/images',image);plainAncestors(source);if(fs.statSync(source).size>5*1024*1024)throw new Error('Image too large.');fs.copyFileSync(source,path.join(target,'uploads/images',image),fs.constants.COPYFILE_EXCL);}
    return {status:'exported',pages:rows.length,images:images.size};
  }finally{if(db)db.close();release();}
}
if(require.main===module){try{if(process.argv.length!==3)throw new Error('Usage: npm run export -- NEW_DIRECTORY');console.log(JSON.stringify(exportSite(dataRoot(),process.argv[2])));}catch(error){console.error('Export failed: '+error.message+' Partial new output may remain.');process.exitCode=1;}}
module.exports={exportSite};
