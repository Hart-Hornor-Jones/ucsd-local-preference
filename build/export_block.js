/* ================================================================
   EXPORT FIGURE — PNG at 2x / 4x, copy to clipboard, CSV of the plotted schools.
   Waits for a plot's animation queue to empty, then re-renders the plot off-screen
   at the chosen scale inside a composite with title, era, stats and source line.
================================================================ */
var VIEW_WORDS={joint:'Joint distribution',x:'Distribution of X',y:'Distribution of Y',r:'Distribution of residuals'};
function plotView(k){ return (k===1)?st.view:entryOf(k).state.view; }
function allSettled(){ return chain.every(function(c){ return c.plot.isSettled(); }); }
function whenSettled(fn,note){
  var t0=performance.now();
  (function poll(){
    if(allSettled()){ fn(); return; }
    if(performance.now()-t0>8000){ if(note) note('the plot is still moving — try again when it has settled'); return; }
    if(note) note('waiting for the plot to settle…');
    setTimeout(poll,120);
  })();
}
function wrapLines(ctx,text,maxW){
  var words=String(text).split(/\s+/), lines=[], cur='';
  words.forEach(function(w){
    var t=cur?cur+' '+w:w;
    if(ctx.measureText(t).width>maxW&&cur){ lines.push(cur); cur=w; } else cur=t;
  });
  if(cur) lines.push(cur);
  return lines;
}
function figureTitle(k){
  if(k===1) return document.querySelector('h1').textContent;
  return 'Plot '+k+' — the residuals of Plot '+(k-1)+', against a third measure';
}
function figureSource(){
  var d=new Date(), ds=d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2);
  return 'University of California admissions by source school; California Department of Education. Exported '+ds+'.';
}
function figureCanvas(k,scale){
  var e=entryOf(k), p=e.plot, sz=p.getSize();
  var plotCv=p.renderTo(scale);
  var W=sz.W, pad=16, gap=6;
  var meas=document.createElement('canvas').getContext('2d');
  meas.font='bold 15px Arial'; var tl=wrapLines(meas,figureTitle(k),W-2*pad);
  meas.font='bold 11.5px Arial';
  var subText=yLong(st.year)+' · '+VIEW_WORDS[plotView(k)]+(k>1?(' · residuals of Plot '+(k-1)+' inherited'):'');
  var sl=wrapLines(meas,subText,W-2*pad);
  var stats=(k===1)?trendStatsText():childStatsText(k);
  meas.font='bold 11px Arial'; var stl=stats?wrapLines(meas,stats,W-2*pad):[];
  meas.font='11px Arial'; var srl=wrapLines(meas,figureSource(),W-2*pad);
  var headH=pad+tl.length*19+sl.length*15+gap, footH=stl.length*14+srl.length*13+pad+gap;
  var H=headH+sz.H+footH;
  var out=document.createElement('canvas'); out.width=Math.round(W*scale); out.height=Math.round(H*scale);
  var c=out.getContext('2d'); c.setTransform(scale,0,0,scale,0,0);
  c.fillStyle='#fff'; c.fillRect(0,0,W,H);
  c.fillStyle='#000'; c.textAlign='left'; c.textBaseline='top';
  var y=pad; c.font='bold 15px Arial'; tl.forEach(function(t){ c.fillText(t,pad,y); y+=19; });
  c.font='bold 11.5px Arial'; c.fillStyle='#333'; sl.forEach(function(t){ c.fillText(t,pad,y); y+=15; });
  y+=gap;
  c.setTransform(1,0,0,1,0,0); c.drawImage(plotCv,0,Math.round(y*scale)); c.setTransform(scale,0,0,scale,0,0);
  y+=sz.H+gap;
  c.font='bold 11px Arial'; c.fillStyle='#000'; stl.forEach(function(t){ c.fillText(t,pad,y); y+=14; });
  c.font='11px Arial'; c.fillStyle='#444'; srl.forEach(function(t){ c.fillText(t,pad,y); y+=13; });
  return out;
}
function figureFileName(k,ext,scale){
  var v=plotView(k), yl=yLabel(st.year).replace(/[^\w]+/g,'-').replace(/^-|-$/g,'');
  return 'ucsd-local-preference_plot'+k+'_'+yl+'_'+v+(scale?('_'+scale+'x'):'')+'.'+ext;
}
function downloadBlob(blob,name){
  var a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(function(){URL.revokeObjectURL(a.href);},2000);
}
function csvOfPlot(k){
  var e=entryOf(k), p=e.plot, pts=p.getPoints(), sp=p.getSpecs(), f=p.getFit();
  var xl=sp.x?sp.x.axisLabel(st.year):'x', yl=sp.y?sp.y.axisLabel(st.year):'y';
  var cm=(st.colorBy!=='none'&&st.colorBy!=='size')?MEASURES[MIDX[st.colorBy]]:null;
  function q(s){ s=String(s==null?'':s); return /[",\n]/.test(s)?('"'+s.replace(/"/g,'""')+'"'):s; }
  var head=['# '+figureTitle(k),'# '+yLong(st.year)+' · '+VIEW_WORDS[plotView(k)],
            '# '+((k===1)?trendStatsText():childStatsText(k)),'# '+figureSource()];
  var cols=['school','ceeb','x: '+xl,'y: '+yl,'fitted','residual','ucsd_applicants_per_year'];
  if(cm) cols.push('color: '+cm.label);
  var rows=[cols.map(q).join(',')];
  pts.forEach(function(pt){
    var fit=null;
    if(f){ fit=f.eq?pt.x:(f.xsect?f.slope*pt.x:(f.slope*pt.x+f.icept)); }
    var r=[names[pt.i],(PANEL.ceeb?PANEL.ceeb[pt.i]:''),pt.x,pt.y,fit==null?'':fit.toFixed(4),fit==null?'':(pt.y-fit).toFixed(4),pt.w];
    if(cm){ var v=pt.cv; r.push(v==null?'':(cm.unit==='cat'?cm.cats[Math.max(0,Math.min(cm.cats.length-1,Math.round(v)))]:v)); }
    rows.push(r.map(q).join(','));
  });
  return head.concat(rows).join('\n');
}
function exportPlot(k,kind,note){
  whenSettled(function(){
    try{
      if(kind==='csv'){
        downloadBlob(new Blob([csvOfPlot(k)],{type:'text/csv'}),figureFileName(k,'csv'));
        note('CSV saved'); return;
      }
      var scale=(kind==='png4')?4:2;
      var out=figureCanvas(k,scale);
      if(kind==='copy'){
        if(!(navigator.clipboard&&window.ClipboardItem)){ note('copying needs a recent browser — use PNG instead'); return; }
        out.toBlob(function(b){
          navigator.clipboard.write([new ClipboardItem({'image/png':b})]).then(function(){note('copied to the clipboard');},function(){note('the browser refused the copy — use PNG instead');});
        },'image/png');
        return;
      }
      out.toBlob(function(b){ downloadBlob(b,figureFileName(k,'png',scale)); note('PNG '+scale+'× saved'); },'image/png');
    }catch(err){ note('export failed: '+err.message); }
  },note);
}
function wireExport(k,dom){
  var open=false;
  function setOpen(v){ open=v; dom.expMenu.style.display=v?'block':'none'; dom.expBtn.setAttribute('aria-expanded',String(v)); }
  function note(msg){ dom.expNote.textContent=msg; clearTimeout(dom.expNote._t); dom.expNote._t=setTimeout(function(){dom.expNote.textContent='';},3500); }
  dom.expBtn.addEventListener('click',function(){ setOpen(!open); });
  dom.expBtn.addEventListener('keydown',function(e){ if(e.key==='Enter'||e.key===' '){e.preventDefault();setOpen(!open);} });
  Array.prototype.forEach.call(dom.expMenu.querySelectorAll('button'),function(b){
    b.addEventListener('click',function(){ setOpen(false); exportPlot(k,b.dataset.kind,note); });
  });
  document.addEventListener('click',function(e){ if(open&&!dom.expWrap.contains(e.target)) setOpen(false); });
}
window.UCSDEXPORT={figureCanvas:figureCanvas,csvOfPlot:csvOfPlot,exportPlot:exportPlot};
