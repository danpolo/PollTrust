const state={election:null,current:null,historical:null};
const fmt=v=>v==null?'אין מספיק נתונים':new Intl.NumberFormat('he-IL',{maximumFractionDigits:2}).format(v);
const fmtDate=v=>new Intl.DateTimeFormat('he-IL',{dateStyle:'medium'}).format(new Date(`${v}T12:00:00`));
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function daysUntil(v){const t=new Date(`${v}T00:00:00`),n=new Date(),d=new Date(n.getFullYear(),n.getMonth(),n.getDate());return Math.max(0,Math.ceil((t-d)/86400000))}
function expected(m,d){return m?.expected_error_by_days?.[String(Math.max(0,Math.min(120,d)))]??null}
function support(m){if(!m)return'אין היסטוריה';const i=m.independent_election_count??m.election_count??0,s=m.shared_prior_effective_elections??0;return s>0?`${i} עצמאיות + ${fmt(s)} משקל היסטורי משותף`:`${i} מערכות בחירות`}

const HELP={
expected_error:'ממוצע שגיאת המנדטים ההיסטורית באותו מרחק מיום הבחירות. בכל מערכת נבחר רק הסקר האחרון שהיה זמין עד נקודת הזמן, וסקר ישן ביותר מ־45 ימים אינו נכלל.',
overall_raw_error:'ממוצע מרחק העברת המנדטים של הסקר האחרון הזמין לפני כל מערכת בחירות. כל מערכת בחירות מקבלת משקל שווה.',
truth_bias:'הממוצע של הפער בין תחזית הסוקר לתוצאה בפועל עבור אוסף רשימות היסטורי שמוגדר בנפרד לכל מערכת בחירות. הסימן מציין את כיוון ההטיה.',
debiased_error:'שגיאת המנדטים לאחר תיקון הטיה שנלמד רק ממערכות הבחירות האחרות, ורק עבור מזהי מפלגות שניתנים להשוואה.',
lean_value_added:'כמה הסטייה של הסוקר ממרכז סקרים מאוזן בין אשכולות קירבה אותו לתוצאה האמיתית. ערך חיובי מציין שיפור ביחס למרכז.',
support:'מספר מערכות הבחירות שתומכות במדד. לשתי ישויות Direct Polls הנוכחיות מוצג בנפרד גם משקל היסטורי משותף מופחת; רווח 95% מחושב על היסטוריה ישירה.',
bloc_totals:'סכום המנדטים בכל אחד משלושת גושי התצוגה שהוגדרו במפורש בתצורת הבחירות. הסכומים מחושבים ישירות מווקטור 120 המנדטים ואינם משפיעים על ציוני האמינות.'
};

function infoButton(key,label){
  return '<button class="info-button" type="button" data-help="'+key+'" aria-label="הסבר על '+esc(label)+'" aria-controls="metricHelpPopover" aria-expanded="false"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg></button>';
}
function metricLabel(label,key){return '<span class="metric-label-text">'+esc(label)+'</span>'+infoButton(key,label)}
function outletLabel(meta){return (meta?.outlet_he||'').trim()||'ללא ערוץ קבוע'}
function blocDefinitions(){return state.election?.presentation_blocs||{}}
function partyBlocMap(){return state.election?.party_presentation_blocs||{}}
function blocCssClass(id){const c=blocDefinitions()[id]?.class_name;return /^[a-z0-9_-]+$/i.test(c||'')?c:'bloc-unconfigured'}

function pollBlocState(p){
  const defs=blocDefinitions(),map=partyBlocMap(),totals=Object.fromEntries(Object.keys(defs).map(id=>[id,0])),unknown=[];
  let sum=0;
  for(const[id,raw]of Object.entries(p?.parties||{})){
    const seats=Number(raw);
    if(!Number.isFinite(seats)){unknown.push(id);continue}
    sum+=seats;
    const bloc=map[id];
    if(!bloc||!defs[bloc]){unknown.push(id);continue}
    totals[bloc]+=seats;
  }
  const errors=[];
  if(unknown.length)errors.push('אין שיוך גוש עבור: '+unknown.join(', '));
  if(Math.abs(sum-120)>.001)errors.push('סכום המנדטים הוא '+fmt(sum)+' במקום 120');
  return{defs,map,totals,error:errors.join(' · ')};
}

