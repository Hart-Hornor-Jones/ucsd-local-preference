"""Assemble index.html for the UCSD local-preference visualizer from the ca-hs-proficiency page:
same engine, new embedded panel, new measure dictionary, era labels on the year slider, and a
categorical color mode (districts, counties, distance bands, terciles, quota status).
Run from build/: python3 splice_page.py"""
import sys
src=open('../../ca-hs-proficiency/index.html',encoding='utf-8').read()
blob=open('panel_blob.json').read()
MEAS=open('measures_block.js',encoding='utf-8').read()
html=src
missed=[]
def rep(old,new,label=None):
    global html
    if old not in html: missed.append(label or old[:60]); return
    html=html.replace(old,new,1)
# ---------- 1. head text ----------
rep('<title>Comparing Measures of Academic Proficiency — California High Schools</title>','<title>Admission to UCSD: Trends and Surprises</title>')
rep('<h1>How do different measures of academic proficiency relate?</h1>','<h1>Admission to UCSD: Trends and Surprises</h1>')
i0=html.find('<p class="intro">'); i1=html.find('</p>',i0)+4
html=html[:i0]+'''<p class="intro">Each dot is one California public high school with freshman applicants to UC San Diego. Choose a measure for each axis, a year or a period (the slider runs 1994–2025 and then through seven multi-year periods), and a coloring. Fit a trend line to open the residual views; <b>Joint distribution of residuals</b> adds a plot of the residuals against another measure. Click a dot to tag its school; double-click to clear. Scroll over a plot to zoom.</p>'''+html[i1:]
fs=html.find('<div class="footer" id="datafooter">'); fe=html.find('</div>',fs)+6
html=html[:fs]+'''<div class="footer" id="datafooter">Admissions figures: University of California, freshman admissions by source school, California public high schools, fall 1994–2025. School characteristics: California Department of Education. Predicted admit rates are fitted each year on schools outside San Diego and Imperial counties as a function of mean applicant GPA.</div>'''+html[fe:]
rep('<div class="fine">Colors are shared: the same school keeps the same color on every plot.</div>','')
rep('<input type="range" id="year" min="1994" max="2025" step="1" value="2020">','<input type="range" id="year" min="1994" max="2032" step="1" value="2031">')
rep('<div class="lab lab-year">Year</div>','<div class="lab lab-year">Year or period</div>')
# ---------- 2. panel blob ----------
a=html.find('var PANEL='); b=html.find('\n',a)
html=html[:a]+'var PANEL='+blob+';'+html[b:]
rep('1. REAL PANEL — California public high schools, 1994–2025.','1. PANEL — California public high schools with UCSD applicants, fall 1994–2025 plus seven pooled eras at pseudo-years 2026–2032.')
# ---------- 3. measures block ----------
a=html.find('var MEASURES=['); b=html.find('var CTX_KEYS='); b=html.find('\n',b)+1
html=html[:a]+MEAS+html[b:]
# ---------- 4. units ----------
rep("usd:'dollars', flag:'yes/no', stud:'students per grade', nmsf:'semifinalists', per100:'semifinalists per 100 students', nstud:'students'};",
 "usd:'dollars', flag:'yes/no', stud:'students', nstud:'students', pts:'percentage points', mi:'miles', cat:'category', seats:'seats', ratio:'applicants per seat', per100s:'applicants per 100 seniors', yrs:'years', lo:'log-odds', lor:'log odds ratio'};",'units')
# ---------- 5. defaults ----------
rep("var st={ xid:'gpa_uc', xDelta:false, xFrom:'sel', xTo:2025,\n         yid:'uc_grad4', yDelta:false, yFrom:'sel', yTo:2025,\n         year:2020, view:'joint', colorBy:'caaspp_math',",
 "var st={ xid:'ucsd_app_gpa', xDelta:false, xFrom:'sel', xTo:2025,\n         yid:'ucsd_admit', yDelta:false, yFrom:'sel', yTo:2025,\n         year:2031, view:'joint', colorBy:'local',",'st defaults')
