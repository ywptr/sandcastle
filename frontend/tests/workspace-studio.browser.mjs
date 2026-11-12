// B2b acceptance: authenticated/domain/provider responses are synthetic fixtures.
import assert from 'node:assert/strict';
import fs from 'node:fs';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = process.env.WORKSPACE_ORIGIN || 'https://192.168.0.99:5182';
const out = process.env.WORKSPACE_SCREENSHOTS || '/tmp/sandcastle-b2b-review';
fs.mkdirSync(out, { recursive: true });
const styles = JSON.parse(fs.readFileSync(new URL('../../backend/app/creative_direction/styles.json', import.meta.url)));
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
const errors=[], measurements=[], writes=[];
let testPage;
try {
 const context=await browser.newContext({locale:'id-ID',ignoreHTTPSErrors:true,viewport:{width:1440,height:900}});
 const page=await context.newPage();testPage=page;page.setDefaultTimeout(15000);page.on('pageerror',e=>errors.push(e.message));
 const stories=[{story_id:'s1',title:'The Cartographer’s Lantern',premise:'Mara maps a city that rearranges itself at dawn. One street has begun to remember her name.',objective:'Find the missing district before its final lantern fades.',language:'en',primary_genre:'fantasy',secondary_genres:['mystery'],status:'draft'},{story_id:'s2',title:'Letters from the Tide',premise:'A quiet coastal mystery.',language:'id',primary_genre:'drama',secondary_genres:[],status:'draft'}];
 const scenes=[{scene_id:'sc1',sequence_number:1,title:'The street that remembered',content:'Mara unfolded the map beneath the last lantern.\n\nA staircase led down into a district she had never drawn. Someone had written her name on the first step.',status:'draft'}];
 const style=styles.find(s=>s.id==='korean_romance_drama');
 let snapshot={story_id:'s1',direction_id:'d1',revision:3,direction:{target_format:'webtoon',storytelling_style_id:style.id,style_version:style.version,audience_rating:'teen_13',visual_style:'match_style',cultural_setting:null,historical_era:null,tone:'Mysterious',tropes:[],expected_revision:2,language_at_approval:'en'},style,approved_at:'2026-11-12T00:00:00Z'};
 const workflow={story_id:'s1',difficulty:'easy',template_name:'Standard',configuration:{steps:[{step_id:'scene_creation',enabled:true},{step_id:'narrative_guidance',enabled:true}]},capabilities:[],step_definitions:[]};
 let failGenerate=true, conflict=true, failDirection=false;
 await page.route('**/api/**',async route=>{
  const req=route.request(),p=new URL(req.url()).pathname;if(!p.startsWith('/api/'))return route.continue();let data;
  const body=req.postDataJSON();if(req.method()!=='GET')writes.push({path:p,method:req.method(),body});
  if(p==='/api/auth/me')data={user_id:'workspace-fixture',name:'Studio preview',email:'writer@example.test'};
  else if(p==='/api/stories')data=stories;
  else if(p==='/api/styles')data=styles;
  else if(p.endsWith('/creative-direction')){
   if(failDirection){return route.fulfill({status:503,json:{detail:'Temporary read failure'}});}
   if(req.method()==='PUT'){
    assert.equal('language_at_approval' in body,false);
    if(conflict){conflict=false;snapshot={...snapshot,revision:4};return route.fulfill({status:409,json:{detail:'Revision changed'}});}
    assert.equal(body.expected_revision,4);snapshot={...snapshot,revision:5,direction:body};
   }data=p.includes('/s1/')?snapshot:null;
  }
  else if(p.endsWith('/workflow'))data=workflow;
  else if(p.endsWith('/guidance/profile'))data={audience:'teen',maturity_rating:'mild',tone:null,genre:null,guidance_notes:null,average_rating:null,rating_count:0,feedback_tags:[]};
  else if(p.endsWith('/narrative_guidance'))data={suggestions:[{id:'g1',title:'Follow the light',text:'Mara follows a flickering light into the lost district.'}]};
  else if(p.endsWith('/scenes/generate')){
   if(failGenerate){failGenerate=false;return route.fulfill({status:503,json:{detail:'Provider unavailable'}});}
   const scene={scene_id:'sc2',sequence_number:2,title:'The lantern answers',content:'A new path opened beneath the city.',status:'draft'};scenes.push(scene);data={scene,action:{status:'executed'}};
  }
  else if(p.endsWith('/scenes'))data=p.includes('/s1/')?scenes:[];
  else if(p.endsWith('/characters'))data=[{character_id:'c1',name:'Mara',description:'An apprentice cartographer.',appearance:'Dark curls.',outfit:'Blue coat.',personality:'Curious.'}];
  else if(p.endsWith('/places'))data=[{place_id:'p1',name:'The shifting market',description:'A street that moves at dawn.'}];
  else if(p.endsWith('/canon')||p.endsWith('/actions'))data=[];
  else throw Error('Unexpected fixture route: '+p);
  await route.fulfill({json:data});
 });
 await page.goto(origin,{waitUntil:'networkidle'});await page.locator('.story-list-item').first().click();
 const workspace=()=>page.locator('.studio-workspace:visible');
 const nav=()=>workspace().locator('.workspace-nav');
 const button=name=>workspace().getByRole('button',{name,exact:true});
 async function shot(name){await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:`${out}/${name}.png`,fullPage:name.includes("after-setup-")});}
 async function checkLayout(label,width){
  const data=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
  assert.equal(data.document>data.viewport,false,label);measurements.push({label,width,...data});
 }
 await workspace().getByText('Revision 3',{exact:true}).waitFor();
 assert.equal(await page.locator('html').getAttribute('lang'),'en');
 assert.equal(await workspace().locator('.setup-values dd').filter({hasText:'English'}).count(),1);
 assert.equal(writes.length,0);
 await checkLayout('chat en desktop',1440);await shot('after-chat-desktop');
 await button('Split workspace').focus();await page.keyboard.press('Enter');
 await nav().getByRole('button',{name:/^Scenes/}).first().click();await checkLayout('split en desktop',1440);await shot('after-split-desktop');
 const prompt=workspace().getByLabel('What should happen next?',{exact:true});await prompt.fill('Mara opens the impossible door.');
 await button('Edit scene').click();const sceneText=workspace().getByLabel('Scene content',{exact:false});await sceneText.fill('Unsaved Scene draft survives view and Story switching.');
 await button('Chat view').click();assert.equal(await workspace().locator('.editor-region').isVisible(),false);
 await button('Split workspace').click();assert.equal(await sceneText.inputValue(),'Unsaved Scene draft survives view and Story switching.');
 await button('Focus editor').click();await checkLayout('focus en desktop',1440);await shot('after-focus-desktop');assert.equal(await sceneText.inputValue(),'Unsaved Scene draft survives view and Story switching.');
 await button('Split workspace').click();await nav().getByRole('button',{name:'Characters',exact:true}).click();
 await nav().getByRole('button',{name:/^Scenes/}).first().click();assert.equal(await sceneText.inputValue(),'Unsaved Scene draft survives view and Story switching.');
 await page.locator('.studio-sidebar [data-destination="series"]').click();await page.locator('.story-list-item').nth(1).click();
 await page.locator('.studio-sidebar [data-destination="series"]').click();await page.locator('.story-list-item').first().click();
 await nav().getByRole('button',{name:/^Scenes/}).first().click();assert.equal(await workspace().getByLabel('Scene content',{exact:false}).inputValue(),'Unsaved Scene draft survives view and Story switching.');
 await workspace().getByRole('button',{name:'Cancel',exact:true}).click();
 assert.equal(await workspace().getByLabel('What should happen next?',{exact:true}).inputValue(),'Mara opens the impossible door.');
 // A retained form survives secondary settings and EN/ID layout changes.
 await button('Edit details').click();const premise=workspace().getByLabel('Premise',{exact:false});await premise.fill('Unsaved Story premise.');
 await button('Chat view').click();await button('Split workspace').click();assert.equal(await premise.inputValue(),'Unsaved Story premise.');
 await workspace().getByRole('button',{name:'Cancel',exact:true}).click();
 await button('Chat view').click();await button('Suggest what happens next').click();await button('Use this suggestion').click();
 assert.match(await workspace().getByLabel('What should happen next?',{exact:true}).inputValue(),/flickering/);
 await button('Generate scene →').click();await workspace().getByText('Could not generate. Your prompt is ready to retry.',{exact:true}).waitFor();
 assert.match(await workspace().getByLabel('What should happen next?',{exact:true}).inputValue(),/flickering/);
 await button('Generate scene →').click();await workspace().getByText('Scene drafted.',{exact:false}).waitFor();assert.equal(scenes.length,2);
 await workspace().locator('.scene-picker button').first().click();await button('Edit scene').click();
 await workspace().getByLabel('Scene content',{exact:false}).fill('First Scene draft stays attached to the first Scene.');
 await workspace().locator('.scene-picker button').nth(1).click();await workspace().locator('.scene-picker button').first().click();await button('Edit scene').click();
 assert.equal(await workspace().locator('.record-editor textarea:visible').inputValue(),'First Scene draft stays attached to the first Scene.');
 await workspace().getByRole('button',{name:'Cancel',exact:true}).click();
 await button('Chat view').click();await workspace().locator('.assistant-receipt').scrollIntoViewIfNeeded();await shot('after-generated-result-desktop');
 await button('Edit creative direction').click();await workspace().getByText('Advanced creative options',{exact:true}).click();
 const tone=workspace().getByLabel('Tone',{exact:true});await tone.fill('Keep this unsaved direction.');
 await button('Story Setup').click();await button('Story Setup').click();assert.equal(await tone.inputValue(),'Keep this unsaved direction.');
 await button('Approve new direction').click();await workspace().getByText('The saved Creative Direction has changed.',{exact:false}).waitFor();
 assert.equal(await tone.inputValue(),'Keep this unsaved direction.');await shot('after-direction-conflict-desktop');
 await button('Reload saved direction').click();await workspace().getByText('Revision 4',{exact:true}).waitFor();
 assert.equal(await tone.inputValue(),'Keep this unsaved direction.');await workspace().getByRole('button',{name:'Cancel',exact:true}).click();
 await button('Edit creative direction').click();await button('Approve new direction').click();await workspace().getByText('Revision 5',{exact:true}).waitFor();
 assert.equal(snapshot.revision,5);assert.equal(styles.length,8);
 // Each mobile mode has exactly one primary region; setup is secondary and collapsed on resize.
 for(const locale of ['en','id']){
  await page.locator('.studio-language select').selectOption(locale);assert.equal(stories[0].language,'en');
  for(const width of [390,320]){
   await page.setViewportSize({width,height:844});
   const modes=workspace().locator('.mobile-modes button');
   await modes.nth(1).click();await checkLayout(`${locale} assistant`,width);await shot(`after-assistant-${locale}-${width}`);
   assert.equal(await workspace().locator('.assistant-region').isVisible(),true);assert.equal(await workspace().locator('.editor-region').isVisible(),false);assert.equal(await nav().isVisible(),false);
   await workspace().getByLabel(locale==='en'?'What should happen next?':'Apa yang terjadi selanjutnya?',{exact:true}).fill('A mobile prompt kept across modes.');
   await modes.nth(0).click();await checkLayout(`${locale} story`,width);await shot(`after-story-${locale}-${width}`);
   assert.equal(await nav().isVisible(),true);assert.equal(await workspace().locator('.assistant-region').isVisible(),false);
   await nav().getByRole('button',{name:locale==='en'?/^Scenes/:/^Adegan/}).first().click();await checkLayout(`${locale} preview`,width);await shot(`after-preview-${locale}-${width}`);
   assert.equal(await workspace().locator('.editor-region').isVisible(),true);assert.equal(await workspace().locator('.assistant-region').isVisible(),false);assert.equal(await nav().isVisible(),false);
   const setup=workspace().locator('.workspace-setup-toggle');if(await setup.getAttribute('aria-expanded')==='false')await setup.click();await checkLayout(`${locale} setup`,width);await shot(`after-setup-${locale}-${width}`);await setup.click();
   await modes.nth(1).click();assert.equal(await workspace().getByLabel(locale==='en'?'What should happen next?':'Apa yang terjadi selanjutnya?',{exact:true}).inputValue(),'A mobile prompt kept across modes.');
  }
 }
 await page.setViewportSize({width:1440,height:900});await page.locator('.studio-language select').selectOption('en');
 // Reload error has an explicit retry and cannot turn an unknown setting into a saved default.
 failDirection=true;await page.reload({waitUntil:'networkidle'});await page.locator('.story-list-item').first().click();await workspace().getByText('Creative Direction could not load.',{exact:false}).waitFor();
 failDirection=false;await workspace().getByRole('button',{name:'Reload saved direction',exact:true}).click();await workspace().getByText('Revision 5',{exact:true}).waitFor();
 assert.deepEqual(errors,[]);
 fs.writeFileSync(out+'/measurements.json',JSON.stringify({fixtureOnly:true,measurements,writes,errors},null,2));
 console.log('PASS B2b: Chat/Split/Focus, saved Setup values and eight presets, keyboard view switching, Story/Scene/assistant drafts across modes/sections/Stories, failed generation retry, saved-result labeling, Creative Direction 409 retention/reload/reapproval with expected_revision, read retry, independent EN/ID, and 390/320 single-primary mobile layouts. Authenticated/provider data are fixtures.');
 await context.close();
}catch(error){if(testPage)await testPage.screenshot({path:out+'/failure.png',fullPage:true});console.error(error);throw error;}finally{await browser.close();}