function blocSummary(bs){
  if(bs.error)return '<div class="bloc-summary-error" role="alert"><strong>שגיאת תצורת גושים:</strong> '+bs.error+'</div>';
  const items=Object.entries(bs.defs).map(([id,d])=>
    '<div class="bloc-total '+blocCssClass(id)+'"><span>'+esc(d.label_he)+'</span><strong>'+fmt(bs.totals[id])+'</strong></div>'
  ).join('');
  return '<div class="bloc-summary" role="group" aria-label="סיכום גושים מתוך 120 מנדטים"><div class="bloc-summary-heading"><h4>מצב הגושים</h4>'+infoButton('bloc_totals','מצב הגושים')+'</div><div class="bloc-totals">'+items+'</div></div>';
}

function validateBlocConfig(){
  const defs=blocDefinitions(),map=partyBlocMap(),issues=[];
  if(Object.keys(defs).length!==3)issues.push('נדרשים בדיוק שלושה גושי תצוגה');
  for(const id of Object.keys(state.election.party_names||{})){
    if(!map[id])issues.push('חסר שיוך עבור '+id);
    else if(!defs[map[id]])issues.push('שיוך לא מוכר עבור '+id);
  }
  for(const p of state.current.polls||[])for(const id of Object.keys(p.parties||{}))if(!map[id]||!defs[map[id]])issues.push('הסקר כולל מפלגה ללא שיוך: '+id);
  return [...new Set(issues)];
}

function renderBlocConfigNotice(){
  const e=document.querySelector('#blocConfigNotice'),issues=validateBlocConfig();
  e.hidden=!issues.length;
  e.textContent=issues.length?'שגיאת תצורת גושים: '+issues.join(' · ')+' — לא יבוצע שיוך אוטומטי.':'';
}

function mandates(p,bs){
  const names=state.election.party_names||{};
  return Object.entries(p.parties||{}).filter(([,seats])=>Number(seats)>0)
    .sort((a,b)=>Number(b[1])-Number(a[1])||String(names[a[0]]||a[0]).localeCompare(String(names[b[0]]||b[0]),'he'))
    .map(([id,seats])=>{
      const bloc=bs.map[id],label=bs.defs[bloc]?.label_he||'ללא סיווג גוש';
      return '<span class="mandate-chip '+blocCssClass(bloc)+'" title="'+esc(names[id]||id)+': '+fmt(seats)+' מנדטים ('+label+')" aria-label="'+esc(names[id]||id)+', '+fmt(seats)+' מנדטים, '+label+'">'
        +'<span class="party-name">'+esc(names[id]||id)+'</span>'
        +'<strong class="party-seats">'+fmt(seats)+'</strong>'
        +'<span class="sr-only">'+label+'</span>'
        +'</span>';
    }).join('');
}

function renderHeader(){
  const days=daysUntil(state.election.election_date),checked=state.current.last_successful_check||state.current.last_successful_update;
  document.querySelector('#electionBadge').innerHTML=`<strong>${days}</strong><span>ימים עד הבחירות<br>${fmtDate(state.election.election_date)}</span>`;
  document.querySelector('#updateMeta').textContent=`בדיקת מקורות אחרונה: ${new Intl.DateTimeFormat('he-IL',{dateStyle:'medium',timeStyle:'short'}).format(new Date(checked))}`;
  if(state.historical.demo_mode){
    const e=document.querySelector('#demoNotice');
    e.hidden=false;
    e.textContent='גרסת הפיתוח משתמשת בנתוני כיול היסטוריים סינתטיים לצורך בדיקת המודל והממשק. אין להסיק מהם מסקנות אמיתיות על אמינות הסוקרים עד להחלפתם במאגר היסטורי מתועד.';
  }
  const age=(Date.now()-new Date(checked))/3600000;
  if(age>state.election.stale_after_hours){
    const e=document.querySelector('#staleNotice');
    e.hidden=false;
    e.textContent=`אזהרה: בדיקת מקורות הסקרים לא הצליחה כבר יותר מ־${state.election.stale_after_hours} שעות.`;
  }
}

function latest(){
  const m=new Map();
  for(const p of state.current.polls){
    const old=m.get(p.pollster);
    if(!old||p.date>old.date)m.set(p.pollster,p);
  }
  return m;
}

