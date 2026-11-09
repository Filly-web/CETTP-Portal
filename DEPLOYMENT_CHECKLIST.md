<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}Fixed Asset Governance Portal{% endblock %}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.datatables.net/2.1.8/css/dataTables.bootstrap5.min.css" rel="stylesheet">
<link href="{{ url_for('static', filename='css/far.css') }}" rel="stylesheet">
</head><body>
<nav class="navbar navbar-expand-lg navbar-dark far-topbar"><div class="container-fluid px-3 px-xl-4">
<a class="navbar-brand d-flex align-items-center gap-2" href="{{ url_for('fixed_assets.dashboard') if current_role else url_for('login') }}"><span class="brand-mark">FA</span><span>BRITAM <small class="d-block brand-subtitle">FIXED ASSET GOVERNANCE</small></span></a>
<div class="ms-auto d-flex align-items-center gap-2">{% if current_role %}<span class="text-white-50 small d-none d-md-inline">{{ current_user_name }}</span><a class="btn btn-sm btn-light" href="{{ url_for('logout') }}">Sign out</a>{% endif %}</div>
</div></nav>
{% if current_role %}<div class="layout"><aside class="sidebar"><div class="side-caption">ASSET MANAGEMENT</div>
{% for ep,label,ico in [('fixed_assets.dashboard','Dashboard','▦'),('fixed_assets.register','Master FAR','▤'),('fixed_assets.import_far','Import FAR','⇧'),('fixed_assets.depreciation','Depreciation','∑'),('fixed_assets.trial_balance','Trial Balance & GL','▥'),('fixed_assets.reconciliation','FAR Reconciliation','↔'),('fixed_assets.cwip','CWIP Projects','▧'),('fixed_assets.verification','Physical Verification','☑'),('fixed_assets.insurance','Insurance Register','◇'),('fixed_assets.tax_schedules','Tax & Deferred Tax','%'),('fixed_assets.periods','Period Controls','▣'),('fixed_assets.audit_pack','Audit Pack Export','⇩'),('fixed_assets.audit_log','Audit Trail','◷')] %}
<a class="side-link {{ 'active' if request.endpoint == ep else '' }}" href="{{ url_for(ep) }}"><span>{{ ico }}</span>{{ label }}</a>{% endfor %}
<div class="sidebar-foot">Financial control workspace<br><small>Internal use only</small></div></aside><main class="main-area">{% else %}<main class="login-area">{% endif %}
{% with messages=get_flashed_messages(with_categories=true) %}{% for category,message in messages %}<div class="alert alert-{{ category }} alert-dismissible fade show">{{ message }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>{% endfor %}{% endwith %}
{% block content %}{% endblock %}
<footer class="footer"><span>FIXED ASSET GOVERNANCE PORTAL</span><span>Internal financial control system</span></footer>
</main>{% if current_role %}</div>{% endif %}
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>{% block scripts %}{% endblock %}
</body></html>
