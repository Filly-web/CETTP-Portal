<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Batch Invoice Processing | Britam EFD Portal</title>
<style>
:root{--blue:#0874d1;--ink:#172b4d;--muted:#71839b;--line:#e6edf5;--bg:#f5f8fc;--green:#138451;--red:#a52b38}*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:Arial,sans-serif;color:var(--ink)}.wrap{max-width:1120px;margin:0 auto;padding:28px 20px}.top{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-bottom:22px}.brand{font-weight:800;font-size:20px}.brand span{display:block;color:var(--muted);font-size:11px;font-weight:500;margin-top:4px}.btn{display:inline-block;border:0;border-radius:9px;background:var(--blue);color:#fff;text-decoration:none;padding:11px 16px;font-weight:700;font-size:13px;cursor:pointer}.btn.secondary{background:#edf5ff;color:#0756a5;border:1px solid #d7e8fb}.btn.danger{background:#fff0f1;color:var(--red);border:1px solid #ffd1d5}.btn:disabled{opacity:.45;cursor:not-allowed}.panel{background:#fff;border:1px solid var(--line);border-radius:14px;padding:22px;margin-bottom:18px;box-shadow:0 5px 18px #1d35570a}.intro h1{margin:0 0 8px;font-size:25px}.intro p{margin:0;color:var(--muted);font-size:14px;line-height:1.5}.field{margin:15px 0}.field label{display:block;font-size:13px;font-weight:700;margin-bottom:7px}.field input{width:100%;padding:11px;border:1px solid #cfd9e7;border-radius:8px;font:inherit}.hint{font-size:12px;color:var(--muted);margin-top:6px}.flash{padding:12px 14px;border-radius:9px;margin:0 0 15px;font-size:13px}.flash.error{background:#fff0f1;color:#9d2430;border:1px solid #ffcbd0}.flash.success{background:#e9fbf1;color:#126b42;border:1px solid #b9efd0}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:700px;font-size:13px}th,td{text-align:left;padding:11px;border-bottom:1px solid var(--line);vertical-align:middle}th{font-size:11px;color:var(--muted);text-transform:uppercase;background:#f8fbff}.empty{padding:22px;text-align:center;color:var(--muted);border:1px dashed #cbd8e8;border-radius:10px}.actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.pill{display:inline-block;background:#edf5ff;color:#0756a5;border-radius:20px;padding:5px 9px;font-size:11px;font-weight:700}.note{background:#f7faff;border:1px solid #e0ebf8;padding:13px;border-radius:9px;font-size:12px;color:#536d8c;line-height:1.5}.back{color:#0756a5;text-decoration:none;font-size:13px;font-weight:700}.step{font-size:12px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px}.count{font-size:14px;font-weight:700;color:#0756a5}@media(max-width:650px){.wrap{padding:17px 12px}.top{align-items:flex-start;flex-direction:column}.panel{padding:16px}.intro h1{font-size:21px}}
</style>
</head>
<body><div class="wrap">
<header class="top"><div class="brand">Britam EFD Portal<span>Tax Compliance Workspace</span></div><div class="actions"><a class="btn secondary" href="/efd-invoice/">← EFD Portal</a><a class="back" href="/">Back to CETTP</a></div></header>
{% with messages = get_flashed_messages(with_categories=true) %}{% for category, message in messages %}<div class="flash {{ category }}" role="alert">{{ message }}</div>{% endfor %}{% endwith %}
<section class="panel intro"><span class="pill">BATCH PROCESSING</span><h1>Build your invoice batch one invoice at a time</h1><p>Upload one Word invoice, enter its TRA EFD verification code and receipt time, and add it to your batch. Repeat for each invoice. When all invoices have been added, download them together in one ZIP file. Single-invoice processing remains unchanged.</p></section>
<section class="panel">
  <div class="step">Step 1 · Add an invoice</div>
  <form action="/efd-invoice/batch" method="post" enctype="multipart/form-data" id="add-form">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><input type="hidden" name="action" value="add">
    <div class="field"><label for="invoice">Select one Word invoice (.docx)</label><input id="invoice" name="invoice" type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required><div class="hint">Upload one invoice per submission. Maximum 100 invoices in a batch; each upload is subject to the portal 40 MB request limit.</div></div>
    <div class="field"><label for="verification_code">TRA EFD verification code</label><input id="verification_code" name="verification_code" type="text" maxlength="100" placeholder="Enter the verification code" required></div>
    <div class="field"><label for="verification_time">Receipt time</label><input id="verification_time" name="verification_time" type="text" placeholder="HH:MM:SS (e.g. 14:05:09)" pattern="(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]|(?:[01][0-9]|2[0-3])[0-5][0-9][0-5][0-9]" title="Enter HH:MM:SS or HHMMSS" required></div>
    <button class="btn" type="submit" id="add-btn">Add invoice to batch</button>
  </form>
</section>
<section class="panel">
  <div class="actions" style="justify-content:space-between;margin-bottom:14px"><div><div class="step">Step 2 · Review your batch</div><h2 style="margin:0;font-size:19px">Invoices added</h2></div><span class="count">{{ batch_count }} / 100 invoices</span></div>
  {% if items %}
  <div class="table-wrap"><table><thead><tr><th>#</th><th>Invoice filename</th><th>EFD verification code</th><th>Receipt time</th><th>Added</th><th>Action</th></tr></thead><tbody>
  {% for item in items %}<tr><td>{{ loop.index }}</td><td>{{ item.original_filename }}</td><td>{{ item.verification_code }}</td><td>{{ item.receipt_time }}</td><td>{{ item.created_at }}</td><td><form action="/efd-invoice/batch" method="post" onsubmit="return confirm('Remove this invoice from the batch?')"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><input type="hidden" name="action" value="remove"><input type="hidden" name="item_id" value="{{ item.id }}"><button class="btn danger" type="submit">Remove</button></form></td></tr>{% endfor %}
  </tbody></table></div>
  <div class="note" style="margin-top:14px">Each row has its own EFD verification code and receipt time. Review the matching details carefully before downloading.</div>
  {% else %}<div class="empty">No invoices have been added yet. Start by uploading the first invoice above.</div>{% endif %}
</section>
<section class="panel">
  <div class="step">Step 3 · Download completed batch</div>
  <form action="/efd-invoice/batch" method="post" class="actions" id="finish-form"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><input type="hidden" name="action" value="process">
    <div class="field" style="flex:1;min-width:240px;margin:0"><label for="batch_name">ZIP filename / batch reference</label><input id="batch_name" name="batch_name" maxlength="80" placeholder="e.g. MEDICAL_INVOICES_NOV_2026"></div>
    <button class="btn" type="submit" {% if not items %}disabled{% endif %} onclick="return confirm('Process all {{ batch_count }} invoice(s) and download the ZIP package?')">Process and download ZIP</button>
  </form>
  <form action="/efd-invoice/batch" method="post" style="margin-top:12px" onsubmit="return confirm('Clear all invoices currently staged in this batch?')"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><input type="hidden" name="action" value="clear"><button class="btn danger" type="submit" {% if not items %}disabled{% endif %}>Clear batch</button></form>
</section>
</div>
<script>
document.getElementById('add-form').addEventListener('submit',function(){const b=document.getElementById('add-btn');b.disabled=true;b.textContent='Adding invoice…';});
document.getElementById('finish-form').addEventListener('submit',function(){const b=this.querySelector('button[type="submit"]');if(b&&!b.disabled){b.disabled=true;b.textContent='Processing batch… Please wait';}});
</script></body></html>
