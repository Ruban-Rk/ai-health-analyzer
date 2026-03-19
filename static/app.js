let currentUser = null;
let cart = [];
let selectedDoctor = null;
let chartsLoaded = false;

async function init() {
  try {
    const res = await fetch('/api/current-user');
    if (!res.ok) { window.location.href='/login'; return; }
    currentUser = await res.json();
    renderUserUI();
    initTheme();
    loadNotifications();
    setInterval(loadNotifications, 30000);
    loadHomeData();
  } catch { window.location.href='/login'; }
}

function renderUserUI() {
  const roleColors = {user:'linear-gradient(135deg,#4f8ef7,#a855f7)',doctor:'linear-gradient(135deg,#10b981,#059669)',admin:'linear-gradient(135deg,#f59e0b,#ef4444)'};
  document.getElementById('topAvatar').textContent = currentUser.avatar;
  document.getElementById('topAvatar').style.background = roleColors[currentUser.role];
  document.getElementById('sidebarUser').innerHTML = `
    <div style="font-size:13px;font-weight:600;margin-bottom:2px">${currentUser.name}</div>
    <div style="font-size:11px;color:#8892b0;text-transform:capitalize">${currentUser.role}</div>
  `;
}

async function loadHomeData() {

  const wb = document.getElementById('welcomeBanner');
  const hour = new Date().getHours();
  const greet = hour<12?'Good morning':hour<18?'Good afternoon':'Good evening';
  wb.innerHTML = `
    <div style="font-size:13px;color:#8892b0;margin-bottom:6px">${greet}</div>
    <div style="font-size:26px;font-weight:800;margin-bottom:6px;background:linear-gradient(135deg,#fff,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent">${currentUser.name}</div>
    <div style="font-size:14px;color:#8892b0">Welcome to HealthAI Pro · Your personal health dashboard</div>
  `;
  document.getElementById('quickStats').innerHTML = `
    <div class="qs-card"><div class="qs-num" style="color:#4f8ef7">94.2%</div><div class="qs-label">Model Accuracy</div></div>
    <div class="qs-card"><div class="qs-num" style="color:#10b981">6</div><div class="qs-label">Specialists Available</div></div>
    <div class="qs-card"><div class="qs-num" style="color:#a855f7">12</div><div class="qs-label">Medicines in Store</div></div>
    <div class="qs-card"><div class="qs-num" style="color:#f59e0b">24/7</div><div class="qs-label">AI Support</div></div>
  `;
  const tips = [
    {color:'#4f8ef7',text:'Drink at least 8 glasses of water daily to stay hydrated and support organ function.'},
    {color:'#10b981',text:'Aim for 7-8 hours of quality sleep every night to boost immunity and recovery.'},
    {color:'#a855f7',text:'Walk at least 30 minutes a day to maintain cardiovascular health.'},
    {color:'#f59e0b',text:'Eat a balanced diet rich in fruits, vegetables and whole grains.'},
  ];
  document.getElementById('tipsList').innerHTML = tips.map(t=>`
    <div class="tip-item"><div class="tip-dot" style="background:${t.color}"></div>${t.text}</div>
  `).join('');
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    new Chart(document.getElementById('miniChart'),{
      type:'line',data:{labels:Object.keys(data.monthly_cases),datasets:[{data:Object.values(data.monthly_cases),borderColor:'#4f8ef7',backgroundColor:'rgba(79,142,247,0.08)',tension:0.4,fill:true,pointRadius:0}]},
      options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#8892b0',font:{size:10}},grid:{color:'#2a3a5c'}},y:{ticks:{color:'#8892b0',font:{size:10}},grid:{color:'#2a3a5c'}}}}
    });
  } catch(e){}
}

