// Original validation helpers. MIT.
const fs=require('node:fs');
const path=require('node:path');
function plainAncestors(input){
  const full=path.resolve(input);
  if(full.startsWith('\\\\'))throw new Error('Use trusted local storage.');
  let current=path.parse(full).root;
  for(const part of full.slice(current.length).split(path.sep).filter(Boolean)){
    current=path.join(current,part);
    if(fs.existsSync(current)){
      const info=fs.lstatSync(current);
      if(info.isSymbolicLink()||fs.realpathSync(current).toLowerCase()!==current.toLowerCase())throw new Error('Linked storage is unsupported.');
    }
  }
  return full;
}
function dataRoot(){return plainAncestors(process.env.SITE_DATA_DIR||path.join(__dirname,'../data'));}
function lock(root){
  plainAncestors(root);fs.mkdirSync(root,{recursive:true});
  const name=path.join(root,'.owner-lock');
  const fd=fs.openSync(name,'wx',0o600);fs.writeFileSync(fd,String(process.pid));
  const own=fs.fstatSync(fd);
  let released=false;
  return ()=>{if(released)return;released=true;fs.closeSync(fd);const now=fs.lstatSync(name);if(now.ino===own.ino&&now.size===own.size)fs.unlinkSync(name);};
}
const allowedTypes=new Set(['hero','text','image_text','three_cards','checklist','faq','affiliate_product','cta','divider','contact']);
function validatePage(value){
  if(!value||typeof value!=='object'||Array.isArray(value)||!Array.isArray(value.blocks)||value.blocks.length>100)throw new Error('A page needs at most 100 blocks.');
  let nodes=0,chars=0;
  function walk(v,depth){
    if(++nodes>10000||depth>10)throw new Error('Page structure is too large or deep.');
    if(typeof v==='string'){chars+=v.length;if(v.length>10000||chars>200000)throw new Error('Page text is too large.');}
    else if(typeof v==='number'){if(!Number.isFinite(v))throw new Error('Invalid page number.');}
    else if(v&&typeof v==='object'){
      if(Array.isArray(v)){if(v.length>200)throw new Error('A page list is too long.');v.forEach(x=>walk(x,depth+1));}
      else for(const [key,item] of Object.entries(v)){if(['__proto__','constructor','prototype'].includes(key))throw new Error('Unsupported page key.');walk(item,depth+1);}
    } else if(v!==null&&typeof v!=='boolean')throw new Error('Unsupported page value.');
  }
  walk(value,0);
  const ids=new Set();
  for(const b of value.blocks){
    if(!b||!allowedTypes.has(b.type)||typeof b.id!=='string'||!b.id||b.id.length>100||!b.settings||typeof b.settings!=='object'||Array.isArray(b.settings))throw new Error('Invalid block.');
    if(ids.has(b.id))throw new Error('Duplicate block ID.');ids.add(b.id);
    const required={three_cards:'cards',faq:'faqs',checklist:'items'}[b.type];
    if(required&&!Array.isArray(b.settings[required]))throw new Error('Missing block list.');
    for(const key of ['cards','faqs'])if(b.settings[key]!==undefined&&(!Array.isArray(b.settings[key])||b.settings[key].some(x=>!x||typeof x!=='object'||Array.isArray(x))))throw new Error('Invalid block list.');
    if(b.settings.items!==undefined&&(!Array.isArray(b.settings.items)||b.settings.items.some(x=>typeof x!=='string')))throw new Error('Invalid checklist.');
  }
  return value;
}
function imageType(bytes){
  if(bytes.length>=24&&bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))return ['image/png','.png'];
  if(bytes.length>=4&&bytes[0]===255&&bytes[1]===216&&bytes[2]===255)return ['image/jpeg','.jpg'];
  if(bytes.length>=13&&['GIF87a','GIF89a'].includes(bytes.subarray(0,6).toString()))return ['image/gif','.gif'];
  if(bytes.length>=16&&bytes.subarray(0,4).toString()==='RIFF'&&bytes.subarray(8,12).toString()==='WEBP')return ['image/webp','.webp'];
  return null;
}
module.exports={plainAncestors,dataRoot,lock,validatePage,imageType};