function blocBar(bs){
  if(bs.error)return '';
  return '<div class="bloc-bar" aria-label="חלוקת גושים מתוך 120 מנדטים">'
    +Object.entries(bs.defs).map(([id,d])=>
      '<span class="bloc-bar-segment '+blocCssClass(id)+'" style="width:'+((bs.totals[id]/120)*100).toFixed(3)+'%" title="'+esc(d.label_he)+': '+fmt(bs.totals[id])+'"></span>'
    ).join('')+'</div>';
}

function renderBlocOverview(){
  const map=latest(),rows=[];
  for(const[id,meta]of Object.entries(state.election.pollsters)){
    const p=map.get(id);
    if(!p)continue;
    const bs=pollBlocState(p);
    rows.push({id,meta,p,bs});
  }
  const all=rows.filter(x=>!x.bs.error),range=id=>{
    const vals=all.map(x=>x.bs.totals[id]);
    return vals.length?[Math.min(...vals),Math.max(...vals)]:null;
  };
  const change=range('change'),coalition=range('coalition');
  const legend=Object.entries(blocDefinitions()).map(([id,d])=>
    '<span class="overview-legend-item"><i class="bloc-dot '+blocCssClass(id)+'"></i>'+esc(d.label_he)+'</span>'
  ).join('');
  const stats='<div class="overview-stats">'
    +'<div class="stat-box"><span class="stat-label">סוקרים עם סקר נוכחי</span><strong class="stat-value">'+all.length+'</strong></div>'
    +(change?'<div class="stat-box"><span class="stat-label">טווח גוש השינוי</span><strong class="stat-value" dir="ltr"><span class="stat-range">'+change[0]+'–'+change[1]+'</span></strong></div>':'')
    +(coalition?'<div class="stat-box"><span class="stat-label">טווח גוש הקואליציה</span><strong class="stat-value" dir="ltr"><span class="stat-range">'+coalition[0]+'–'+coalition[1]+'</span></strong></div>':'')
    +'</div>';
  const list=rows.map(({meta,p,bs})=>
    '<div class="overview-row"><div class="overview-row-head"><div><strong class="overview-outlet">'+esc(outletLabel(meta))+'</strong><span class="overview-pollster">'+esc(meta.name_he)+'</span></div><time class="overview-date" datetime="' + esc(p.date) + '">' + fmtDate(p.date) + '</time></div>'
    +(bs.error?'<div class="bloc-summary-error">'+esc(bs.error)+'</div>':blocBar(bs)+'<div class="overview-values">'+Object.entries(bs.defs).map(([id,d])=>'<span class="overview-pill '+blocCssClass(id)+'"><b>'+fmt(bs.totals[id])+'</b> '+esc(d.label_he)+'</span>').join('')+'</div>')
    +'</div>'
  ).join('');
  document.querySelector('#liveOverview').innerHTML='<div class="overview-head"><div><p class="eyebrow">השוואת גושים</p><h3>אותם 120 מנדטים, זה לצד זה</h3><p>כך אפשר לראות מיד היכן הסוקרים מסכימים והיכן הפערים גדולים, בלי להסתיר את פירוט המפלגות.</p></div><div class="overview-legend">'+legend+'</div></div>'+stats+'<div class="overview-list">'+list+'</div>';
}

