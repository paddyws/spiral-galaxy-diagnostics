/* Read-only display of saved geometry. No fitting or smoothing is performed here. */
'use strict';
const D=JSON.parse(document.getElementById('pitchData').textContent), params=new URLSearchParams(location.search);
const controls={method:document.getElementById('method'),group:document.getElementById('track'),image:document.getElementById('image'),overlay:document.getElementById('overlay'),labels:document.getElementById('labels'),boundary:document.getElementById('boundary')};
if(params.has('embed'))document.body.classList.add('embedded');
const escapeText=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite=(n,d=1)=>n===null||n===undefined?'—':Number(n).toFixed(d);
function selected(){return D.methods[controls.method.value];}
function selectedCurves(){return selected().curves.filter(c=>controls.group.value==='all'||c.group===controls.group.value);}
function backgroundName(plane){return 'images/'+D.stem+'/'+plane+'_'+controls.image.value+'.png?v='+D.version;}
function paint(plane,companions=false){
 const element=document.getElementById(companions?'gap-face':plane+'-overlay');
 const curves=selectedCurves(),mode=controls.overlay.value;let out='';
 if(controls.boundary.checked){const a=D.boundaries[plane];out+='<path d="'+a.outer+'" fill="none" stroke="#dfe8f4" stroke-opacity=".62" stroke-width="1.2" stroke-dasharray="3 6"/><path d="'+a.inner+'" fill="none" stroke="#9ba6b7" stroke-opacity=".65" stroke-width="1" stroke-dasharray="5 6"/>';}
 const center=D.boundaries[plane].center;
 out+='<path d="M'+(center[0]-5)+','+center[1]+'h10 M'+center[0]+','+(center[1]-5)+'v10" stroke="white" stroke-opacity=".65" stroke-width="1"/>';
 if(mode!=='none'){
   for(const c of curves){const v=c[plane];
     if(mode!=='points'){
       out+='<path d="'+v.curve+'" fill="none" stroke="'+c.color+'" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>';
       if(companions)out+='<path d="'+v.gap+'" fill="none" stroke="'+c.color+'" stroke-width="1.4" stroke-dasharray="5 6"/>';
     }
     if(mode==='both'||mode==='points')for(const p of v.points)out+='<circle cx="'+p[0]+'" cy="'+p[1]+'" r="2.3" fill="'+c.color+'" stroke="#10151d" stroke-width=".85"/>';
   }
   if(controls.labels.checked){for(const l of selected().labels[plane]){
     if(controls.group.value!=='all'&&l.group!==controls.group.value)continue;
     const b=l.box,a=l.anchor,e=l.end;
     out+='<g class="pitch-label" data-group="'+escapeText(l.group)+'"><path d="M'+a.join(',')+' L'+e.join(',')+'" fill="none" stroke="'+l.color+'" stroke-width="1.15"/><rect x="'+b[0]+'" y="'+b[1]+'" width="'+(b[2]-b[0])+'" height="'+(b[3]-b[1])+'" rx="4" fill="#0e1620" fill-opacity=".95" stroke="'+l.color+'"/><text x="'+(b[0]+6)+'" y="'+(b[1]+18.5)+'" font-family="Arial,sans-serif" font-size="17" font-weight="bold" fill="'+l.color+'">'+escapeText(l.text)+'</text></g>';
   }}
 }
 element.innerHTML=out;
 element.querySelectorAll('.pitch-label').forEach(g=>g.addEventListener('click',()=>{controls.group.value=g.dataset.group;render();}));
}
function table(){
 const curves=selectedCurves();let out='';
 for(const c of curves){const range=c.variable?(finite(c.range[0])+'–'+finite(c.range[1])+'°'):'Constant-pitch fit';
   const support=c.raw_available?((controls.method.value==='sparcfire'?'Cluster pixels':'Fitted points')+': '+c.raw_count+(c.display_raw_count<c.raw_count?' ('+c.display_raw_count+' displayed)':'')):'No detected point set (inferred Fourier ridge)';
   out+='<tr><td style="color:'+c.color+'"><button class="pick-track" data-group="'+escapeText(c.group)+'">'+escapeText(c.group)+'</button></td><td>'+finite(c.pitch,2)+'°'+(c.variable?' ~':'')+'</td><td>'+range+'</td><td>'+escapeText(support)+'</td><td>'+c.gap_count+'</td></tr>';
 }
 if(!curves.length)out='<tr><td colspan="5">No retained geometry for this method.</td></tr>';
 document.getElementById('track-body').innerHTML=out;
 document.querySelectorAll('.pick-track').forEach(el=>el.addEventListener('click',()=>{controls.group.value=el.dataset.group;render();}));
}
function chooseMethod(){
 const groups=[...new Set(selected().curves.map(c=>c.group))];
 controls.group.innerHTML='<option value="all">All tracks / components</option>'+groups.map(g=>'<option value="'+escapeText(g)+'">'+(controls.method.value==='fourier'?'Component ':'Track ')+escapeText(g)+'</option>').join('');
 controls.group.value='all';render();
}
function render(){
 for(const plane of ['native','face']){
   const image=document.getElementById(plane+'-image'),src=backgroundName(plane);
   if(image.getAttribute('src')!==src)image.src=src;
   paint(plane);
 }
 const gapImage=document.getElementById('gap-image');if(gapImage.getAttribute('src')!==backgroundName('face'))gapImage.src=backgroundName('face');paint('face',true);
 document.getElementById('method-title').textContent=selected().name;
 const curves=selectedCurves(),raw=curves.reduce((s,c)=>s+c.raw_count,0),gaps=curves.some(c=>c.has_inferred_gaps);
 document.getElementById('support-note').textContent=selected().notes+(raw?' Circles show saved fitted points; selecting one track reduces clutter.':' No point detections are fabricated for a Fourier component.')+(gaps?' Internal gap connections appear only in the expandable companion below.':'');
 document.getElementById('gap-details').hidden=!gaps;
 document.getElementById('empty-note').hidden=curves.length>0;
 document.getElementById('image-note').textContent=controls.image.value==='color'?'Multiband color reference only. The checkerboard marks positions outside the available color image.':controls.image.value==='g'?'Actual unfiltered, sky-subtracted g-band data, with the existing photometric stretch.':'Actual unfiltered residual: (original − sky) − (bulge + disk + bar). Red is positive residual, blue is excess model light. The same signed stretch is used in both frames.';
 table();notifyHeight();
}
function notifyHeight(){requestAnimationFrame(()=>{if(parent!==window)parent.postMessage({type:'faceon-pitch-view-height',stem:D.stem,height:Math.ceil(document.getElementById('app').getBoundingClientRect().height+36)},'*');});}
controls.method.value=(params.get('method') in D.methods)?params.get('method'):'radial_tracks';
controls.method.addEventListener('change',chooseMethod);
for(const c of [controls.group,controls.image,controls.overlay,controls.labels,controls.boundary])c.addEventListener('change',render);
document.querySelectorAll('img').forEach(im=>im.addEventListener('load',notifyHeight));
document.getElementById('gap-details').addEventListener('toggle',notifyHeight);
window.addEventListener('resize',notifyHeight);
new ResizeObserver(notifyHeight).observe(document.getElementById('app'));
chooseMethod();
