from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from database import get_conn, update_application_status

def get_data():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    screening = conn.execute("SELECT COUNT(*) FROM applications WHERE status='screening'").fetchone()[0]
    interview = conn.execute("SELECT COUNT(*) FROM applications WHERE status='interview'").fetchone()[0]
    rejected = conn.execute("SELECT COUNT(*) FROM applications WHERE status='rejected'").fetchone()[0]
    offer = conn.execute("SELECT COUNT(*) FROM applications WHERE status='offer'").fetchone()[0]
    manually_applied = conn.execute("SELECT COUNT(*) FROM applications WHERE status='manually_applied'").fetchone()[0]
    cold_sent = conn.execute("SELECT COUNT(*) FROM email_outreach WHERE status!='pending'").fetchone()[0]
    f1 = conn.execute("SELECT COUNT(*) FROM email_outreach WHERE status IN ('followup1_sent','followup2_sent','thankyou_sent')").fetchone()[0]
    f2 = conn.execute("SELECT COUNT(*) FROM email_outreach WHERE status IN ('followup2_sent','thankyou_sent')").fetchone()[0]
    ty = conn.execute("SELECT COUNT(*) FROM email_outreach WHERE status='thankyou_sent'").fetchone()[0]
    inv = conn.execute("SELECT COUNT(*) FROM inbox_log WHERE classification='interview_invite'").fetchone()[0]
    rej_moved = conn.execute("SELECT COUNT(*) FROM inbox_log WHERE classification='rejection'").fetchone()[0]
    jobs = conn.execute("""
        SELECT id, job_title, company, job_board, job_url, status, applied_at, resume_used
        FROM applications
        WHERE job_title NOT LIKE '%Gartner%'
        AND job_title NOT LIKE '%Magic Quadrant%'
        AND job_title NOT LIKE '%Sponsor%'
        AND job_title NOT LIKE '%Rovo%'
        AND job_title NOT LIKE '%Ship high%'
        AND job_title NOT LIKE '%Fund open%'
        AND LENGTH(job_title) < 60
        ORDER BY applied_at DESC
    """).fetchall()
    outreach = conn.execute("""
        SELECT e.company, e.recruiter_email, e.status, e.cold_email_sent_at
        FROM email_outreach e ORDER BY e.id DESC LIMIT 21
    """).fetchall()
    inbox = conn.execute("SELECT subject,from_address,classification,action_taken FROM inbox_log ORDER BY received_at DESC LIMIT 10").fetchall()
    conn.close()
    return dict(total=total,screening=screening,interview=interview,rejected=rejected,offer=offer,
                manually_applied=manually_applied,cold_sent=cold_sent,f1=f1,f2=f2,ty=ty,
                inv=inv,rej_moved=rej_moved,jobs=[dict(j) for j in jobs],
                outreach=[dict(o) for o in outreach],inbox=[dict(i) for i in inbox])

def status_badge(status):
    styles = {
        "applied": ("To Apply","#1e3a5f","#60a5fa"),
        "manually_applied": ("Applied","#1a3a1a","#4ade80"),
        "screening": ("Screening","#3a2a0a","#fbbf24"),
        "interview": ("Interview","#1a3a1a","#4ade80"),
        "rejected": ("Rejected","#3a1a1a","#f87171"),
        "offer": ("Offer","#2a1a3a","#a78bfa"),
    }
    label, bg, fg = styles.get(status, (status,"#2a2a2a","#888"))
    return f'<span style="background:{bg};color:{fg};padding:3px 10px;border-radius:99px;font-size:11px;font-weight:500;white-space:nowrap">{label}</span>'

def email_badge(status):
    styles = {
        "cold_sent": ("Cold Sent","#1e3a5f","#60a5fa"),
        "followup1_sent": ("Follow-up 1","#3a2a0a","#fbbf24"),
        "followup2_sent": ("Follow-up 2","#2a1a3a","#a78bfa"),
        "thankyou_sent": ("Thank-you","#1a3a1a","#4ade80"),
        "pending": ("Pending","#2a2a2a","#666"),
    }
    label, bg, fg = styles.get(status, (status,"#2a2a2a","#666"))
    return f'<span style="background:{bg};color:{fg};padding:3px 10px;border-radius:99px;font-size:11px;font-weight:500">{label}</span>'

def inbox_badge(cls):
    styles = {
        "interview_invite": ("Interview","#1a3a1a","#4ade80"),
        "screening": ("Screening","#3a2a0a","#fbbf24"),
        "rejection": ("Rejection","#3a1a1a","#f87171"),
        "offer": ("Offer","#2a1a3a","#a78bfa"),
        "noise": ("Noise","#2a2a2a","#666"),
        "other": ("Other","#2a2a2a","#666"),
    }
    label, bg, fg = styles.get(cls, (cls,"#2a2a2a","#666"))
    return f'<span style="background:{bg};color:{fg};padding:3px 10px;border-radius:99px;font-size:11px;font-weight:500">{label}</span>'