function renderCards(){
  const map=latest(),days=daysUntil(state.election.election_date);
  document.querySelector('#pollCards').innerHTML=Object.entries(state.election.pollsters).map(([id,meta])=>{
    const p=map.get(id),m=state.historical.pollsters[id];
    if(!p)return '<article class="poll-card empty-card"><div class="card-top"><div><p class="card-kicker">'+esc(outletLabel(meta))+'</p><h3>'+esc(meta.name_he)+'</h3></div></div><p class="context-note">לא נמצא כרגע סקר נוכחי מאומת במאגר עבור סוקר זה.</p>'+(meta.lineage_note_he?'<p class="lineage">'+esc(meta.lineage_note_he)+'</p>':'')+'</article>';
    const bs=pollBlocState(p),err=expected(m,days);
    return '<article class="poll-card">'
      +'<div class="card-top"><div><p class="card-kicker">'+esc(outletLabel(meta))+'</p><h3>'+esc(meta.name_he)+'</h3></div><time class="date-pill" datetime="'+esc(p.date)+'">'+fmtDate(p.date)+'</time></div>'
      +(bs.error?'<div class="bloc-summary-error" role="alert">'+esc(bs.error)+'</div>':'<div class="card-bloc-wrap">'+blocBar(bs)+'<div class="bloc-totals compact">'+Object.entries(bs.defs).map(([bid,d])=>'<div class="bloc-total '+blocCssClass(bid)+'"><span>'+esc(d.label_he)+'</span><strong>'+fmt(bs.totals[bid])+'</strong></div>').join('')+'</div></div>')
      +'<div class="metric-grid">'
        +'<div class="metric metric-primary"><span class="metric-label">'+metricLabel('שגיאה היסטורית צפויה כיום','expected_error')+'</span><strong class="metric-value">'+(m?.data_status==='demo'?'הדגמה בלבד':fmt(err))+'</strong><small class="metric-sub">מנדטים בממוצע</small></div>'
        +'<div class="metric"><span class="metric-label">'+metricLabel('שגיאת סקר אחרון היסטורית','overall_raw_error')+'</span><strong class="metric-value">'+(m?.data_status==='demo'?'הדגמה בלבד':fmt(m?.overall_raw_error))+'</strong><small class="metric-sub">ממוצע סקר אחרון</small></div>'
        +'<div class="metric"><span class="metric-label">'+metricLabel('תמיכת נתונים','support')+'</span><strong class="metric-value metric-value-sm">'+esc(support(m))+'</strong><small class="metric-sub">מערכות בחירות</small></div>'
      +'</div>'
      +'<section class="party-results" aria-label="מנדטים לפי מפלגה"><div class="party-results-heading"><h4>מנדטים לפי מפלגה</h4><span>מתוך 120</span></div><div class="mandate-list">'+mandates(p,bs)+'</div></section>'
      +(meta.lineage_note_he?'<p class="lineage">'+esc(meta.lineage_note_he)+'</p>':'')
      +'<div class="card-footer"><span>'+(p.sample_size?'מדגם: '+fmt(p.sample_size):'גודל מדגם לא זמין')+'</span><a href="'+esc(p.source)+'" target="_blank" rel="noopener noreferrer">מקור הסקר ↗</a></div>'
      +'</article>';
  }).join('');
}

function renderHistoryOverview(days){
  const rows=Object.entries(state.election.pollsters).map(([id,meta])=>({id,meta,m:state.historical.pollsters[id]||{}}));
  const vals=rows.map(x=>expected(x.m,days)).filter(v=>Number.isFinite(v));
  const max=vals.length?Math.max(...vals):1;
  document.querySelector('#historyOverview').innerHTML='<div class="history-overview-head"><div><p class="eyebrow">המדד המרכזי</p><h3>שגיאה צפויה '+(days===0?'ביום הבחירות':days+' ימים לפני הבחירות')+'</h3></div><p>הפס מציג את ממוצע מרחק המנדטים ההיסטורי בנקודת הזמן שנבחרה. קצר יותר = שגיאה היסטורית נמוכה יותר; אין להסיק מהבדלים קטנים יותר ממה שהנתונים תומכים בו.</p></div><div class="history-bars">'+rows.map(({meta,m})=>{
    const v=expected(m,days),pct=Number.isFinite(v)?Math.max(4,(v/max)*100):0;
    return '<div class="history-bar-row"><div class="history-bar-label"><strong>'+esc(meta.name_he)+'</strong><span>'+esc(outletLabel(meta))+'</span></div><div class="history-bar-track">'+(Number.isFinite(v)?'<span class="history-bar-fill" style="width:'+pct.toFixed(1)+'%"></span>':'<span class="history-bar-empty">אין נתון</span>')+'</div><div class="history-bar-value">'+(Number.isFinite(v)?fmt(v):'—')+'</div></div>';
  }).join('')+'</div>';
}

function renderHistory(days){
  document.querySelector('#daysValue').textContent=days===0?'יום הבחירות':days+' ימים';
  renderHistoryOverview(days);
  document.querySelector('#historyRows').innerHTML=Object.entries(state.election.pollsters).map(([id,meta])=>{
    const m=state.historical.pollsters[id]||{},demo=m.data_status==='demo';
    const ci=m.uncertainty_95?'<span dir="ltr">'+fmt(m.uncertainty_95[0])+'–'+fmt(m.uncertainty_95[1])+'</span>':'אין';
    return '<tr><td class="pollster-cell"><strong>'+esc(meta.name_he)+'</strong><span class="pollster-outlet">'+esc(outletLabel(meta))+'</span></td><td><strong class="table-primary-value">'+(demo?'הדגמה בלבד':fmt(expected(m,days)))+'</strong></td><td>'+(demo?'הדגמה בלבד':fmt(m.overall_raw_error))+'</td><td>'+(demo?'הדגמה בלבד':fmt(m.truth_bias))+'</td><td>'+(demo?'הדגמה בלבד':fmt(m.debiased_error))+'</td><td>'+(demo?'הדגמה בלבד':fmt(m.lean_value_added))+'</td><td><div class="support-count">'+esc(support(m))+'</div><div class="support-ci">רווח 95%: '+ci+'</div></td></tr>';
  }).join('');
}

