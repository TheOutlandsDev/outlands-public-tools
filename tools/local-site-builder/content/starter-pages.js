// Original fictional examples, MIT. No family/business content or assets.
const DEFAULT_DISCLOSURE='Replace this with an accurate disclosure if you use affiliate links.';
const DEFAULT_PAGES=[['Welcome','home'],['Projects','projects'],['About','about']];
const PAGE_TEMPLATES=[
  {id:'guide',label:'Guide',description:'A heading, text and a checklist.'},
  {id:'checklist',label:'Checklist',description:'A short list of tasks.'},
  {id:'product',label:'Project card',description:'A fictional project or product.'},
  {id:'about',label:'About',description:'Introduce your site.'},
  {id:'community',label:'Community',description:'A local inbox contact block.'},
  {id:'blank',label:'Blank',description:'Start with an empty canvas.'}
];
function block(type,settings,id){return {id,type,settings};}
function templatePageData(template,title,slug){
  const blocks=[block('hero',{kicker:'Fictional example',headline:title,body:'Replace this starter text with your own content.'},`${slug}_hero`)];
  if(template==='blank')return {version:1,theme:'natural',blocks:[]};
  if(template==='checklist'||template==='guide')blocks.push(block('checklist',{heading:'Getting started',items:['Choose a small project','Gather the materials','Review your result']},`${slug}_list`));
  if(template==='product')blocks.push(block('affiliate_product',{productName:'Example workbench',shortDescription:'A fictional project. No purchase is offered.',buttonText:'Read more',affiliateUrl:'https://example.invalid',disclosureText:DEFAULT_DISCLOSURE},`${slug}_project`));
  if(template==='about')blocks.push(block('text',{heading:'About this workshop',body:'This is a fictional demo site for learning the editor.'},`${slug}_about`));
  if(template==='community')blocks.push(block('contact',{heading:'Leave a local demo message',body:'Messages stay in this local app unless SMTP is explicitly enabled.',contactEmail:'hello@example.invalid',subject:'Workshop question'},`${slug}_contact`));
  return {version:1,theme:'natural',blocks};
}
function defaultPageData(title,slug){return templatePageData(slug==='about'?'about':'guide',title,slug);}
module.exports={DEFAULT_DISCLOSURE,DEFAULT_PAGES,PAGE_TEMPLATES,templatePageData,defaultPageData};