function switchTab(tab, el) {
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  document.getElementById('tab-'+tab).classList.add('active');
  const titles = {home:'Home',chat:'AI Chatbot',checker:'Symptom Checker',appointments:'Appointments',store:'Medicine Store',dashboard:'Dashboard',records:'Health Records',vision:'Skin Analysis'};
  document.getElementById('topbarTitle').textContent = titles[tab]||tab;
  if(el) el.classList.add('active');
  if(tab==='dashboard') loadDashboard();
  if(tab==='appointments') loadDoctors();
  if(tab==='store') loadStore();
  if(tab==='records') loadRecords();
  if(window.innerWidth<=900) document.getElementById('sidebar').classList.remove('open');
  if(tab==='bmi') { document.getElementById('bmiResult').style.display='none'; }
  if(tab==='news') loadHealthNews();
  if(tab==='donors') findDonors();
  if(tab==='profile') loadProfile();
}

function toggleSidebar(){document.getElementById('sidebar').classList.toggle('open');}

async function doLogout(){
  await fetch('/api/logout');
  window.location.href='/login';
}

function showToast(msg,type='info'){
  const tc=document.getElementById('toastContainer');
  const t=document.createElement('div');
  t.className=`toast ${type}`;
  const icons={success:'✓',error:'✗',info:'ℹ'};
  t.innerHTML=`<span>${icons[type]}</span><span>${msg}</span>`;
  tc.appendChild(t);
  setTimeout(()=>t.remove(),3500);
}

// CHAT
function handleChatKey(e){if(e.key==='Enter')sendMessage();}
function quickPrompt(t){document.getElementById('chatInput').value=t;sendMessage();}

function addMessage(text,isUser){
  const c=document.getElementById('chatMessages');
  const d=document.createElement('div');
  d.className='message '+(isUser?'user-message':'bot-message');
  d.innerHTML=`<div class="message-avatar">${isUser?currentUser.avatar:'AI'}</div><div class="message-bubble">${text}</div>`;
  c.appendChild(d);
  c.scrollTop=c.scrollHeight;
}

async function sendMessage(){
  const input=document.getElementById('chatInput');
  const msg=input.value.trim();
  if(!msg)return;
  addMessage(msg,true);
  input.value='';
  const ti=document.getElementById('typingIndicator');
  ti.style.display='block';
  try{
    const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
    const data=await res.json();
    setTimeout(()=>{ti.style.display='none';addMessage(data.response,false);},900);
  }catch{ti.style.display='none';addMessage('Connection error. Please try again.',false);}
}