rep("zid:'caaspp_math' };","zid:'dist' };",'zid')
rep("var prefs=['caaspp_math','","var prefs=['dist','apps_per100','oth_admit','ctx_urg','caaspp','",'prefs')
rep("if(!sel.querySelector('option[value=\"'+cur+'\"]')) sel.value='caaspp';","if(!sel.querySelector('option[value=\"'+cur+'\"]')) sel.value='dist';",'zsel default')
# ---------- 6. categorical colors ----------
rep("var CBASE=[[0,0,255],[17,128,64],[255,140,0],[251,2,7]], CGRAY=[125,125,125];",
 "var CBASE=[[0,0,255],[17,128,64],[255,140,0],[251,2,7],[122,0,204],[175,175,175],[139,74,0],[230,0,126]], CGRAY=[125,125,125];",'CBASE')
rep("    var lab, cy=null, dec=0, isFlag=false;\n    if(st.colorBy==='size'){\n      lab='school size (students per grade)';",
 "    var lab, cy=null, dec=0, isFlag=false, cats=null;\n    if(st.colorBy==='size'){\n      lab='UCSD applicants per year (average)';",'size label')
rep("      lab=cm.label; dec=cm.dec; isFlag=(cm.unit==='flag');",
 "      lab=cm.label; dec=cm.dec; isFlag=(cm.unit==='flag'); cats=(cm.unit==='cat')?cm.cats:null;",'cats detect')
rep("    if(shared){ cuts=shared.cuts; twoWay=shared.twoWay; }\n    else if(isFlag){ cuts=[0.5]; twoWay=true; }",
 "    if(shared){ cuts=shared.cuts; twoWay=shared.twoWay; cats=shared.cats||null; }\n    else if(cats){ cuts=[]; }\n    else if(isFlag){ cuts=[0.5]; twoWay=true; }",'shared cuts')
rep("      if(p.cv==null){p.ci=-1;missing=true;}\n      else if(twoWay) p.ci=(p.cv<=cuts[0])?0:3;",
 "      if(p.cv==null){p.ci=-1;missing=true;}\n      else if(cats) p.ci=Math.max(0,Math.min(cats.length-1,Math.round(p.cv)));\n      else if(twoWay) p.ci=(p.cv<=cuts[0])?0:3;",'ci assign')
rep("    colorInfo={label:lab, year:(shared?shared.year:cy), cuts:cuts, dec:dec,\n               missing:missing, twoWay:twoWay};",
 "    colorInfo={label:lab, year:(shared?shared.year:cy), cuts:cuts, dec:dec,\n               missing:missing, twoWay:twoWay, cats:cats};",'colorInfo')
rep("      if(colorInfo.twoWay){ labels=['no','yes']; keys=[0,3]; }\n      else { labels=",
 "      if(colorInfo.cats){ labels=colorInfo.cats.slice(); keys=labels.map(function(_,q){return q;}); }\n      else if(colorInfo.twoWay){ labels=['no','yes']; keys=[0,3]; }\n      else { labels=",'legend')
rep("      var head='dots colored by '+colorInfo.label+(colorInfo.year?(' ('+colorInfo.year+')'):'')+':';",
 "      var head='dots colored by '+colorInfo.label+(colorInfo.year?(' ('+yLabel(colorInfo.year)+')'):'')+':';",'legend head')
rep("      html+='<br>'+colorInfo.label+(colorInfo.year?(' ('+colorInfo.year+')'):'')\n        +': <b>'+p2.cv.toFixed(colorInfo.dec)+'</b>';",
 "      html+='<br>'+colorInfo.label+(colorInfo.year?(' ('+yLabel(colorInfo.year)+')'):'')\n        +': <b>'+(colorInfo.cats?colorInfo.cats[Math.max(0,Math.min(colorInfo.cats.length-1,Math.round(p2.cv)))]:p2.cv.toFixed(colorInfo.dec))+'</b>';",'tooltip color')
rep("      +(p2.w>0?('about '+p2.w+' students per grade'):'school size not on file');","      +(p2.w>0?('about '+p2.w+' UCSD applicants per year'):'applicant count not on file');",'tooltip size')
rep("[['none','nothing — all dots red'],['size','school size']]","[['none','nothing — all dots red'],['size','UCSD applicants per year']]",'csel plain')
# ---------- 7. era labels ----------
rep("yearVal.textContent=yearEl.disabled?'— (not in use)':String(st.year);","yearVal.textContent=yearEl.disabled?'— (not in use)':yLong(st.year);",'yearVal')
rep("c.side.yrnote.textContent='Follows Plot 1’s Year slider — currently '+st.year+'.';","c.side.yrnote.textContent='Follows Plot 1’s Year slider — currently '+yLabel(st.year)+'.';",'yrnote')
rep("return 'X: '+w(xs)+' · Y: '+w(ys)+zpart+'.'+tail+' A year means the spring of that school year ('+st.year+' = '+(st.year-1)+'–'+String(st.year).slice(2)+'); the GPA and college-outcome measures use the fall their class entered college.';",
 "return 'X: '+w(xs)+' · Y: '+w(ys)+zpart+'.'+tail+'';",'coverage tail')
