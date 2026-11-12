// B2a UI and request-contract acceptance; authenticated responses are fixtures.
import assert from 'node:assert/strict';
import fs from 'node:fs';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const out=(process.env.HOME_SCREENSHOTS || new URL('../docs/design-reference/phase-b2a-review/screenshots/',import.meta.url).pathname).replace(/\/$/,'')+'/';
fs.mkdirSync(out,{recursive:true});
const styles=JSON.parse(fs.readFileSync(new URL('../../backend/app/creative_direction/styles.json',import.meta.url)));
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
const measurements=[],errors=[];
try {
 for(const locale of ['en','id']){
  const context=await browser.newContext({ignoreHTTPSErrors:true,locale:'id-ID',viewport:{width:1440,height:900}});
  if(locale==='id')await context.addInitScript(()=>localStorage.setItem('sandcastle.uiLocale','id'));
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));const writes=[];
  await page.route('**/api/**',async route=>{
   const req=route.request(),p=new URL(req.url()).pathname;
   if(!p.startsWith('/api/'))return route.continue();
   if(req.method()!=='GET')writes.push(p);
   const data=p==='/api/auth/me'?{user_id:'home-fixture',name:'Writer'}:p==='/api/stories'?[]:p==='/api/styles'?styles:p==='/api/styles/recommend'?{target_format:'webtoon',primary_genre:'romance',secondary_genres:['drama'],storytelling_style_id:'korean_romance_drama',audience_rating:'teen_13',language:'id',visual_style:'match_style',tone:'Emotional',rationale:'Fixture direction for review.',warnings:[]}:null;
   assert.notEqual(data,null,'Unexpected API '+p);await route.fulfill({json:data});
  });
  await page.goto(process.env.WORKSPACE_ORIGIN||'https://192.168.0.99:5182',{waitUntil:'networkidle'});
  assert.equal(await page.locator('html').getAttribute('lang'),locale);
  const home=page.locator('.studio-home');
  for(const width of [1440,390,320]){
   await page.setViewportSize({width,height:width===1440?900:844});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.equal(overflow,false);
   await page.screenshot({path:`${out}/home-${locale}-${width}.png`,fullPage:true});
   await page.screenshot({path:`${out}/viewport-${locale}-${width}.png`});
   const composerBounds=await home.locator(".idea-card").boundingBox();
   const inspirationBounds=await home.locator(".home-inspiration").boundingBox();
   assert(composerBounds.y<inspirationBounds.y,"Composer must precede inspiration");
   measurements.push({locale,width,overflow,composerBeforeInspiration:true});
  }
  await page.setViewportSize({width:1440,height:900});
  const idea=home.locator('.idea-card textarea');await idea.fill('My unsaved idea');
  await home.locator('.home-inspiration button').first().click();assert.match(await idea.inputValue(),/^My unsaved idea\n/);
  assert.equal(await idea.evaluate(e=>e===document.activeElement),true);
  await page.keyboard.press('Tab');assert.equal(await home.locator('.home-output-language select').evaluate(e=>e===document.activeElement),true);
  assert.equal(await page.evaluate(()=>getComputedStyle(document.activeElement).outlineStyle),'solid');
  const draft=await idea.inputValue();await home.locator('.create-paths button').nth(1).click();
  const source=home.locator('.import-entry textarea');await source.fill('Unfinished import text');
  await home.locator('.create-paths button').first().click();assert.equal(await idea.inputValue(),draft);
  await home.locator('.create-paths button').nth(1).click();assert.equal(await source.inputValue(),'Unfinished import text');
  await home.locator('.create-paths button').first().click();
  await page.locator('.studio-language select').selectOption(locale==='en'?'id':'en');assert.equal(await idea.inputValue(),draft);
  await page.locator('.studio-language select').selectOption(locale);
  await home.locator('.format-choices button').nth(1).click();
  await home.locator('.idea-card .primary-button').click();await home.locator('.direction-review').waitFor();
  assert.equal(await home.locator('.direction-review select').first().inputValue(),'id');
  assert.deepEqual(writes,['/api/styles/recommend']);
  for(const width of [1440,390,320]){
   await page.setViewportSize({width,height:width===1440?900:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   await page.screenshot({path:`${out}/review-${locale}-${width}.png`,fullPage:true});
  }
  await context.close();
 }
 assert.deepEqual(errors,[]);fs.writeFileSync(out+'measurements.json',JSON.stringify({measurements,errors,fixtureOnly:true},null,2));
 console.log('PASS B2a: EN default on ID browser, explicit ID, 1440/390/320 no overflow, inspiration appends/focuses, new/import draft retention, locale draft retention, real recommendation request contract, reviewed output language and no auto creation.');
}finally{await browser.close();}