// SYMPTOM CHECKER
async function analyzeSymptoms(){
  const keys=['fever','cough','headache','fatigue','sore_throat','body_ache','nausea','runny_nose'];
  const symptoms={};
  keys.forEach(s=>{symptoms[s]=document.getElementById(s).checked?1:0;});
  if(!Object.values(symptoms).some(v=>v===1)){showToast('Please select at least one symptom','error');return;}
  const btn=document.querySelector('.pulse-btn');
  btn.textContent='Analyzing...';btn.disabled=true;
  try{
    const res=await fetch('/api/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symptoms})});
    const data=await res.json();
    showResult(data);
    showToast('Analysis complete!','success');
  }catch{showToast('Error connecting to server','error');}
  btn.textContent='Analyze with AI';btn.disabled=false;
}

function showResult(data){
  const c=document.getElementById('result-container');
  c.classList.remove('hidden');
  c.style.borderLeftColor=data.color||'#4f8ef7';
  let bars='';
  for(const[d,p] of Object.entries(data.probabilities)){
    bars+=`<div class="prob-bar-row"><div class="prob-bar-label"><span>${d}</span><span>${p}%</span></div><div class="prob-bar-bg"><div class="prob-bar-fill" style="width:${p}%"></div></div></div>`;
  }
  c.innerHTML=`
    <div class="result-disease" style="color:${data.color}">${data.disease}</div>
    <div class="result-confidence">AI Confidence: ${data.confidence}%</div>
    <span class="severity-badge severity-${data.severity}">${data.severity} Severity</span>
    <p style="font-size:14px;color:#ccd6f6;margin-bottom:10px;line-height:1.6">${data.description}</p>
    <p style="font-size:13px;color:#8892b0;margin-bottom:16px"><strong style="color:#4f8ef7">Recommendation:</strong> ${data.advice}</p>
    <div class="prob-bars">${bars}</div>
    <p style="font-size:12px;color:#8892b0;margin-top:16px;font-style:italic">⚠ AI prediction only. Consult a qualified doctor for diagnosis.</p>
  `;
  c.scrollIntoView({behavior:'smooth'});
}

// APPOINTMENTS
async function loadDoctors(){
  const res=await fetch('/api/doctors');
  const data=await res.json();
  document.getElementById('doctorsGrid').innerHTML=data.doctors.map(d=>`
    <div class="doctor-card">
      <div class="doc-header">
        <div class="doc-avatar">${d.name.split(' ')[1][0]}</div>
        <div><div class="doc-name">${d.name}</div><div class="doc-spec">${d.spec}</div></div>
      </div>
      <div class="doc-meta">
        <span>📅 ${d.exp} experience</span>
        <span class="doc-rating">★ ${d.rating}</span>
      </div>
      <button class="book-doc-btn" onclick="openBooking(${JSON.stringify(d).replace(/"/g,'&quot;')})">Book Appointment</button>
    </div>
  `).join('');
  loadMyAppointments();
}

function openBooking(doc){
  selectedDoctor=doc;
  document.getElementById('bookingTitle').textContent='Book with '+doc.name+' · '+doc.spec;
  const sel=document.getElementById('apptTime');
  sel.innerHTML=doc.slots.map(s=>`<option>${s}</option>`).join('');
  const today=new Date().toISOString().split('T')[0];
  document.getElementById('apptDate').min=today;
  document.getElementById('apptDate').value=today;
  document.getElementById('bookingForm').classList.remove('hidden');
  document.getElementById('bookingMsg').classList.add('hidden');
  document.getElementById('bookingForm').scrollIntoView({behavior:'smooth'});
}

async function confirmBooking(){
  const date=document.getElementById('apptDate').value;
  const time=document.getElementById('apptTime').value;
  const reason=document.getElementById('apptReason').value;
  if(!date||!reason){showToast('Please fill in all fields','error');return;}
  try{
    const res=await fetch('/api/appointment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({doctor:selectedDoctor.name,date,time,reason})});
    const data=await res.json();
    showToast('Appointment booked successfully!','success');
    document.getElementById('bookingForm').classList.add('hidden');
    loadMyAppointments();
  }catch{showToast('Booking failed. Try again.','error');}
}

async function loadMyAppointments(){
  const res=await fetch('/api/my-appointments');
  const data=await res.json();
  const container=document.getElementById('myAppointments');
  if(!data.appointments.length){container.innerHTML='';return;}
  container.innerHTML=`<h3 style="margin-bottom:14px;font-size:16px">My Appointments</h3>`+data.appointments.map(a=>`
    <div class="appt-item">
      <div><div style="font-size:14px;font-weight:600">${a.doctor}</div><div style="font-size:12px;color:#8892b0">${a.date} · ${a.time} · ${a.reason}</div></div>
      <span class="appt-status">${a.status}</span>
    </div>
  `).join('');
}

// STORE
async function loadStore(category='all',search=''){
  const url=`/api/medicines?category=${encodeURIComponent(category)}&search=${encodeURIComponent(search)}`;
  const res=await fetch(url);
  const data=await res.json();
  document.getElementById('medicinesGrid').innerHTML=data.medicines.map(m=>`
    <div class="med-card">
      <div class="med-emoji">${m.img}</div>
      <div class="med-name">${m.name}</div>
      <div class="med-desc">${m.desc}</div>
      <span class="med-category">${m.category}</span>
      <div class="med-footer">
        <div class="med-price">₹${m.price}</div>
        <button class="add-cart-btn" onclick="addToCart(${m.id},'${m.name.replace(/'/g,"\\'")}',${m.price})">+ Cart</button>
      </div>
    </div>
  `).join('');
}

function filterStore(){
  const cat=document.getElementById('categoryFilter').value;
  const s=document.getElementById('storeSearch').value;
  loadStore(cat,s);
}

function addToCart(id,name,price){
  const existing=cart.find(c=>c.id===id);
  if(existing) existing.qty++;
  else cart.push({id,name,price,qty:1});
  updateCartBar();
  showToast(name+' added to cart','success');
}

function updateCartBar(){
  const bar=document.getElementById('cartBar');
  if(!cart.length){bar.style.display='none';return;}
  const total=cart.reduce((s,c)=>s+c.price*c.qty,0);
  const count=cart.reduce((s,c)=>s+c.qty,0);
  document.getElementById('cartCount').textContent=count;
  document.getElementById('cartTotal').textContent=total;
  bar.style.display='flex';
}

async function checkout(){
  const total=cart.reduce((s,c)=>s+c.price*c.qty,0);
  try{
    const res=await fetch('/api/order',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items:cart,total})});
    const data=await res.json();
    cart=[];
    updateCartBar();
    showToast('Order placed! ID: #'+data.order_id,'success');
  }catch{showToast('Order failed. Try again.','error');}
}

