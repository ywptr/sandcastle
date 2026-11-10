// Fixture-only acceptance. No billable AI, IG, production DB, or live credentials.
import assert from 'node:assert/strict';
import fs from 'node:fs';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
const origin=process.env.WORKSPACE_ORIGIN||'https://192.168.0.99:5182';
const out='/tmp/sc0004-visuals';fs.mkdirSync(out,{recursive:true});
const styles=JSON.parse(fs.readFileSync(new URL('../../backend/app/creative_direction/styles.json',import.meta.url)));
const errors=[];
async function session(locale){
 const context=await browser.newContext({locale,ignoreHTTPSErrors:true,viewport:{width:1440,height:1000}});const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 const stories=[];let snapshot=null;let failRecommendation=false;let failCreation=true;const writes=[];
 await page.route('**/api/**',async route=>{
  const req=route.request(),p=new URL(req.url()).pathname;if(!p.startsWith('/api/'))return route.continue();let data;
  if(p==='/api/auth/me')data={user_id:'onboarding-fixture',name:'Creator',email:'creator@example.test'};
  else if(p==='/api/stories')data=stories;
  else if(p==='/api/styles')data=styles;
  else if(p==='/api/styles/recommend'){
   if(failRecommendation)return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'No provider'})});
   data={target_format:req.postDataJSON().target_format,primary_genre:'romance',secondary_genres:['drama'],storytelling_style_id:'korean_romance_drama',audience_rating:'teen_13',language:'en',visual_style:'match_style',tone:'Emotional',rationale:'Gradual relationships and emotional tension.',warnings:[]};
  }else if(p==='/api/stories/import/analyze')data={story:{proposed_title:'A shared secret',premise:'Two students find a letter.',evidence:['A letter arrives.'],detected_language:'en'},characters:[],places:[],canon_candidates:[],warnings:[]};
  else if(p==='/api/stories/start'){
   if(failCreation){failCreation=false;return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Temporarily unavailable'})});}const body=req.postDataJSON();writes.push(body);const story={...body.story,story_id:'s-new',user_id:'onboarding-fixture',status:'active',created_at:'2026-11-10T00:00:00Z',updated_at:'2026-11-10T00:00:00Z'};stories.push(story);snapshot={direction_id:'d1',story_id:story.story_id,revision:1,direction:{...body.creative_direction,language_at_approval:story.language},style:styles.find(s=>s.id===body.creative_direction.storytelling_style_id),approved_at:'2026-11-10T00:00:00Z'};data=story;
  }else if(p.endsWith('/creative-direction')){
   if(req.method()==='PUT'){const body=req.postDataJSON();assert.equal('language_at_approval' in body,false);snapshot={...snapshot,revision:snapshot.revision+1,direction:body,style:styles.find(s=>s.id===body.storytelling_style_id)};}data=snapshot;
  }else if(p.endsWith('/guidance/profile'))data={story_id:'s-new',audience:'general',tone:'balanced',pacing:'balanced',focus_areas:[]};
  else if(p.endsWith('/workflow'))data={story_id:'s-new',difficulty:'easy',template_name:'Standard',configuration:{steps:[],media_settings:{},story_settings:{}},capabilities:[],step_definitions:[]};
  else if(['/characters','/places','/canon','/scenes','/actions'].some(v=>p.endsWith(v)))data=[];
  else throw Error('Unexpected onboarding fixture route: '+p);
  return route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
 });
 return {context,page,stories,writes,setFailure:()=>{failRecommendation=true;}};
}
try{
 for(const [locale,title]of [['en-US','What do you want to create?'],['id-ID','Cerita apa yang ingin kamu buat?'],['fr-FR','What do you want to create?']]){
  const s=await session(locale),{page}=s;await page.goto(origin,{waitUntil:'networkidle'});await page.getByRole('heading',{name:title,exact:true}).waitFor();assert.equal(await page.locator('html').getAttribute('lang'),locale==='id-ID'?'id':'en');
  if(locale==='fr-FR'){await page.getByRole('button',{name:'Settings',exact:true}).click();await page.getByText('Your browser language is not supported yet.',{exact:false}).waitFor();}
  if(locale==='id-ID'){
   await page.getByRole('button',{name:'Pengaturan',exact:true}).click();await page.getByLabel('Bahasa antarmuka').selectOption('en');await page.reload({waitUntil:'networkidle'});await page.getByRole('heading',{name:'What do you want to create?',exact:true}).waitFor();
   await page.getByRole('button',{name:'Settings',exact:true}).click();await page.getByLabel('Interface language').selectOption('auto');await page.getByRole('button',{name:'Kembali ke studio',exact:true}).click();await page.getByRole('heading',{name:title,exact:true}).waitFor();
   s.setFailure();await page.getByRole('button',{name:'Serial Webtoon',exact:true}).click();await page.getByLabel('Ceritakan ide ceritamu').fill('Dua mahasiswa bertemu di perpustakaan.');await page.getByRole('button',{name:'Rekomendasikan arahan kreatif',exact:true}).click();await page.getByText('Ini bukan rekomendasi AI.',{exact:false}).waitFor();
   await page.getByRole('button',{name:'Sesuaikan',exact:true}).click();await page.getByLabel('Bahasa cerita / dialog').selectOption('en');assert.equal(await page.locator('html').getAttribute('lang'),'id');
   for(const width of[390,320]){await page.setViewportSize({width,height:900});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await page.screenshot({path:`${out}/create-id-${width}.png`,fullPage:true});}
   await page.getByRole('button',{name:'Ubah gaya',exact:true}).click();const sheet=page.getByRole('dialog');await sheet.waitFor();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);const bounds=await sheet.boundingBox();assert.equal(Math.round(bounds.y),0);assert.equal(Math.round(bounds.height),900);await page.screenshot({path:out+'/style-id-mobile.png',fullPage:false});await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>!!document.activeElement?.closest('dialog')),true);await page.keyboard.press('Escape');assert.equal(await sheet.count(),0);
  }
  await s.context.close();
 }
 const s=await session('en-US'),{page}=s;await page.goto(origin,{waitUntil:'networkidle'});
 await page.getByRole('button',{name:'Import an existing story',exact:true}).click();await page.getByLabel('Existing story text').fill('A letter arrives.');await page.getByRole('button',{name:'Analyze story',exact:true}).click();await page.getByRole('heading',{name:'Story analysis',exact:true}).waitFor();assert.equal(s.stories.length,0);await page.getByRole('button',{name:'Back',exact:true}).click();
 await page.getByRole('button',{name:'Webtoon Series',exact:true}).click();await page.getByLabel('Tell us your story idea').fill('Two university students grow closer over a mysterious letter.');await page.getByRole('button',{name:'Recommend creative direction',exact:true}).click();await page.getByRole('heading',{name:'Your story direction',exact:true}).waitFor();assert.equal(s.stories.length,0);await page.getByRole('button',{name:'Customize',exact:true}).click();
 await page.getByRole('button',{name:'Change style',exact:true}).click();const dialog=page.getByRole('dialog');await dialog.waitFor();await dialog.getByLabel('Search styles, regions, or moods').fill('no-such-style');await dialog.getByText('No styles found.',{exact:false}).waitFor();await dialog.getByLabel('Search styles, regions, or moods').fill('');await dialog.getByLabel('Browse by region').selectOption('mena');await dialog.getByRole('button',{name:'Turkish Dizi Romance',exact:false}).click();await dialog.getByRole('heading',{name:'Video / Performance direction'}).waitFor();await page.screenshot({path:out+'/style-library.png',fullPage:false});await dialog.getByRole('button',{name:'Use this style',exact:true}).click();assert.equal(await dialog.count(),0);
 await page.getByLabel('Story / dialogue language').selectOption('id');await page.getByLabel('Primary genre').selectOption('romance');await page.getByLabel('Series title').fill('Letters in the Library');await page.screenshot({path:out+'/review-desktop.png',fullPage:true});
 await page.getByRole('button',{name:'Looks good — create series',exact:true}).click();await page.getByText('Your series could not be created.',{exact:false}).waitFor();assert.equal(s.stories.length,0);assert.equal(await page.getByLabel('Series title').inputValue(),'Letters in the Library');await page.getByRole('button',{name:'Looks good — create series',exact:true}).click();await page.getByRole('heading',{name:'Letters in the Library',exact:true}).waitFor();assert.equal(s.stories.length,1);assert.equal(s.writes[0].story.language,'id');assert.equal(s.writes[0].creative_direction.storytelling_style_id,'turkish_dizi_romance');assert.equal(s.writes[0].creative_direction.cultural_setting,null);assert.equal(await page.locator('html').getAttribute('lang'),'en');
 const nav=page.getByRole('navigation',{name:'Story workspace',exact:true});assert.equal(await nav.getByRole('button',{name:'Canon',exact:true}).count(),0);await page.getByRole('button',{name:'Create adaptation',exact:true}).click();await page.getByText('All formats share this Story',{exact:false}).waitFor();assert.equal(s.stories.length,1);
 await page.getByRole('button',{name:'Edit creative direction',exact:true}).click();await page.getByRole('button',{name:'Approve new direction',exact:true}).click();await page.getByText('New direction approved.',{exact:false}).waitFor();await page.reload({waitUntil:'networkidle'});await page.getByText('View Creative Direction',{exact:true}).click();await page.getByText('Revision 2',{exact:true}).waitFor();
 await nav.getByRole('button',{name:'More story tools',exact:true}).click();await nav.getByRole('button',{name:'Canon',exact:true}).waitFor();await s.context.close();assert.deepEqual(errors,[]);console.log('PASS: en/id/unsupported locales, override/reload/Automatic, Import analysis only, recommendations/manual fallback, style search/region/detail, creation, immutable revision, Easy tools, shared-Story adaptation, language independence, 320/390 layouts. No media calls.');
}finally{await browser.close();}
