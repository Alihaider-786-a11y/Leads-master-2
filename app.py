import os,csv,io,secrets,sqlite3
from datetime import datetime
from fastapi import FastAPI,Request,Form,UploadFile,File
from fastapi.responses import HTMLResponse,RedirectResponse,StreamingResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
load_dotenv()
DB="leads_master.db"; USER=os.getenv("ADMIN_USERNAME","admin"); PASS=os.getenv("ADMIN_PASSWORD","ChangeThisPassword123!"); SECRET=os.getenv("SECRET_KEY","change-me")
app=FastAPI(title="Leads Master Pro",version="2.0"); app.add_middleware(SessionMiddleware,secret_key=SECRET,max_age=28800); app.mount("/static",StaticFiles(directory="static"),name="static")
def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 c=db(); c.execute("""CREATE TABLE IF NOT EXISTS leads(
 id INTEGER PRIMARY KEY AUTOINCREMENT, company_name TEXT NOT NULL, website TEXT,email TEXT,phone TEXT,
 country TEXT,city TEXT,industry TEXT,category TEXT,company_size TEXT,event_type TEXT,contact_name TEXT,
 job_title TEXT,linkedin TEXT,source TEXT,status TEXT DEFAULT 'New',score INTEGER DEFAULT 0,notes TEXT,created_at TEXT)""")
 c.commit(); c.close()
init()
def ok(r): return bool(r.session.get("admin"))
def guard(r):
 if not ok(r): return RedirectResponse("/login",303)
def nav(active):
 items=[("dashboard","⌂ Dashboard","/"),("finder","⌕ Lead Finder","/finder"),("leads","▦ All Leads","/leads"),("add","＋ Add Lead","/leads/new"),("import","⇧ Import CSV","/import"),("export","⇩ Export CSV","/export.csv")]
 return "".join(f'<a class="nav {"active" if active==k else ""}" href="{u}"><i>{ic}</i>{txt[2:]}</a>' for k,txt,u in items for ic in [txt[0]])
def layout(title,content,active="dashboard"):
 return f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>{title} · Leads Master</title><link rel=stylesheet href=/static/style.css></head><body>