// DASHBOARD
async function loadDashboard(){
  if(chartsLoaded)return;
  chartsLoaded=true;
  document.getElementById('dashStats').innerHTML=`
    <div class="stat-card"><div class="stat-number" style="color:#4f8ef7">1,247</div><div class="stat-label">Total Analyses</div></div>
    <div class="stat-card"><div class="stat-number" style="color:#10b981">94.2%</div><div class="stat-label">Accuracy</div></div>
    <div class="stat-card"><div class="stat-number" style="color:#a855f7">3</div><div class="stat-label">Conditions</div></div>
    <div class="stat-card"><div class="stat-number" style="color:#f59e0b">8</div><div class="stat-label">Symptoms Tracked</div></div>
  `;
  try{
    const res=await fetch('/api/stats');
    const d=await res.json();
    const cfg={plugins:{legend:{labels:{color:'#8892b0',font:{size:12}}}},scales:{x:{ticks:{color:'#8892b0'},grid:{color:'#2a3a5c'}},y:{ticks:{color:'#8892b0'},grid:{color:'#2a3a5c'}}}};
    new Chart(document.getElementById('symptomChart'),{type:'bar',data:{labels:Object.keys(d.symptom_frequency),datasets:[{data:Object.values(d.symptom_frequency),backgroundColor:['#4f8ef7','#a855f7','#10b981','#f59e0b','#ef4444','#06b6d4','#ec4899','#84cc16'],borderRadius:6}]},options:{...cfg,plugins:{legend:{display:false}}}});
    new Chart(document.getElementById('diseaseChart'),{type:'doughnut',data:{labels:Object.keys(d.disease_distribution),datasets:[{data:Object.values(d.disease_distribution),backgroundColor:['#ef4444','#3498db','#9b59b6'],borderWidth:0,hoverOffset:8}]},options:{plugins:{legend:{labels:{color:'#8892b0'}}}}});
    new Chart(document.getElementById('ageChart'),{type:'bar',data:{labels:Object.keys(d.age_groups),datasets:[{label:'Patients %',data:Object.values(d.age_groups),backgroundColor:'rgba(168,85,247,0.7)',borderRadius:6}]},options:{...cfg}});
    new Chart(document.getElementById('recoveryChart'),{type:'radar',data:{labels:Object.keys(d.recovery_rate),datasets:[{data:Object.values(d.recovery_rate),backgroundColor:'rgba(16,185,129,0.15)',borderColor:'#10b981',pointBackgroundColor:'#10b981'}]},options:{plugins:{legend:{display:false}},scales:{r:{ticks:{color:'#8892b0',backdropColor:'transparent'},grid:{color:'#2a3a5c'},pointLabels:{color:'#8892b0'}}}}});
    new Chart(document.getElementById('trendChart'),{type:'line',data:{labels:Object.keys(d.monthly_cases),datasets:[{label:'Cases',data:Object.values(d.monthly_cases),borderColor:'#4f8ef7',backgroundColor:'rgba(79,142,247,0.08)',tension:0.4,fill:true,pointBackgroundColor:'#4f8ef7',pointRadius:4}]},options:{...cfg}});
  }catch(e){console.error(e);}
}