rep("    if(!spec.delta) return m.y0+'–'+m.y1+(m.skip.length?(' (not '+m.skip.join(', ')+')'):'');","    if(!spec.delta) return m.y0+'–'+Math.min(m.y1,2025)+(m.skip.filter(function(v){return v<2026;}).length?(' (not '+m.skip.filter(function(v){return v<2026;}).join(', ')+')'):'')+' and periods';",'coverage w')
rep("      return 'Change in '+m.axis+', '+res(from,sel)+'→'+res(to,sel);};","      return 'Change in '+m.axis+', '+yLabel(res(from,sel))+'→'+yLabel(res(to,sel));};",'delta axis label')
rep("    if(to!=='sel'&&y>=to) continue; opt(fEl,y,y,from); }","    if(to!=='sel'&&y>=to) continue; opt(fEl,y,yLabel(y),from); }",'span from')
rep("    if(from!=='sel'&&y2<=from) continue; opt(tEl,y2,y2,to); }","    if(from!=='sel'&&y2<=from) continue; opt(tEl,y2,yLabel(y2),to); }",'span to')
rep("function spanWord(e){return e==='sel'?'the selected year':String(e);}","function spanWord(e){return e==='sel'?'the selected year':yLabel(e);}",'spanWord')
rep("across schools in '+f1.xsYear+'","across schools in '+yLabel(f1.xsYear)+'",'xsYear')
rep("    spec.axisLabel=function(sel){return m.axis;};","    spec.axisLabel=function(sel){return m.axis+(ERAS[sel]?(', '+ERAS[sel][0]):'');};",'axisLabel era')
rep("xsel.value='gpa_uc'; ysel.value='uc_grad4';","xsel.value='ucsd_app_gpa'; ysel.value='ucsd_admit';",'init selects')
rep("'ctx_upp','ctx_urg','ctx_tract_inc','caaspp','ag'];","'ctx_upp','ctx_lcff','gpa_prem'];",'prefs tail')
rep("  else tail=' The slider is limited to years the whole chain of plots can use.';","  else tail='';",'cov tail 1')
rep("  if(yearEl.disabled&&xs.usesSlider&&ys.usesSlider){tail=' These two measures never overlap in time — no single year can show both. To compare them anyway, put a “Change in” span on one axis, or pick a contemporary of the other.';}","  if(yearEl.disabled&&xs.usesSlider&&ys.usesSlider){tail=' These two measures share no year.';}",'cov tail 2')
rep("    zpart+=' · Plot '+c.kk+' against: '+zm.label+' ('+zm.y0+'–'+zm.y1+')';","    zpart+=' · Plot '+c.kk+': '+zm.label+' ('+zm.y0+'–'+Math.min(zm.y1,2025)+')';",'cov zpart')
# ---------- 8. method text ----------
rep("parts.push('<b>Each dot is one high school.</b> Click a dot","parts.push('<b>Each dot is one high school.</b> In a period, each measure pools the period’s years. Click a dot",'method open')
rep("parts.push('Every number here is a published school-level figure — sources are under the chart.","parts.push('",'method close')
# ---------- 9. draw order: gray / plain dots first, colored group dots on top ----------
rep("    for(var i=0;i<N;i++){\n      var P=screenPos(i,G);\n      if(!P) continue;\n      var base=dotBase(pts[i]);",
 "    var ordr=[]; for(var i0=0;i0<N;i0++) ordr.push(i0);\n    ordr.sort(function(a,b){ var ra=(pts[a].ci===5||pts[a].ci<0)?0:1, rb=(pts[b].ci===5||pts[b].ci<0)?0:1; return ra-rb; });\n    for(var ii=0;ii<N;ii++){\n      var i=ordr[ii];\n      var P=screenPos(i,G);\n      if(!P) continue;\n      var base=dotBase(pts[i]);",'draw order')
open('../index.html','w',encoding='utf-8').write(html)
print('missed:',missed); print('bytes',len(html))
