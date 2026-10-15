"""Actual drawer checks at desktop/mobile widths; other projects must stay unchanged."""
import json,threading,shutil,os
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/tarsia-browser';OUT.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'docs')))
threading.Thread(target=server.serve_forever,daemon=True).start()
results=[]
try:
 with sync_playwright() as w:
  browser=w.chromium.launch(headless=True,executable_path=os.environ.get('WIND_BROWSER_EXECUTABLE'))
  for width,height in ((1440,1000),(390,844)):
   page=browser.new_page(viewport={'width':width,'height':height})
   errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.route('**/*',lambda route:route.continue_() if route.request.url.startswith('http://127.0.0.1:') else route.abort())
   page.goto(f'http://127.0.0.1:{server.server_port}/wind/',wait_until='domcontentloaded')
   row=page.locator('#opportunityRows [data-project-id="tarsia-ovest"]');row.wait_for();row.click()
   panel=page.locator('[data-documentary-project="tarsia-ovest"]');panel.wait_for()
   assert panel.locator('a[href="mailto:commerciale.system@plc-spa.com"]').count()==1
   assert panel.locator('a[href="tel:+390972536073"]').count()==1
   assert 'Delta S.r.l.' in panel.inner_text()
   assert panel.locator('a[href="mailto:ufficio.stampa@eniplenitude.com"]').count()==1
   assert page.locator('#drawer').get_attribute('aria-hidden')=='false'
   panel.scroll_into_view_if_needed();page.screenshot(path=str(OUT/f'tarsia-{width}.png'))
   overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth')
   panel_overflow=panel.evaluate('(e)=>e.scrollWidth>e.clientWidth+1')
   assert not overflow and not panel_overflow,(width,overflow,panel_overflow)
   page.locator('#closeDrawer').click()
   oid=page.locator('#opportunityRows [data-project-id]').evaluate_all("els=>els.map(e=>e.dataset.projectId).find(x=>x!=='tarsia-ovest')")
   page.locator(f'#opportunityRows [data-project-id="{oid}"]').click()
   assert page.locator('.documentary-summary').count()==0
   page.locator('#closeDrawer').click()
   serrarow=page.locator('#opportunityRows [data-project-id="serra-giannina"]')
   serrarow.wait_for()
   serrarow.click()
   sp=page.locator('[data-documentary-project="serra-giannina"]');sp.wait_for()
   assert '02094310766' in sp.inner_text()
   assert '06400370968' in sp.inner_text()
   assert 'Parzialmente' in sp.inner_text() or 'parzialmente' in sp.inner_text()
   assert sp.locator('a[href="mailto:info@egmproject.it"]').count()==1
   assert sp.locator('a[href="mailto:antonia.raino@rwe.com"]').count()==1
   assert sp.locator('a[href="tel:+393499341765"]').count()==1
   assert sp.locator('a[href$="1433468#page=14"]').count()==1
   assert '244 riferimenti residui' in sp.inner_text()
   assert '279' in sp.inner_text() and '30 PDF distinti' in sp.inner_text()
   sp.scroll_into_view_if_needed();page.screenshot(path=str(OUT/f'serra-{width}.png'))
   sp.locator('a[href="mailto:antonia.raino@rwe.com"]').scroll_into_view_if_needed()
   page.screenshot(path=str(OUT/f'serra-contacts-{width}.png'))
   sp.get_by_text('MASE – quattro indici verificati',exact=True).scroll_into_view_if_needed()
   page.screenshot(path=str(OUT/f'serra-coverage-{width}.png'))
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
   assert not sp.evaluate('(e)=>e.scrollWidth>e.clientWidth+1')
   assert not errors,errors
   results.append({'viewport':[width,height],'contacts_visible':True,'other_project_unchanged':True,'overflow':False,'javascript_errors':errors})
   page.close()
  browser.close()
finally:server.shutdown();server.server_close()
(OUT/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results))