// RECORDS
async function loadRecords(){
  try{
    const res=await fetch('/api/my-records');
    const data=await res.json();
    const container=document.getElementById('recordsList');
    if(!data.records.length){
      container.innerHTML='<div style="color:#8892b0;font-size:14px;text-align:center;padding:40px">No health records yet. Use the Symptom Checker to create one.</div>';
      return;
    }
    const colors={'Flu':'#e74c3c','Cold':'#3498db','Migraine':'#9b59b6'};
    container.innerHTML=data.records.map(r=>`
      <div class="record-item">
        <div><div class="record-diag" style="color:${colors[r.diagnosis]||'#4f8ef7'}">${r.diagnosis}</div><div class="record-date">${r.date}</div></div>
        <div class="record-conf">${r.confidence}% confidence</div>
      </div>
    `).join('');
  }catch{document.getElementById('recordsList').innerHTML='<div style="color:#8892b0;font-size:14px">Could not load records.</div>';}
}

// VISION
function analyzeImage(event){
  const file=event.target.files[0];
  if(!file)return;
  const prev=document.getElementById('imagePreview');
  const res=document.getElementById('visionResult');
  const reader=new FileReader();
  reader.onload=function(e){
    prev.innerHTML=`<img src="${e.target.result}" alt="Skin image">`;
    prev.classList.remove('hidden');
    res.classList.remove('hidden');
    res.innerHTML='<div style="color:#4f8ef7;font-size:14px">🔍 Analyzing image with computer vision...</div>';
    setTimeout(()=>{
      const conditions=[
        {name:'Eczema (Atopic Dermatitis)',confidence:73,severity:'Mild',color:'#f59e0b',advice:'Keep skin moisturized. Avoid known irritants. Use gentle, fragrance-free products.'},
        {name:'Contact Dermatitis',confidence:81,severity:'Mild',color:'#4f8ef7',advice:'Identify and avoid the allergen. Apply cool compresses. See a doctor if spreading.'},
        {name:'Psoriasis',confidence:67,severity:'Moderate',color:'#a855f7',advice:'Use prescribed topical treatments. Keep skin hydrated. Consult a dermatologist.'},
      ];
      const picked=conditions[Math.floor(Math.random()*conditions.length)];
      res.innerHTML=`
        <h3 style="color:${picked.color};font-size:18px;margin-bottom:8px">${picked.name}</h3>
        <div style="font-size:13px;color:#8892b0;margin-bottom:10px">Confidence: ${picked.confidence}%</div>
        <span class="severity-badge severity-${picked.severity}">${picked.severity}</span>
        <p style="font-size:14px;margin-top:14px;color:#ccd6f6;line-height:1.6">${picked.advice}</p>
        <p style="font-size:12px;color:#8892b0;margin-top:14px;font-style:italic">⚠ Simulated CV for demonstration. Not a medical diagnosis.</p>
      `;
      showToast('Image analysis complete!','success');
    },2200);
  };
  reader.readAsDataURL(file);
}
// THEME TOGGLE
function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  const btn = document.getElementById('themeBtn');
  if(btn) btn.textContent = next === 'light' ? '🌙' : '☀️';
}

function initTheme() {
  const saved = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  const btn = document.getElementById('themeBtn');
  if(btn) btn.textContent = saved === 'light' ? '🌙' : '☀️';
}

// NOTIFICATIONS
async function loadNotifications() {
  try {
    const res = await fetch('/api/notifications');
    const data = await res.json();
    const dot = document.querySelector('.notif-dot');
    if(data.unread > 0 && dot) dot.style.display = 'block';
    else if(dot) dot.style.display = 'none';
    const panel = document.getElementById('notifPanel');
    if(!panel) return;
    panel.innerHTML = `
      <div class="notif-header">
        <span>Notifications</span>
        <span style="font-size:12px;color:var(--muted)">${data.unread} new</span>
      </div>
      ${data.notifications.length ? data.notifications.map(n=>`
        <div class="notif-item">
          <div class="notif-dot-item" style="background:${n.type==='success'?'#10b981':n.type==='error'?'#ef4444':'#4f8ef7'}"></div>
          <div>
            <div style="font-size:13px;font-weight:600;margin-bottom:2px">${n.title}</div>
            <div style="font-size:12px;color:var(--muted);line-height:1.4">${n.msg}</div>
            <div style="font-size:11px;color:var(--muted);margin-top:3px">${n.time}</div>
          </div>
        </div>`).join('') : '<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">No new notifications</div>'}
    `;
  } catch(e) {}
}

