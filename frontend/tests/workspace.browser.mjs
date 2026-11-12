// Optional browser harness: provide Playwright externally; no application dependency.
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || "playwright");
import assert from 'node:assert/strict';
import fs from 'node:fs';
const browser = await chromium.launch({headless:true,args:['--no-sandbox']});
const origin=process.env.WORKSPACE_ORIGIN || "https://192.168.0.99:5182";
const out=process.env.WORKSPACE_SCREENSHOTS || "/tmp/m14-visuals";fs.mkdirSync(out,{recursive:true});
const page = await browser.newPage({ignoreHTTPSErrors:true,viewport:{width:1600,height:1000}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
let connected=false;page.on('console',m=>{if(m.text().includes('[vite] connected'))connected=true;});
try {
await page.goto(origin,{waitUntil:'networkidle'});
await page.getByRole('button',{name:'Sign in through IS'}).waitFor();
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
await page.screenshot({path:out+'/sign-in.png',fullPage:true});
const auth=await page.request.get(origin+'/api/auth/login',{maxRedirects:0});
assert([302,307].includes(auth.status()));assert.match(auth.headers().location,/authorize/);
console.log('LIVE: HTTPS sign-in entry, API proxy 401, IS authorize redirect, Vite WebSocket connected='+connected);
const config={steps:['scene_creation','narrative_guidance','canon_extraction','canon_review','continuity_check'].map(step_id=>({step_id,enabled:true})),order:['scene_creation','narrative_guidance','canon_extraction','canon_review','continuity_check'],guidance:{count:3,recent_scene_count:3},review:{require_before_media:true,review_new:true,review_conflicts:true,review_uncertain:true},media:{aspect_ratio:'1:1',output_format:'webtoon'},adaptation:{sensitivity_hints:[]},references:{character_ids:null,place_ids:null,artifact_ids:[]}};
const caps=['guidance_options','template_selection','profile_details','reference_selection','step_configuration','step_ordering'];
const workflow={story_id:'s1',difficulty:'easy',workflow_template_id:'standard-story',template_version:1,template_name:'Standard',configuration:config,capabilities:[],step_definitions:config.steps.map(s=>({...s,label:s.step_id.replaceAll('_',' '),available:true,required:s.step_id==='scene_creation',dependencies:[]}))};
let stories=[{story_id:'s1',title:'The Cartographer’s Lantern',premise:'An apprentice maps a city that rearranges itself every night. One street has begun to remember her name.',objective:'Find the missing district before the final lantern fades.',language:'en',primary_genre:'fantasy',secondary_genres:['mystery'],status:'draft'},{story_id:'s2',title:'Letters from the Tide',premise:'A quiet coastal mystery.',language:'id',primary_genre:'drama',secondary_genres:[],status:'draft'}];
let characters=[{character_id:'c1',name:'Mara',description:'An apprentice cartographer with a gift for noticing what others forget.',appearance:'Dark curls, ink-stained hands.',outfit:'A weathered blue coat.',personality:'Curious and stubborn.'},{character_id:'c2',name:'Ivo',description:'The keeper of the northern lantern.',appearance:'Silver hair.',outfit:'A long wool coat.',personality:'Patient, guarded.'}];
let places=[{place_id:'p1',name:'The shifting market',description:'A street that moves at dawn.',appearance:'Amber lanterns and folded awnings.',atmosphere:'Warm, restless, mysterious.'}];
let canon=[{canon_entry_id:'f1',type:'rule',key:'city.shift',value:'The city rearranges itself at dawn.',status:'approved'},{canon_entry_id:'f2',type:'rule',key:'city.old_map',value:'All maps remain accurate.',status:'superseded'}];
let scenes=[{scene_id:'sc1',sequence_number:1,title:'The street that remembered',content:'Mara unfolded the map beneath the last lantern.\n\nWhere the alley should have ended, a staircase led down into a district she had never drawn. Someone had written her name on the first step.\n\nShe took out her pen. For the first time in her life, the ink refused to dry.',status:'draft'},{scene_id:'sc2',sequence_number:2,title:'A small impossible door',content:'The door was blue yesterday. Today it was the colour of a forgotten promise.',status:'draft'}];
let candidates=[{canon_candidate_id:'q1',key:'city.shift',value:'The city shifts at midnight.',evidence:'“At midnight, the streets began to move.”',classification:'conflict',status:'pending',reasoning:'Conflicts with the approved dawn shift.',subject_name:'City'},{canon_candidate_id:'q2',key:'mara.memory',value:'Mara may remember previous streets.',evidence:'She almost recognized the alley.',classification:'uncertain',status:'pending',reasoning:'The scene implies a possibility, not a confirmed fact.'}];
let failPlaces=false;const writes=[];
await page.route('**/api/**',async route=>{
const req=route.request(),url=new URL(req.url());if(!url.pathname.startsWith('/api/'))return route.continue();const p=url.pathname.replace('/api',''),method=req.method(),body=req.postDataJSON();let result;let status=200;
if(method!=='GET')writes.push({p,method,body});
if(p==='/auth/me')result={user_id:'demo',email:'writer@example.test',name:'Studio preview'};
else if(p==='/stories'){if(method==='POST'){result={...body,story_id:'s3',status:'draft'};stories.unshift(result);}else result=stories;}
else if(/^\/stories\/s\d$/.test(p)){const story=stories.find(s=>s.story_id===p.split('/')[2]);Object.assign(story,body);result=story;}
else if(p.endsWith('/workflow')){if(body)Object.assign(workflow,body);result=workflow;}
else if(p==='/workflows/templates')result=[{workflow_template_id:'standard-story',version:1,name:'Standard',description:'A guided story workflow from scene drafting to explicit Canon review.',difficulty_minimum:'easy',configuration:config}];
else if(p==='/workflows/difficulties')result=['easy','normal','difficult','impossible'].map((id,i)=>({id,label:id[0].toUpperCase()+id.slice(1),capabilities:i?caps:[]}));
else if(p.includes('/characters')){if(body){Object.assign(characters[0],body);result=characters[0];}else result=characters;}
else if(p.endsWith('/creative-direction'))result=null;
else if(p.includes('/places')){if(failPlaces){status=503;result={detail:'Places temporarily unavailable'};}else if(body){Object.assign(places[0],body);result=places[0];}else result=places;}
else if(p.endsWith('/canon/candidates'))result=candidates;
else if(p.endsWith('/approve')||p.endsWith('/reject')){const c=candidates.find(c=>p.includes(c.canon_candidate_id));c.status=p.endsWith('/approve')?'approved':'rejected';result=c;}
else if(p.endsWith('/canon'))result=canon;
else if(p.includes('/canon/f')){Object.assign(canon[0],body);result=canon[0];}
else if(p.endsWith('/scenes/generate')){const scene={scene_id:'sc3',sequence_number:3,title:'The lantern answers',content:'A new path opened beneath the city.',status:'draft'};scenes.push(scene);result={scene,action:{}};}
else if(p.includes('/scenes/')){Object.assign(scenes.find(s=>p.endsWith(s.scene_id)),body);result=scenes.find(s=>p.endsWith(s.scene_id));}
else if(p.endsWith('/scenes'))result=scenes;
else if(p.endsWith('/actions'))result=[];
else if(p.endsWith('/guidance/profile'))result={audience:'teen',maturity_rating:'mild',tone:null,genre:null,guidance_notes:null,average_rating:null,rating_count:0,feedback_tags:[]};
else if(p.endsWith('/narrative_guidance'))result={suggestions:[{id:'g1',title:'Follow the light',text:'Mara follows a flickering light into the lost district.'}]};
else if(p.endsWith('/canon_extraction')||p.endsWith('/continuity_check'))result=[];
else if(p==='/universes')result=[{universe_id:'u1',name:'The Lantern Atlas',description:'Cities shaped by memory.'}];
else if(p==='/universes/u1/stories')result=[{story_id:'s1'}];
else if(p==='/universes/u1/canon/references')result=[{reference_id:'ur1',canon_object_id:'co1',canon_version_id:'v1'}];
else if(p==='/canon/library/co1/versions')result=[{canon_version_id:'v1',version_number:1,data:{name:'Atlas rule',description:'Memory shapes the city.'}}];
else if(p==='/artifacts')result=[{artifact_id:'a1',display_name:'Lantern study',source:'external',media_type:'image'}];
else if(p.endsWith('/references'))result=[];
else throw Error('Unhandled API '+p);
await route.fulfill({status,contentType:'application/json',body:JSON.stringify(result)});
});
await page.reload({waitUntil:'networkidle'});
await page.getByRole('heading',{name:'Series',exact:true}).waitFor();
await page.screenshot({path:out+'/series.png',fullPage:true});
await page.locator('.story-list-item').filter({hasText:'Cartographer'}).click();
await page.screenshot({path:out+'/desktop.png',fullPage:true});
await page.getByRole('button',{name:'Edit details',exact:true}).click();
await page.getByLabel('Story language').selectOption('id');await page.getByLabel('Primary genre').selectOption('adventure');
await page.getByRole('button',{name:'Save story details'}).click();await page.getByRole('button',{name:'Edit details',exact:true}).waitFor();
assert.equal(stories.find(s=>s.story_id==='s1').language,'id');
const nav=page.getByRole('navigation',{name:'Story workspace',exact:true});
await nav.getByRole('button',{name:'Characters',exact:true}).click();
await page.getByRole('button',{name:'Edit character',exact:true}).click();await page.getByLabel('Personality').fill('Brave and observant.');await page.getByRole('button',{name:'Save character',exact:true}).click();
await page.getByRole('button',{name:'Edit character',exact:true}).waitFor();assert.equal(characters[0].personality,'Brave and observant.');
await nav.getByRole('button',{name:'More story tools',exact:true}).click();
await nav.getByRole('button',{name:'Places',exact:true}).click();await page.getByRole('button',{name:'Edit place',exact:true}).click();await page.getByLabel('Atmosphere').fill('Quiet and uneasy.');await page.getByRole('button',{name:'Save place',exact:true}).click();await page.getByRole('button',{name:'Edit place',exact:true}).waitFor();assert.equal(places[0].atmosphere,'Quiet and uneasy.');
await nav.getByRole('button',{name:'Canon',exact:true}).click();await page.getByRole('heading',{name:'Canon candidates'}).waitFor();await page.screenshot({path:out+'/canon.png',fullPage:true});
const conflict=page.locator('.candidate-list li').filter({hasText:'Conflicts with'});assert.equal(await conflict.getByRole('button',{name:'Approve fact'}).isEnabled(),false);await conflict.getByRole('checkbox').check();await conflict.getByRole('button',{name:'Approve fact'}).click();await page.getByText('Canon approved explicitly.').waitFor();assert.equal(candidates[0].status,'approved');
await page.getByRole('button',{name:'Edit canon fact',exact:true}).click();await page.getByLabel('Authoritative fact').fill('The city rearranges at sunrise.');await page.getByRole('button',{name:'Save canon fact',exact:true}).click();await page.getByRole('button',{name:'Edit canon fact',exact:true}).waitFor();
await nav.getByRole('button',{name:/^Scenes/}).first().click();await page.getByRole('button',{name:'Edit scene',exact:true}).click();await page.getByLabel('Scene content').fill('Mara stepped into the lantern light.');await page.getByRole('button',{name:'Save scene',exact:true}).click();await page.getByRole('button',{name:'Edit scene',exact:true}).waitFor();await page.screenshot({path:out+'/scenes.png',fullPage:true});
await page.getByRole('button',{name:'Continue the story'}).click();await page.getByRole('button',{name:'Generate scene →',exact:true}).click();await page.getByText('Scene drafted.',{exact:false}).waitFor();assert.equal(scenes.length,3);
await nav.getByRole('button',{name:'Workflow & Difficulty'}).click();await page.getByLabel('Difficulty',{exact:false}).selectOption('impossible');await page.getByRole('button',{name:'Save workflow',exact:true}).click();await page.getByText('Workflow saved.',{exact:false}).waitFor();await page.screenshot({path:out+'/workflow.png',fullPage:true});
await page.getByRole('button',{name:'Suggest what happens next'}).click();await page.getByRole('button',{name:'Use this suggestion'}).click();assert.match(await page.getByLabel('What should happen next?').inputValue(),/flickering/);
await nav.getByRole('button',{name:'Universe',exact:true}).click();await page.getByText('The Lantern Atlas',{exact:true}).waitFor();await page.getByText('Canon reference · co1').click();await page.getByText('Memory shapes the city.',{exact:false}).waitFor();
await nav.getByRole('button',{name:'Assets',exact:true}).click();await page.getByText('Lantern study').waitFor();
await page.getByRole('button',{name:'My Series'}).click();await page.locator('.story-list-item').filter({hasText:'Letters'}).click();await page.getByRole('heading',{name:'Letters from the Tide',exact:true}).waitFor();
await page.getByRole('button',{name:'My Series'}).click();await page.getByRole('button',{name:'Detailed story form'}).click();await page.getByLabel('Title / idea').fill('A new horizon');await page.getByLabel('Story language').selectOption('ja');await page.getByRole('button',{name:'Create series',exact:true}).click();await page.getByRole('heading',{name:'A new horizon',exact:true}).waitFor();assert.equal(stories[0].language,'ja');
for(const width of [1440,1024,768,390,320]){
await page.setViewportSize({width,height:900});
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'overflow at '+width);
if(width===390){await page.screenshot({path:out+'/mobile.png',fullPage:true});await page.getByRole('button',{name:/Story tools/}).click();await nav.getByRole('button',{name:'Characters',exact:true}).click();await page.getByRole('button',{name:'Edit character',exact:true}).click();await page.getByLabel('Personality').fill('Patient.');await page.getByRole('button',{name:'Save character',exact:true}).click();await page.getByRole('button',{name:'Edit character',exact:true}).waitFor();await page.screenshot({path:out+'/mobile-editor.png',fullPage:true});}
}
await page.setViewportSize({width:1440,height:1000});failPlaces=true;await page.reload({waitUntil:'networkidle'});await page.getByText('Some story data could not load.').waitFor();await page.getByRole('button',{name:'Story Setup',exact:true}).waitFor();await page.screenshot({path:out+'/partial-failure.png',fullPage:true});failPlaces=false;await page.getByRole('button',{name:'Retry failed reads'}).click();await page.getByText('Some story data could not load.').waitFor({state:'hidden'});
assert.deepEqual(errors,[]);console.log('FIXTURES: creation/switching, metadata, character/place/Canon/scene edits, conflict review, generation, guidance, Workflow/Difficulty, Universe/assets, mobile edit, partial failure retry PASS. No overflow at 320/390/768/1024/1440. Screenshots: '+out);console.log('Writes validated: '+writes.length);
}finally{await browser.close();}
