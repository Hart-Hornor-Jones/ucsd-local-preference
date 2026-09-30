"""Step 2 of the build: add the EXPORT FIGURE menu (PNG 2x/4x, copy, CSV) to ../index.html.
Run from build/ AFTER splice_page.py: python3 splice_export.py"""
missed=[]
def rep(old,new,label=None):
    global html
    if old not in html: missed.append(label or old[:60]); return
    html=html.replace(old,new,1)
# ================= EXPORT FIGURE (added 9/30) =================
EXP=open('export_block.js',encoding='utf-8').read()
html=open('../index.html',encoding='utf-8').read()
missed=[]
rep("  .pctl:hover,.pkill:hover{background:#f1f1f1;}",
 "  .pctl:hover,.pkill:hover{background:#f1f1f1;}\n  .pexpwrap{position:relative;display:inline-block;}\n  .pexp{display:inline-block;border:2px solid #000;background:#fff;color:#000;font-size:11px;font-weight:700;letter-spacing:.05em;padding:2px 9px;cursor:pointer;user-select:none;}\n  .pexp:hover{background:#f1f1f1;}\n  .pmenu{position:absolute;top:26px;left:0;background:#fff;border:2px solid #000;z-index:40;min-width:210px;display:none;}\n  .pmenu button{display:block;width:100%;text-align:left;border:0;background:#fff;font:inherit;font-size:11.5px;font-weight:700;padding:5px 10px;cursor:pointer;}\n  .pmenu button:hover{background:#f1f1f1;}\n  .pexpnote{font-size:10.5px;font-weight:700;color:#333;}",'export css')
rep("  bar.appendChild(ctlBtn);\n  var killBtn=null;",
 "  bar.appendChild(ctlBtn);\n  var expWrap=document.createElement('span'); expWrap.className='pexpwrap';\n  var expBtn=document.createElement('a'); expBtn.className='pexp'; expBtn.setAttribute('role','button'); expBtn.tabIndex=0; expBtn.setAttribute('aria-haspopup','true'); expBtn.setAttribute('aria-expanded','false'); expBtn.textContent='EXPORT FIGURE \\u25BE';\n  var expMenu=document.createElement('div'); expMenu.className='pmenu';\n  [['png2','PNG at 2\\u00d7'],['png4','PNG at 4\\u00d7'],['copy','Copy PNG to clipboard'],['csv','CSV of the plotted schools']].forEach(function(d){ var b=document.createElement('button'); b.dataset.kind=d[0]; b.textContent=d[1]; expMenu.appendChild(b); });\n  expWrap.appendChild(expBtn); expWrap.appendChild(expMenu); bar.appendChild(expWrap);\n  var expNote=document.createElement('span'); expNote.className='pexpnote'; bar.appendChild(expNote);\n  var killBtn=null;",'export menu dom')
rep("  return {sec:sec, btns:btns, ctlBtn:ctlBtn, killBtn:killBtn, canvas:cv};",
 "  return {sec:sec, btns:btns, ctlBtn:ctlBtn, killBtn:killBtn, canvas:cv, expWrap:expWrap, expBtn:expBtn, expMenu:expMenu, expNote:expNote};",'export dom return')
rep("  self.rebuild=rebuild;\n  self.draw=draw;",
 "  self.isSettled=function(){ return queue.length===0; };\n  self.getSize=function(){ return {W:W,H:H}; };\n  self.renderTo=function(scale){\n    var off=document.createElement('canvas'); off.width=Math.round(W*scale); off.height=Math.round(H*scale);\n    var sc=cv, sx=ctx; cv=off; ctx=off.getContext('2d'); ctx.setTransform(scale,0,0,scale,0,0);\n    try{ draw(); } finally { cv=sc; ctx=sx; }\n    return off;\n  };\n  self.rebuild=rebuild;\n  self.draw=draw;",'plot export methods')
rep("  dom.ctlBtn.addEventListener('click',function(){ setCtrl(!ctrlShown); });",
 "  dom.ctlBtn.addEventListener('click',function(){ setCtrl(!ctrlShown); });\n  wireExport(k,dom);",'wire export')
rep("fillSelect(xsel); fillSelect(ysel); fillColorSel();\nxsel.value='ucsd_app_gpa';",
 EXP+"\nfillSelect(xsel); fillSelect(ysel); fillColorSel();\nxsel.value='ucsd_app_gpa';",'export block')
open('../index.html','w',encoding='utf-8').write(html)
print('export missed:',missed,'bytes',len(html))