function toggleNotifPanel() {
  const panel = document.getElementById('notifPanel');
  if(panel) panel.classList.toggle('hidden');
  loadNotifications();
}

// BMI CALCULATOR
async function calculateBMI() {
  const weight = document.getElementById('bmiWeight')?.value;
  const height = document.getElementById('bmiHeight')?.value;
  if(!weight || !height) { showToast('Enter both weight and height','error'); return; }
  if(weight <= 0 || height <= 0) { showToast('Please enter valid values','error'); return; }
  try {
    const res = await fetch('/api/bmi', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({weight:parseFloat(weight), height:parseFloat(height)})
    });
    const data = await res.json();
    const result = document.getElementById('bmiResult');
    if(!result) return;
    result.style.display = 'block';
    result.style.background = data.color + '15';
    result.style.border = `1px solid ${data.color}40`;
    result.innerHTML = `
      <div class="bmi-number" style="color:${data.color}">${data.bmi}</div>
      <div class="bmi-label" style="color:${data.color}">${data.category}</div>
      <div style="font-size:13px;color:var(--muted);margin-top:8px">${data.advice}</div>
      <div style="margin-top:16px;height:8px;background:var(--bg3);border-radius:4px;overflow:hidden">
        <div style="height:100%;width:${Math.min(data.bmi/40*100,100)}%;background:${data.color};border-radius:4px;transition:width 1s ease"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-top:4px">
        <span>Underweight</span><span>Normal</span><span>Overweight</span><span>Obese</span>
      </div>
    `;
    showToast('BMI calculated!','success');
  } catch(e) {
    showToast('Error calculating BMI. Try again.','error');
    console.error(e);
  }
}

// HEALTH NEWS
async function loadHealthNews() {
  const container = document.getElementById('newsFeed');
  if(!container) return;

  container.innerHTML = `<div style="color:var(--muted);font-size:14px;padding:20px 0">Loading latest health news...</div>`;

  try {
    const res = await fetch('/api/health-news');
    const data = await res.json();

    const categories = ['All', ...new Set(data.news.map(n => n.category))];
    let activeCategory = 'All';

    function renderNews(filter) {
      const filtered = filter === 'All' ? data.news : data.news.filter(n => n.category === filter);
      return filtered.map(n => `
        <div class="news-card" onclick="window.open('${n.url}','_blank')" style="cursor:pointer">
          <div class="news-color-bar" style="background:${n.color}"></div>
          <div class="news-body">
            <div class="news-meta">
              <span class="news-category-badge" style="background:${n.color}18;color:${n.color};border:1px solid ${n.color}30">${n.category}</span>
              <span class="news-source">📰 ${n.source}</span>
              <span class="news-time">🕐 ${n.time}</span>
              <span class="news-read-time">📖 ${n.read_time}</span>
            </div>
            <div class="news-title">${n.title}</div>
            <div class="news-summary">${n.summary}</div>
            <div class="news-footer">
              <span class="news-link" style="color:${n.color}">Read full article → ${n.source}</span>
            </div>
          </div>
        </div>
      `).join('');
    }

    container.innerHTML = `
      <div class="news-filter-bar">
        ${categories.map(c => `
          <button class="news-filter-btn ${c==='All'?'active':''}"
            style="${c==='All'?'background:linear-gradient(135deg,#4f8ef7,#a855f7);color:#fff;border-color:transparent':''}"
            onclick="filterNews('${c}', this)">
            ${c}
          </button>`).join('')}
      </div>
      <div id="newsGrid">${renderNews('All')}</div>
    `;

    window.filterNews = function(category, btn) {
      document.querySelectorAll('.news-filter-btn').forEach(b => {
        b.style.background = 'var(--glass)';
        b.style.color = 'var(--muted)';
        b.style.borderColor = 'var(--glass-border)';
        b.classList.remove('active');
      });
      btn.style.background = 'linear-gradient(135deg,#4f8ef7,#a855f7)';
      btn.style.color = '#fff';
      btn.style.borderColor = 'transparent';
      btn.classList.add('active');
      document.getElementById('newsGrid').innerHTML = renderNews(category);
    };

  } catch(e) {
    container.innerHTML = `<div style="color:var(--muted);font-size:14px;padding:20px">Could not load news. Please try again.</div>`;
  }
}

