"""Small dependency-free Admin interface over the same authenticated API."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["admin-ui"])

_PAGE = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI My Time — Admin</title><style>
:root{font-family:Inter,system-ui,sans-serif;color:#16202a;background:#f6f8fb}body{margin:0}main{max-width:1180px;margin:auto;padding:28px}h1{margin:0 0 6px}h2{font-size:18px;margin:0 0 12px}.muted{color:#64748b}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px}.card,section{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px;margin-top:18px}.metric{font-size:28px;font-weight:700}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;border-bottom:1px solid #e2e8f0;padding:9px;vertical-align:top}button{background:#0f766e;color:#fff;border:0;border-radius:6px;padding:8px 11px;cursor:pointer}button.secondary{background:#475569}input{padding:9px;border:1px solid #cbd5e1;border-radius:6px;margin:3px;width:220px}.hidden{display:none}pre{white-space:pre-wrap;overflow:auto;background:#f8fafc;padding:10px;border-radius:6px;max-height:320px}a{color:#0f766e;cursor:pointer}@media(max-width:650px){main{padding:14px}table{font-size:12px}}
</style></head><body><main>
<header><h1>AI My Time — Admin</h1><div id="identity" class="muted">Вход требуется</div></header>
<section id="login"><h2>Вход</h2><form id="login-form"><input name="email" type="email" placeholder="email" required><input name="password" type="password" placeholder="пароль" required><button>Войти</button></form><div id="login-error" class="muted"></div></section>
<div id="app" class="hidden"><section><div class="grid" id="dashboard"></div></section>
<section><h2>Люди</h2><input id="search" placeholder="Имя, username или UUID"><button class="secondary" id="search-button">Найти</button><div id="people"></div></section>
<section><h2>Заявки на консультацию</h2><div id="consultations"></div></section>
<section><h2>Очередь внимания</h2><div id="attention"></div></section>
<section><h2>Сегменты</h2><div id="segments"></div></section>
<section><h2>Рассылки</h2><div class="muted">Запуск доступен только через preview и отдельное подтверждение в API.</div><div id="broadcasts"></div></section>
<section id="person-panel" class="hidden"><h2>Карточка человека</h2><pre id="person"></pre></section>
<button class="secondary" id="logout">Выйти</button></div>
</main><script>
const $=id=>document.getElementById(id); const esc=v=>String(v??'—').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
async function api(path,opts={}){const r=await fetch(path,{credentials:'same-origin',headers:{'Content-Type':'application/json',...(opts.headers||{})},...opts});if(!r.ok)throw new Error((await r.json().catch(()=>({detail:r.statusText}))).detail||r.statusText);return r.status===204?null:r.json()}
function table(rows, cols){if(!rows.length)return '<p class="muted">Нет данных</p>';return '<table><thead><tr>'+cols.map(c=>'<th>'+c[0]+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+cols.map(c=>'<td>'+(typeof c[1]==='function'?c[1](r):esc(r[c[1]]))+'</td>').join('')+'</tr>').join('')+'</tbody></table>'}
async function load(){const [d,p,c,a,s,b]=await Promise.all([api('/admin/dashboard'),api('/admin/people?limit=50'+($('search').value?'&search='+encodeURIComponent($('search').value):'')),api('/admin/consultations'),api('/admin/attention'),api('/admin/segments'),api('/admin/broadcasts')]);$('dashboard').innerHTML=[['Новые люди',d.new_people],['Диагностики начаты',d.started_diagnostics],['Диагностики завершены',d.completed_diagnostics],['Заявки',d.consultation_requests],['Внимание',d.attention_items]].map(x=>'<div class="card"><div class="muted">'+x[0]+'</div><div class="metric">'+x[1]+'</div></div>').join('');$('people').innerHTML=table(p.items,[['Имя',x=>'<a data-person="'+x.user_id+'">'+esc(x.display_name||x.telegram_username||x.user_id)+'</a>'],['Этап','lifecycle_stage'],['Диагностика','diagnostic_status'],['Консультация','consultation_status'],['Связь','communication_status'],['Внимание','attention_count']]);$('consultations').innerHTML=table(c.items,[['Создана',x=>new Date(x.created_at).toLocaleString()],['Статус','status'],['Источник','source'],['Диагностика',x=>esc(x.diagnostic_session_id).slice(0,8)]]);$('attention').innerHTML=table(a.items,[['Причина','reason'],['Приоритет','priority'],['Статус','status'],['Создано',x=>new Date(x.created_at).toLocaleString()]]);$('segments').innerHTML=table(s.items,[['Сегмент','title'],['Ключ','key'],['Допущено','eligible_count']]);$('broadcasts').innerHTML=table(b.items,[['Название','title'],['Статус','status'],['Допущено','eligible_count'],['В очереди','queued_count'],['Отправлено','sent_count'],['Ошибки','failed_count']]);document.querySelectorAll('[data-person]').forEach(x=>x.onclick=()=>person(x.dataset.person))}
async function person(id){const data=await api('/admin/people/'+id);$('person-panel').classList.remove('hidden');$('person').textContent=JSON.stringify(data,null,2);window.scrollTo({top:document.body.scrollHeight,behavior:'smooth'})}
async function ready(){try{const me=await api('/admin/auth/me');$('identity').textContent=me.email+' · '+me.role;$('login').classList.add('hidden');$('app').classList.remove('hidden');await load()}catch{}}
$('login-form').onsubmit=async e=>{e.preventDefault();try{const f=new FormData(e.target);await api('/admin/auth/login',{method:'POST',body:JSON.stringify(Object.fromEntries(f))});await ready()}catch(err){$('login-error').textContent='Не удалось войти: '+err.message}};$('search-button').onclick=load;$('logout').onclick=async()=>{await api('/admin/auth/logout',{method:'POST',headers:{Origin:location.origin}});location.reload()};ready();
</script></body></html>"""


@router.get("/admin/", include_in_schema=False, response_class=HTMLResponse)
async def admin_ui() -> HTMLResponse:
    return HTMLResponse(_PAGE, headers={"Cache-Control": "no-store"})