let activeHelpButton=null;
function closeHelp(){
  const p=document.querySelector('#metricHelpPopover');
  if(!p||p.hidden)return;
  p.hidden=true;
  p.removeAttribute('style');
  if(activeHelpButton)activeHelpButton.setAttribute('aria-expanded','false');
  activeHelpButton=null;
}

function openHelp(b){
  const p=document.querySelector('#metricHelpPopover'),help=HELP[b.dataset.help];
  if(!p||!help)return;
  if(activeHelpButton===b&&!p.hidden){closeHelp();return}
  closeHelp();
  activeHelpButton=b;
  b.setAttribute('aria-expanded','true');
  p.textContent=help;
  p.hidden=false;
  const r=b.getBoundingClientRect(),w=Math.min(320,window.innerWidth-24);
  p.style.width=w+'px';
  let left=Math.max(12,Math.min(r.right-w,window.innerWidth-w-12)),top=r.bottom+8;
  if(top+p.offsetHeight>window.innerHeight-12)top=Math.max(12,r.top-p.offsetHeight-8);
  p.style.left=left+'px';
  p.style.top=top+'px';
}

function wireHelp(){
  document.addEventListener('click',e=>{
    const b=e.target.closest('.info-button');
    if(b){e.preventDefault();openHelp(b);return}
    if(!e.target.closest('#metricHelpPopover'))closeHelp();
  });
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeHelp()});
  window.addEventListener('resize',closeHelp);
  window.addEventListener('scroll',closeHelp,true);
}

function activateTab(b){
  closeHelp();
  document.querySelectorAll('.tab').forEach(x=>{
    const on=x===b;
    x.classList.toggle('is-active',on);
    x.setAttribute('aria-selected',String(on));
    x.tabIndex=on?0:-1;
  });
  document.querySelectorAll('.panel').forEach(x=>{
    const on=x.id===b.dataset.tab;
    x.classList.toggle('is-active',on);
    x.hidden=!on;
  });
}

function updateSliderTrack(slider){
  if(!slider)return;
  const min=Number(slider.min||0),max=Number(slider.max||120),val=Number(slider.value);
  const pct=((val-min)/(max-min))*100;
  slider.style.setProperty('--slider-fill', pct+'%');
}

function wire(){
  const tabs=[...document.querySelectorAll('.tab')];
  tabs.forEach((b,i)=>{
    b.addEventListener('click',()=>activateTab(b));
    b.addEventListener('keydown',e=>{
      if(!['ArrowLeft','ArrowRight'].includes(e.key))return;
      e.preventDefault();
      const step=e.key==='ArrowLeft'?1:-1;
      const next=tabs[(i+step+tabs.length)%tabs.length];
      activateTab(next);
      next.focus();
    });
  });
  document.querySelectorAll('.panel').forEach(x=>x.hidden=!x.classList.contains('is-active'));
  const slider=document.querySelector('#daysSlider');
  if(slider){
    updateSliderTrack(slider);
    slider.addEventListener('input',()=>{
      closeHelp();
      updateSliderTrack(slider);
      renderHistory(Number(slider.value));
    });
  }
  wireHelp();
}

async function init(){
  try{
    const[election,current,historical]=await Promise.all(['data/election.json','data/current-polls.json','data/historical-model.json'].map(u=>fetch(u).then(r=>{if(!r.ok)throw Error(u);return r.json()})));
    Object.assign(state,{election,current,historical});
    renderHeader();
    renderBlocConfigNotice();
    renderBlocOverview();
    renderCards();
    renderHistory(30);
    wire();
  }catch(e){
    document.querySelector('main').innerHTML='<div class="notice notice-danger">לא ניתן לטעון את קובצי הנתונים. בדקו את תהליך הפריסה.</div>';
    console.error(e);
  }
}
init();