<aside><div class=logo><span>LM</span><div>LEADS <b>MASTER</b><small>BUSINESS INTELLIGENCE</small></div></div><div class=navtitle>WORKSPACE</div>{nav(active)}
<div class=sidebottom><a class=nav href="/api/leads"><i>⌁</i>API</a><a class=nav href="/logout"><i>↪</i>Logout</a></div></aside>
<main><header><div><div class=eyebrow>LEADS MASTER / {title.upper()}</div><h1>{title}</h1></div><div class=user><span class=avatar>AD</span><div><b>Administrator</b><small>Lead Manager</small></div></div></header>{content}</main></body></html>"""
def login_page(msg=""):
 return f"""<!doctype html><html><head><meta charset=utf-8><link rel=stylesheet href=/static/style.css><title>Leads Master Login</title></head><body class=login><form class=loginbox method=post><div class=loginlogo><span>LM</span><h1>Leads <b>Master</b></h1><small>BUSINESS INTELLIGENCE PLATFORM</small></div><h2>Welcome back</h2><p class=muted>Sign in to your lead management workspace.</p>{f'<div class=error>{msg}</div>' if msg else ''}<label>Username<input name=username required value=admin></label><label>Password<input type=password name=password required></label><button>Sign in to Leads Master →</button></form></body></html>"""
@app.get("/login",response_class=HTMLResponse)
def lp(): return login_page()
@app.post("/login")
def li(request:Request,username:str=Form(...),password:str=Form(...)):
 if secrets.compare_digest(username,USER) and secrets.compare_digest(password,PASS):
  request.session["admin"]=username; return RedirectResponse("/",303)
 return HTMLResponse(login_page("Invalid username or password."),401)
@app.get("/logout")
def lo(request:Request): request.session.clear(); return RedirectResponse("/login",303)
@app.get("/",response_class=HTMLResponse)
def dash(request:Request):
 if g:=guard(request): return g
 c=db(); total=c.execute("select count(*) x from leads").fetchone()["x"]; countries=c.execute("select count(distinct country) x from leads where country!=''").fetchone()["x"]; sponsors=c.execute("select count(*) x from leads where category='Sponsor'").fetchone()["x"]; new=c.execute("select count(*) x from leads where status='New'").fetchone()["x"]; top=c.execute("select industry,count(*) n from leads where industry!='' group by industry order by n desc limit 6").fetchall(); recent=c.execute("select * from leads order by id desc limit 7").fetchall(); c.close()
 cards=f"""<div class=stats><div class=stat><span class=staticon>◎</span><small>TOTAL LEADS</small><strong>{total:,}</strong><em>Database records</em></div><div class=stat><span class=staticon>◉</span><small>COUNTRIES</small><strong>{countries:,}</strong><em>Global coverage</em></div><div class=stat><span class=staticon>◆</span><small>SPONSORS</small><strong>{sponsors:,}</strong><em>Potential sponsors</em></div><div class=stat><span class=staticon>✦</span><small>NEW LEADS</small><strong>{new:,}</strong><em>Ready to review</em></div></div>"""
 search="""<div class=hero><div><span class=kicker>INTELLIGENT LEAD DISCOVERY</span><h2>Find the right companies.<br><b>Build better pipelines.</b></h2><p>Search your business database by company, industry, country, category and event.</p></div><form action=/finder class=heroform><input name=q placeholder="e.g. Clinical Trials, Pharma, Hotel Tech..."><select name=country><option value="">All Countries</option></select><button>Search Leads →</button></form></div>"""
 tophtml="".join(f"<div class=barrow><span>{r['industry']}</span><div><i style='width:{min(100,r['n']*12)}%'></i></div><b>{r['n']}</b></div>" for r in top) or "<p class=muted>No data yet. Add/import your first leads.</p>"
 rows="".join(f"<tr><td><b>{r['company_name']}</b><small>{r['contact_name'] or 'No contact'} · {r['job_title'] or '—'}</small></td><td>{r['country'] or '—'}</td><td><span class=tag>{r['category'] or 'Company'}</span></td><td>{r['email'] or '—'}</td><td><a class=iconbtn href=/leads/{r['id']}>→</a></td></tr>" for r in recent) or "<tr><td colspan=5>No leads available.</td></tr>"
 body=cards+search+f"""<div class=twocol><section class=card><div class=cardhead><div><small>ANALYTICS</small><h3>Top Industries</h3></div></div>{tophtml}</section><section class=card><div class=cardhead><div><small>DATABASE</small><h3>Recent Leads</h3></div><a class=btn href=/leads>View all →</a></div><div class=tablewrap><table><tr><th>COMPANY</th><th>COUNTRY</th><th>TYPE</th><th>EMAIL</th><th></th></tr>{rows}</table></div></section></div>"""
 return layout("Dashboard",body)
@app.get("/finder",response_class=HTMLResponse)
def finder(request:Request,q="",country="",industry="",category="",size="",event=""):
 if g:=guard(request): return g
 c=db(); clauses=[]; args=[]
 vals=[("country",country),("industry",industry),("category",category),("company_size",size),("event_type",event)]
 for f,v in vals:
  if v: clauses.append(f"{f}=?");args.append(v)
 if q: clauses.append("(company_name like ? or email like ? or contact_name like ? or industry like ? or event_type like ?)");args += [f"%{q}%"]*5
 where=" WHERE "+" AND ".join(clauses) if clauses else ""
 rows=c.execute("select * from leads"+where+" order by score desc,id desc limit 500",args).fetchall()
 countries=c.execute("select distinct country from leads where country!='' order by country").fetchall(); inds=c.execute("select distinct industry from leads where industry!='' order by industry").fetchall(); c.close()
 opts=lambda rs,cur:"".join(f"<option {'selected' if x[0]==cur else ''}>{x[0]}</option>" for x in rs)
 body=f"""<div class=searchpanel><div class=searchtitle><span class=kicker>LEAD FINDER</span><h2>Discover your next opportunity</h2><p>Use multiple filters to narrow down your target market.</p></div>
 <form class=filtergrid><label>Keyword<input name=q value="{q}" placeholder="Company, person, email..."></label><label>Country<select name=country><option value="">All Countries</option>{opts(countries,country)}</select></label><label>Industry<select name=industry><option value="">All Industries</option>{opts(inds,industry)}</select></label>
 <label>Category<select name=category><option value="">All Types</option>{''.join(f'<option {"selected" if category==x else ""}>{x}</option>' for x in ["Company","Delegate","Sponsor","Partner"])}</select></label><label>Company Size<select name=size><option value="">Any Size</option>{''.join(f'<option {"selected" if size==x else ""}>{x}</option>' for x in ["1-10","11-50","51-200","201-500","501-1000","1001+"])}</select></label><label>Event / Topic<input name=event value="{event}" placeholder="Clinical Trials..."></label><button>Run Search →</button><a class=btn href=/finder>Clear</a></form></div>
 <div class=card><div class=cardhead><div><small>SEARCH RESULTS</small><h3>{len(rows)} leads found</h3></div><a class=btn href=/export.csv>Export results</a></div><div class=tablewrap><table><tr><th>COMPANY / CONTACT</th><th>LOCATION</th><th>INDUSTRY</th><th>TYPE</th><th>CONTACT</th><th>SCORE</th><th></th></tr>"""
 body+="".join(f"<tr><td><b>{r['company_name']}</b><small>{r['contact_name'] or 'No contact'} · {r['job_title'] or '—'}</small></td><td>{r['city'] or '—'}<br>{r['country'] or '—'}</td><td>{r['industry'] or '—'}</td><td><span class=tag>{r['category'] or 'Company'}</span></td><td>{r['email'] or '—'}<br>{r['phone'] or ''}</td><td><span class=score>{r['score']}/100</span></td><td><a class=iconbtn href=/leads/{r['id']}>→</a></td></tr>" for r in rows) or "<tr><td colspan=7 class=empty>No matching leads. Try broader filters.</td></tr>"
 body+="</table></div></div>"
 return layout("Lead Finder",body,"finder")
@app.get("/leads",response_class=HTMLResponse)
def all_leads(request:Request,q=""):
 if g:=guard(request): return g
 return RedirectResponse("/finder?q="+q,303)
fields=["company_name","website","email","phone","country","city","industry","category","company_size","event_type","contact_name","job_title","linkedin","source","status","score","notes"]
labels={"company_name":"Company Name *","website":"Website","email":"Business Email","phone":"Business Phone","country":"Country","city":"City","industry":"Industry","company_size":"Company Size","event_type":"Event / Topic","contact_name":"Contact Person","job_title":"Job Title","linkedin":"LinkedIn / Company Profile","source":"Data Source","status":"Lead Status","score":"Lead Score (0-100)","notes":"Notes"}
def form_page(r=None):
 r=r or {}; val=lambda k:str(r.get(k,"")).replace('"',"&quot;")
 controls=""
 for k in fields:
  if k in ("category","status"):
   options=["Company","Delegate","Sponsor","Partner"] if k=="category" else ["New","Qualified","Contacted","Converted","Archived"]
   controls+=f"<label>{labels[k]}<select name={k}>"+ "".join(f"<option {'selected' if r.get(k,options[0])==o else ''}>{o}</option>" for o in options)+"</select></label>"
  elif k=="notes": controls+=f"<label class=full>{labels[k]}<textarea name={k}>{val(k)}</textarea></label>"
  else: controls+=f"<label>{labels[k]}<input name={k} value=\"{val(k)}\"></label>"
 return f"""<div class=card><div class=cardhead><div><span class=kicker>DATABASE</span><h3>{'Edit Lead' if r else 'Create New Lead'}</h3></div></div><form class=formgrid>{controls}<div class=full><button>Save Lead →</button> <a class=btn href=/leads>Cancel</a></div></form></div>"""
@app.get("/leads/new",response_class=HTMLResponse)
def new(request:Request):
 if g:=guard(request): return g
 return layout("Add Lead",form_page(), "add")
@app.post("/leads/new")
async def create(request:Request):
 if g:=guard(request): return g
 d=dict(await request.form()); c=db()
 if not d.get("company_name"): return HTMLResponse("Company name required",400)
 vals=[d.get(f,"") for f in fields]
 c.execute(f"insert into leads ({','.join(fields)},created_at) values ({','.join('?' for _ in fields)},?)",vals+[datetime.utcnow().isoformat()]);c.commit();c.close();return RedirectResponse("/finder",303)
@app.get("/leads/{id}",response_class=HTMLResponse)
def detail(request:Request,id:int):
 if g:=guard(request): return g
 c=db();r=c.execute("select * from leads where id=?",(id,)).fetchone();c.close()
 if not r:return HTMLResponse("Not found",404)
 vals="".join(f"<div class=detailitem><small>{labels[k].replace(' *','')}</small><p>{r[k] or '—'}</p></div>" for k in fields)
 body=f"""<div class=card><div class=cardhead><div><span class=kicker>{r['category'] or 'LEAD'}</span><h2>{r['company_name']}</h2></div><div><a class=btn href=/leads/{id}/edit>Edit</a> <form style=display:inline method=post action=/leads/{id}/delete><button class=danger>Delete</button></form></div></div><div class=detailgrid>{vals}</div></div>"""
 return layout("Lead Details",body,"leads")
@app.get("/leads/{id}/edit",response_class=HTMLResponse)
def edit(request:Request,id:int):
 if g:=guard(request): return g
 c=db();r=c.execute("select * from leads where id=?",(id,)).fetchone();c.close()
 return layout("Edit Lead",form_page(dict(r) if r else None),"leads")
@app.post("/leads/{id}/edit")
async def update(request:Request,id:int):
 if g:=guard(request): return g
 d=dict(await request.form());c=db();vals=[d.get(f,"") for f in fields];c.execute(f"update leads set {','.join(f+'=?' for f in fields)} where id=?",vals+[id]);c.commit();c.close();return RedirectResponse(f"/leads/{id}",303)
@app.post("/leads/{id}/delete")
def delete(request:Request,id:int):
 if g:=guard(request): return g
 c=db();c.execute("delete from leads where id=?",(id,));c.commit();c.close();return RedirectResponse("/finder",303)
@app.get("/import",response_class=HTMLResponse)
def imp(request:Request):
 if g:=guard(request):return g
 return layout("Import CSV",f"""<div class=card><span class=kicker>DATA INGESTION</span><h2>Import your lead database</h2><p class=muted>Upload a CSV with columns: {', '.join(fields)}</p><form class=upload method=post enctype=multipart/form-data><input type=file name=file accept=.csv required><button>Import Leads →</button></form></div>""","import")
@app.post("/import")
async def imp_post(request:Request,file:UploadFile=File(...)):
 if g:=guard(request):return g
 text=(await file.read()).decode("utf-8-sig","ignore");reader=csv.DictReader(io.StringIO(text));c=db();n=0
 for row in reader:
  if not row.get("company_name"):continue
  vs=[row.get(f,"") for f in fields];c.execute(f"insert into leads ({','.join(fields)},created_at) values ({','.join('?' for _ in fields)},?)",vs+[datetime.utcnow().isoformat()]);n+=1
 c.commit();c.close();return RedirectResponse("/finder",303)
@app.get("/export.csv")
def export(request:Request):
 if g:=guard(request):return g
 c=db();rows=c.execute("select * from leads order by id desc").fetchall();c.close();out=io.StringIO();w=csv.DictWriter(out,fieldnames=["id"]+fields+["created_at"]);w.writeheader()
 for r in rows:w.writerow({"id":r["id"],**{f:r[f] for f in fields},"created_at":r["created_at"]})
 return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=leads_master.csv"})
@app.get("/api/leads")
def api(request:Request,q=""):
 if not ok(request):return JSONResponse({"error":"unauthorized"},401)
 c=db();rows=c.execute("select * from leads where company_name like ? or email like ? order by id desc limit 500",(f"%{q}%",f"%{q}%")).fetchall();c.close();return {"count":len(rows),"data":[dict(x) for x in rows]}
