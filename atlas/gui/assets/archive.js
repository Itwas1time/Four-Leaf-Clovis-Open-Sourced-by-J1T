(function(){
  let scale=1, angle=0, local=false, down=null;
  const status=text=>{const el=document.getElementById('archive-image-status');if(el)el.textContent=text;};
  function paint(image,box){image.style.display='block';image.style.width=(100*scale)+'%';image.style.maxWidth='none';image.style.height='auto';image.style.transform='rotate('+angle+'deg)';image.style.transformOrigin='center center';box.style.cursor='grab';}
  window.clovisArchive={view:function(upload,sheet,sheets,selected,zin,zout,fit,rotate,state,geoid){
    const image=document.getElementById('archive-image'),box=document.getElementById('archive-image-viewport');
    if(!image||!box)return window.dash_clientside.no_update;
    const trigger=window.dash_clientside.callback_context.triggered_id;
    if(trigger==='resident-state'||trigger==='resident-place'){local=false;image.removeAttribute('src');image.style.display='none';document.getElementById('archive-image-empty').style.display='block';window.dash_clientside.set_props('archive-source-mode',{data:null});window.dash_clientside.set_props('archive-local-title',{value:''});status('Town changed. Search maps again or reopen a local image for this town.');return Date.now();}
    let source=null;
    if(trigger==='archive-upload'){
      if(typeof upload!=='string'||upload.length>16800000||!/^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(upload)) {status('Choose a JPEG, PNG or WebP map under 12 MB.');return Date.now();}
      source=upload;local=true;window.dash_clientside.set_props('archive-source-mode',{data:{mode:'local',state:state,geoid:geoid}});window.dash_clientside.set_props('archive-local-title',{value:''});
    }else if(trigger==='archive-sheet'||trigger==='archive-sheets'||trigger==='archive-selected'){
      local=false;window.dash_clientside.set_props('archive-local-title',{value:''}); const row=Array.isArray(sheets)&&Number.isInteger(sheet)?sheets[sheet]:null;
      const candidate=row&&row.image;
      if(typeof candidate==='string'){try{let u=new URL(candidate);if(u.protocol==='https:'&&['www.loc.gov','loc.gov','tile.loc.gov'].includes(u.hostname)&&!u.username&&!u.password)source=candidate;}catch(e){}}
      if(!source){image.removeAttribute('src');image.style.display='none';document.getElementById('archive-image-empty').style.display='block';window.dash_clientside.set_props('archive-source-mode',{data:null});status('Select a map sheet or open a local image.');return Date.now();}
      window.dash_clientside.set_props('archive-source-mode',{data:{mode:'archive',state:state,geoid:geoid}});
    }
    if(source){scale=1;angle=0;image.onload=()=>status(local?'Local image open. Drag or scroll to inspect; zoom to read details.':'Library of Congress map image open. Drag or scroll to inspect; check date and legend.');image.onerror=()=>status('The image could not be loaded. Try another sheet or open a local map image.');image.src=source;document.getElementById('archive-image-empty').style.display='none';box.scrollTop=0;box.scrollLeft=0;}
    if(trigger==='archive-zoom-in')scale=Math.min(8,scale*1.4);
    if(trigger==='archive-zoom-out')scale=Math.max(.5,scale/1.4);
    if(trigger==='archive-fit'){scale=1;angle=0;box.scrollTop=0;box.scrollLeft=0;}
    if(trigger==='archive-rotate')angle=(angle+90)%360;
    if(image.getAttribute('src'))paint(image,box);
    if(!box.dataset.panReady){box.dataset.panReady='yes';box.addEventListener('pointerdown',e=>{if(e.button!==0)return;down={x:e.clientX,y:e.clientY,left:box.scrollLeft,top:box.scrollTop};box.setPointerCapture(e.pointerId);box.style.cursor='grabbing';e.preventDefault();});box.addEventListener('pointermove',e=>{if(down){box.scrollLeft=down.left-(e.clientX-down.x);box.scrollTop=down.top-(e.clientY-down.y);}});const end=()=>{down=null;box.style.cursor='grab';};box.addEventListener('pointerup',end);box.addEventListener('pointercancel',end);}
    return Date.now();
  }};
})();