def render(d):
    job_rows = ""
    for j in d["jobs"]:
        date = (j["applied_at"] or "")[:10]
        title = j["job_title"][:45] + "..." if len(j["job_title"]) > 45 else j["job_title"]
        
        actions = ""
        if j["job_url"]:
            actions += f'<a href="{j["job_url"]}" target="_blank" class="btn btn-blue">Apply</a>'
        if j["resume_used"]:
            actions += f'<a href="/resume?path={j["resume_used"]}" target="_blank" class="btn btn-green">Resume</a>'
        if j["status"] != "manually_applied":
            actions += f'<a href="/mark_applied?id={j["id"]}" class="btn btn-yellow">Mark Applied</a>'
        actions += '<a href="/delete_job?id=' + str(j["id"]) + '" class="btn btn-red">Delete</a>'
        
        job_rows += f"""<tr>
            <td class="role-cell" title="{j["job_title"]}">{title}</td>
            <td><strong>{j["company"]}</strong></td>
            <td><span class="source">{j["job_board"].replace("_"," ").title()}</span></td>
            <td>{status_badge(j["status"])}</td>
            <td class="date-cell">{date}</td>
            <td class="action-cell">{actions}</td>
        </tr>"""

    outreach_rows = ""
    for o in d["outreach"]:
        date = (o["cold_email_sent_at"] or "")[:10]
        outreach_rows += f"""<tr>
            <td><strong>{o["company"]}</strong></td>
            <td class="email-cell">{o["recruiter_email"]}</td>
            <td>{email_badge(o["status"])}</td>
            <td class="date-cell">{date}</td>
        </tr>"""

    inbox_rows = ""
    for i in d["inbox"]:
        subject = i["subject"][:55] + "..." if len(i["subject"]) > 55 else i["subject"]
        inbox_rows += f"""<tr>
            <td>{subject}</td>
            <td class="email-cell">{i["from_address"][:35]}</td>
            <td>{inbox_badge(i["classification"])}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JobPilot</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 32px; }}
  
  .header {{ margin-bottom: 32px; }}
  .header h1 {{ font-size: 26px; font-weight: 700; color: #fff; letter-spacing: -0.5px; }}
  .header p {{ color: #555; font-size: 13px; margin-top: 4px; }}
  
  .stats {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 12px; margin-bottom: 28px; }}
  .stat {{ background: #141414; border: 1px solid #222; border-radius: 10px; padding: 16px; }}
  .stat .num {{ font-size: 30px; font-weight: 700; line-height: 1; }}
  .stat .lbl {{ font-size: 11px; color: #555; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.05em; }}
  
  .section {{ background: #141414; border: 1px solid #222; border-radius: 10px; margin-bottom: 20px; overflow: hidden; }}
  .section-header {{ padding: 16px 20px; border-bottom: 1px solid #1e1e1e; display: flex; align-items: center; justify-content: space-between; }}
  .section-header h2 {{ font-size: 14px; font-weight: 600; color: #fff; }}
  .section-header span {{ font-size: 12px; color: #555; }}
  
  .search-bar {{ padding: 12px 20px; border-bottom: 1px solid #1e1e1e; }}
  .search-bar input {{ width: 100%; background: #0a0a0a; border: 1px solid #222; border-radius: 6px; padding: 8px 12px; color: #e0e0e0; font-size: 13px; outline: none; }}
  .search-bar input:focus {{ border-color: #444; }}
  
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; font-size: 11px; font-weight: 500; color: #555; padding: 10px 20px; border-bottom: 1px solid #1e1e1e; text-transform: uppercase; letter-spacing: 0.05em; }}
  td {{ padding: 12px 20px; border-bottom: 1px solid #141414; font-size: 13px; color: #ccc; vertical-align: middle; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #161616; }}
  
  .role-cell {{ color: #e0e0e0; font-weight: 500; max-width: 280px; }}
  .email-cell {{ color: #888; font-size: 12px; }}
  .date-cell {{ color: #555; font-size: 12px; white-space: nowrap; }}
  .source {{ font-size: 11px; color: #666; background: #1a1a1a; padding: 2px 8px; border-radius: 4px; white-space: nowrap; }}
  .action-cell {{ white-space: nowrap; }}
  
  .btn {{ display: inline-block; padding: 5px 12px; border-radius: 6px; font-size: 11px; font-weight: 500; text-decoration: none; margin-right: 6px; cursor: pointer; }}
  .btn-blue {{ background: #1d4ed8; color: #fff; }}
  .btn-blue:hover {{ background: #2563eb; }}
  .btn-green {{ background: #065f46; color: #fff; }}
  .btn-green:hover {{ background: #047857; }}
  .btn-red {{ background: #450a0a; color: #f87171; border: 1px solid #7f1d1d; }}
  .btn-red:hover {{ background: #7f1d1d; }}
  .btn-yellow {{ background: #92400e; color: #fbbf24; border: 1px solid #78350f; }}
  .btn-yellow:hover {{ background: #78350f; }}
  
  .email-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; padding: 16px 20px; }}
  .email-stat {{ background: #0a0a0a; border: 1px solid #1e1e1e; border-radius: 8px; padding: 14px; text-align: center; }}
  .email-stat .num {{ font-size: 24px; font-weight: 700; color: #60a5fa; }}
  .email-stat .lbl {{ font-size: 11px; color: #555; margin-top: 4px; }}
</style>
</head>
<body>

<div class="header">
  <h1>JobPilot</h1>
  <p>Last updated {datetime.now().strftime("%b %d, %Y at %I:%M %p")} &nbsp;·&nbsp; Auto-refreshes every 60s</p>
</div>

<div class="stats">
  <div class="stat"><div class="num" style="color:#fff">{d["total"]}</div><div class="lbl">Listings Found</div></div>
  <div class="stat"><div class="num" style="color:#60a5fa">{d["manually_applied"]}</div><div class="lbl">Applied</div></div>
  <div class="stat"><div class="num" style="color:#fbbf24">{d["screening"]}</div><div class="lbl">Screening</div></div>
  <div class="stat"><div class="num" style="color:#4ade80">{d["interview"]}</div><div class="lbl">Interviews</div></div>
  <div class="stat"><div class="num" style="color:#f87171">{d["rejected"]}</div><div class="lbl">Rejected</div></div>
  <div class="stat"><div class="num" style="color:#a78bfa">{d["offer"]}</div><div class="lbl">Offers</div></div>
  <div class="stat"><div class="num" style="color:#4ade80">{d["inv"]}</div><div class="lbl">Invites</div></div>
</div>

<div class="section">
  <div class="section-header">
    <h2>Email Outreach</h2>
    <span>21 recruiters contacted</span>
  </div>
  <div class="email-grid">
    <div class="email-stat"><div class="num">{d["cold_sent"]}</div><div class="lbl">Cold Emails</div></div>
    <div class="email-stat"><div class="num" style="color:#fbbf24">{d["f1"]}</div><div class="lbl">Follow-up 1</div></div>
    <div class="email-stat"><div class="num" style="color:#a78bfa">{d["f2"]}</div><div class="lbl">Follow-up 2</div></div>
    <div class="email-stat"><div class="num" style="color:#4ade80">{d["ty"]}</div><div class="lbl">Thank-you</div></div>
  </div>
</div>

<div class="section">
  <div class="section-header">
    <h2>Jobs Ready to Apply</h2>
    <span>Click Apply → upload tailored resume → submit</span>
  </div>
  <div class="search-bar">
    <input type="text" placeholder="Search by role or company..." onkeyup="filterTable(this,'jobTable')">
  </div>
  <table id="jobTable">
    <tr><th>Role</th><th>Company</th><th>Source</th><th>Status</th><th>Found</th><th>Actions</th></tr>
    {job_rows}
  </table>
</div>

<div class="section">
  <div class="section-header">
    <h2>Outreach Tracker</h2>
    <span>Follow-ups auto-send every 7 days</span>
  </div>
  <table>
    <tr><th>Company</th><th>Recruiter</th><th>Status</th><th>Sent</th></tr>
    {outreach_rows}
  </table>
</div>

<div class="section">
  <div class="section-header">
    <h2>Inbox Activity</h2>
    <span>Rejections auto-moved · Interviews flagged</span>
  </div>
  <table>
    <tr><th>Subject</th><th>From</th><th>Classification</th></tr>
    {inbox_rows}
  </table>
</div>

<script>
function filterTable(input, tableId) {{
  const filter = input.value.toLowerCase();
  document.querySelectorAll("#" + tableId + " tr:not(:first-child)").forEach(row => {{
    row.style.display = row.textContent.toLowerCase().includes(filter) ? "" : "none";
  }});
}}
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/delete_job"):
            params = parse_qs(urlparse(self.path).query)
            app_id = params.get("id", [""])[0]
            if app_id:
                conn = get_conn()
                conn.execute("DELETE FROM applications WHERE id = ?", (int(app_id),))
                conn.commit()
                conn.close()
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return

        if self.path.startswith("/mark_applied"):
            params = parse_qs(urlparse(self.path).query)
            app_id = params.get("id", [""])[0]
            if app_id:
                update_application_status(int(app_id), "manually_applied")
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return

        if self.path.startswith("/resume"):
            params = parse_qs(urlparse(self.path).query)
            path = params.get("path", [""])[0]
            if path and path.endswith(".txt"):
                try:
                    with open(path, "r") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-type", "text/plain")
                    self.end_headers()
                    self.wfile.write(content.encode())
                    return
                except:
                    pass
            self.send_response(404)
            self.end_headers()
            return

        html = render(get_data())
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, *a):
        pass

def run_dashboard(port=8080):
    print(f"JobPilot Dashboard -> http://localhost:{port}")
    HTTPServer(("localhost", port), Handler).serve_forever()

if __name__ == "__main__":
    run_dashboard()