// BLOOD DONOR FINDER
async function findDonors() {
  const bg = document.getElementById('donorBloodGroup')?.value || '';
  const res = await fetch(`/api/blood-donors?blood_group=${bg}`);
  const data = await res.json();
  const container = document.getElementById('donorsList');
  if(!container) return;
  container.innerHTML = data.donors.length ? data.donors.map(d=>`
    <div style="display:flex;align-items:center;gap:14px;padding:14px 18px;background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:10px;transition:all 0.2s" onmouseover="this.style.borderColor='rgba(239,68,68,0.3)'" onmouseout="this.style.borderColor='var(--border)'">
      <div style="width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,#ef4444,#dc2626);display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:700;color:#fff;flex-shrink:0">${d.avatar}</div>
      <div style="flex:1">
        <div style="font-size:14px;font-weight:600">${d.name}</div>
        <div style="font-size:12px;color:var(--muted)">${d.phone}</div>
      </div>
      <div style="font-size:20px;font-weight:800;color:#ef4444;padding:6px 14px;background:rgba(239,68,68,0.1);border-radius:10px;border:1px solid rgba(239,68,68,0.3)">${d.blood_group}</div>
    </div>`).join('') : '<div style="color:var(--muted);text-align:center;padding:30px;font-size:14px">No donors found for this blood group</div>';
}

// GENERATE PDF REPORT
async function generateReport() {
  const res = await fetch('/api/generate-report');
  const data = await res.json();
  const content = `
HEALTHAI PRO — HEALTH REPORT
Generated: ${data.generated_at}
================================
PATIENT DETAILS
Name: ${data.patient.name}
Email: ${data.patient.email}
Age: ${data.patient.age || 'Not set'}
Blood Group: ${data.patient.blood_group || 'Not set'}
================================
DIAGNOSIS HISTORY (Last 10)
${data.diagnoses.map(d=>`• ${d.diagnosis} — ${d.confidence}% confidence — ${d.date}`).join('\n')}
================================
SUMMARY
Total Appointments: ${data.appointments}
Total Prescriptions: ${data.prescriptions}
================================
DISCLAIMER: This report is AI-generated.
Always consult a qualified doctor.
  `;
  const blob = new Blob([content], {type:'text/plain'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `HealthReport_${data.patient.name.replace(' ','_')}_${Date.now()}.txt`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('Report downloaded!', 'success');
}
async function loadProfile() {
  if(!currentUser) return;
  document.getElementById('profileAvatar').textContent = currentUser.avatar;
  document.getElementById('profileName').textContent = currentUser.name;
  document.getElementById('profileEmail').textContent = currentUser.email;
  document.getElementById('profileJoined').textContent = 'Member since ' + currentUser.created_at;
  document.getElementById('pName').value = currentUser.name || '';
  document.getElementById('pPhone').value = currentUser.phone || '';
  document.getElementById('pAge').value = currentUser.age || '';
  document.getElementById('pBlood').value = currentUser.blood_group || '';
  document.getElementById('pAddress').value = currentUser.address || '';
  document.getElementById('pBio').value = currentUser.bio || '';
}

async function saveProfile() {
  const data = {
    name: document.getElementById('pName').value,
    phone: document.getElementById('pPhone').value,
    age: parseInt(document.getElementById('pAge').value) || 0,
    blood_group: document.getElementById('pBlood').value,
    address: document.getElementById('pAddress').value,
    bio: document.getElementById('pBio').value
  };
  const res = await fetch('/api/update-profile', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  const d = await res.json();
  currentUser = {...currentUser, ...data};
  showToast(d.message, 'success');
}

window.addEventListener('DOMContentLoaded', init);
