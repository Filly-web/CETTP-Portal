from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO, StringIO
import csv, json, re, secrets, os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, send_file, current_app
from sqlalchemy import func, or_
from openpyxl import load_workbook, Workbook
from werkzeug.utils import secure_filename
from xml.sax.saxutils import escape as xml_escape

MONEY = Decimal('0.01')

def create_fixed_assets_blueprint(db, M):
    bp = Blueprint('fixed_assets', __name__, url_prefix='/fixed-assets', template_folder='templates', static_folder='static')
    Asset=M['Asset']; Category=M['AssetCategory']; ImportBatch=M['AssetImportBatch']; ImportRow=M['AssetImportRow']
    Transfer=M['AssetTransfer']; Disposal=M['AssetDisposal']; DepRun=M['DepreciationRun']; DepLine=M['DepreciationLine']
    TBImport=M['TrialBalanceImport']; TBLine=M['TrialBalanceLine']; GLMap=M['GLMapping']; Recon=M['Reconciliation']
    Investigation=M['ReconciliationInvestigation']; Audit=M['AssetAuditLog']; PeriodLock=M['PeriodLock']; Snapshot=M['AssetPeriodSnapshot']
    Cwip=M['CwipProject']; CwipExp=M['CwipExpenditure']; Verify=M['VerificationRecord']; Insurance=M['InsurancePolicy']; InsuranceClaim=M['InsuranceClaim']; Tax=M['TaxSchedule']; Doc=M['AssetDocument']; Usage=M['DepreciationUsage']

    def actor(): return (session.get('actor_name') or session.get('initiator_email') or 'Unknown user')[:160]
    def required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get('role') not in ('tax', 'asset_admin', 'asset_accountant', 'asset_auditor'):
                if session.get('role') == 'initiator': abort(403)
                return redirect(url_for('home'))
            if session.get('role') == 'asset_auditor' and request.method in ('POST','PUT','DELETE'):
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    def audit(action, module, record=None, old=None, new=None):
        db.session.add(Audit(actor=actor(), action=action, module=module,
            record_type=type(record).__name__ if record is not None else None,
            record_id=str(getattr(record,'id','')) if record is not None else None,
            old_value=old, new_value=new, ip_address=request.remote_addr,
            user_agent=(request.user_agent.string or '')[:255]))
    def safe_text(v):
        value=str(v or '')
        return "'"+value if value[:1] in ('=','+','-','@') else value
    def money(v):
        try: return Decimal(str(v or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError): return Decimal('0.00')
    def parse_date(v):
        if not v: return None
        if isinstance(v, datetime): return v.date()
        if isinstance(v, date): return v
        for fmt in ('%Y-%m-%d','%d/%m/%Y','%m/%d/%Y','%d-%m-%Y'):
            try: return datetime.strptime(str(v).strip()[:10],fmt).date()
            except ValueError: pass
        try: return datetime.fromisoformat(str(v).strip()).date()
        except Exception: return None
    def period_locked(period):
        lock=PeriodLock.query.filter_by(period=period,status='LOCKED').first()
        return lock is not None
    def category_values():
        return [x[0] for x in db.session.query(Asset.major_category).filter(Asset.archived_at.is_(None)).distinct().order_by(Asset.major_category).all() if x[0]]
    def asset_number(major, counters=None):
        code_map={'BUILDINGS':'BLD','BUILDING':'BLD','MOTOR VEHICLES':'VEH','VEHICLES':'VEH','COMPUTERS':'IT','IT EQUIPMENT':'IT','FURNITURE':'FUR','FURNITURE & FITTINGS':'FUR','SOFTWARE':'SW','INTANGIBLE ASSETS':'INT','OFFICE EQUIPMENT':'OFE'}
        code=code_map.get((major or '').upper(), re.sub(r'[^A-Z]','',(major or 'AST').upper())[:3] or 'AST')
        year=date.today().year
        prefix=f'{code}-{year}-'
        if counters is not None:
            if code not in counters:
                existing=Asset.query.filter(Asset.asset_number.like(prefix+'%')).all()
                counters[code]=max([int(x.asset_number.rsplit('-',1)[1]) for x in existing if x.asset_number.rsplit('-',1)[-1].isdigit()] or [0])
            counters[code]+=1
            return f'{prefix}{counters[code]:04d}'
        existing=Asset.query.filter(Asset.asset_number.like(prefix+'%')).order_by(Asset.asset_number.desc()).first()
        try: n=int(existing.asset_number.rsplit('-',1)[1])+1 if existing else 1
        except Exception: n=1
        return f'{prefix}{n:04d}'

    @bp.route('/')
    @required
    def dashboard():
        active=Asset.query.filter(Asset.archived_at.is_(None),Asset.status=='ACTIVE')
        total_cost=db.session.query(func.coalesce(func.sum(Asset.cost),0)).filter(Asset.archived_at.is_(None),Asset.status.notin_(['DISPOSED','WRITTEN_OFF'])).scalar() or 0
        total_dep=db.session.query(func.coalesce(func.sum(Asset.accumulated_dep),0)).filter(Asset.archived_at.is_(None),Asset.status.notin_(['DISPOSED','WRITTEN_OFF'])).scalar() or 0
        total_nbv=db.session.query(func.coalesce(func.sum(Asset.nbv),0)).filter(Asset.archived_at.is_(None),Asset.status.notin_(['DISPOSED','WRITTEN_OFF'])).scalar() or 0
        intangible=Asset.query.filter(Asset.archived_at.is_(None),Asset.is_intangible.is_(True)).count()
        categories=db.session.query(Asset.major_category,func.sum(Asset.cost)).filter(Asset.archived_at.is_(None),Asset.status.notin_(['DISPOSED','WRITTEN_OFF'])).group_by(Asset.major_category).order_by(func.sum(Asset.cost).desc()).all()
        locations=db.session.query(Asset.location,func.sum(Asset.cost)).filter(Asset.archived_at.is_(None),Asset.status.notin_(['DISPOSED','WRITTEN_OFF'])).group_by(Asset.location).order_by(func.sum(Asset.cost).desc()).limit(8).all()
        latest=Asset.query.filter(Asset.archived_at.is_(None)).order_by(Asset.created_at.desc()).limit(8).all()
        last_run=DepRun.query.order_by(DepRun.created_at.desc()).first()
        open_variances=Recon.query.filter(Recon.status.notin_(['RECONCILED','RESOLVED']),Recon.variance!=0).count()
        return render_template('fixed_assets/dashboard.html', total_cost=total_cost,total_dep=total_dep,total_nbv=total_nbv,
            active_count=active.count(),intangible=intangible,categories=categories,locations=locations,latest=latest,
            last_run=last_run,open_variances=open_variances)

    @bp.route('/register')
    @required
    def register():
        q=(request.args.get('q') or '').strip(); status=request.args.get('status',''); category=request.args.get('category','')
        query=Asset.query.filter(Asset.archived_at.is_(None))
        if q: query=query.filter(or_(Asset.asset_number.ilike(f'%{q}%'),Asset.description.ilike(f'%{q}%'),Asset.tag_number.ilike(f'%{q}%'),Asset.serial_number.ilike(f'%{q}%')))
        if status: query=query.filter_by(status=status)
        if category: query=query.filter_by(major_category=category)
        page=max(1,int(request.args.get('page',1) or 1)); pagination=query.order_by(Asset.asset_number).paginate(page=page,per_page=50,error_out=False)
        return render_template('fixed_assets/register.html',pagination=pagination,q=q,status=status,category=category,categories=category_values())

    @bp.route('/assets/new',methods=['GET','POST'])
    @required
    def new_asset():
        if request.method=='POST':
            f=request.form
            try:
                cost=money(f.get('cost')); residual=money(f.get('residual_value')); opening=money(f.get('opening_accum_dep')); ytd=money(f.get('ytd_depreciation'))
                life=int(f.get('useful_life_months') or 0); placed=parse_date(f.get('placed_in_service'))
                major=f.get('major_category','').strip(); minor=f.get('minor_category','').strip(); desc=f.get('description','').strip()
                if not major or not minor or not desc or not placed or life<=0: raise ValueError('Complete description, category, placed-in-service date and useful life.')
                if cost<=0 or residual<0 or residual>cost or opening<0 or ytd<0 or opening+ytd>cost: raise ValueError('Invalid financial values. Residual value and accumulated depreciation must be within asset cost.')
                method=f.get('depreciation_method','STRAIGHT_LINE')
                if method=='REDUCING_BALANCE' and money(f.get('depreciation_rate'))<=0: raise ValueError('Enter an annual reducing-balance rate greater than zero.')
                if method=='UNITS_OF_PRODUCTION' and money(f.get('total_units_of_production'))<=0: raise ValueError('Enter total expected units for units-of-production depreciation.')
                period=placed.strftime('%Y-%m')
                if period_locked(period): raise ValueError(f'Period {period} is locked.')
                tag=f.get('tag_number','').strip() or None
                if tag and Asset.query.filter_by(tag_number=tag).first(): raise ValueError('Tag number already exists.')
                num=f.get('asset_number','').strip() or asset_number(major)
                if Asset.query.filter_by(asset_number=num).first(): raise ValueError('Asset number already exists.')
                acc=opening+ytd; nbv=cost-acc
                if nbv<0: raise ValueError('Net book value cannot be negative.')
                a=Asset(asset_number=num,description=desc,major_category=major,minor_category=minor,department=f.get('department') or None,
                    location=f.get('location') or None,custodian=f.get('custodian') or None,tag_number=tag,serial_number=f.get('serial_number') or None,
                    supplier=f.get('supplier') or None,invoice_number=f.get('invoice_number') or None,purchase_order_number=f.get('purchase_order_number') or None,
                    purchase_date=parse_date(f.get('purchase_date')),placed_in_service=placed,cost=cost,residual_value=residual,useful_life_months=life,
                    depreciation_method=method,depreciation_rate=money(f.get('depreciation_rate'))/100 if f.get('depreciation_rate') else None,total_units_of_production=money(f.get('total_units_of_production')) if f.get('total_units_of_production') else None,
                    opening_accum_dep=opening,ytd_depreciation=ytd,accumulated_dep=acc,nbv=nbv,status='ACTIVE',
                    is_intangible=f.get('is_intangible')=='on',created_by=actor())
                db.session.add(a); db.session.flush(); audit('CREATE','ASSET',a,None,{'asset_number':num,'cost':str(cost),'nbv':str(nbv)}); db.session.commit()
                flash(f'Asset {num} created successfully.','success'); return redirect(url_for('fixed_assets.register'))
            except Exception as e:
                db.session.rollback(); flash(str(e),'danger')
        return render_template('fixed_assets/asset_form.html')

    @bp.route('/assets/<int:asset_id>')
    @required
    def asset_detail(asset_id):
        a=Asset.query.filter_by(id=asset_id,archived_at=None).first_or_404()
        transfers=Transfer.query.filter_by(asset_id=a.id).order_by(Transfer.transfer_date.desc()).all()
        disposals=Disposal.query.filter_by(asset_id=a.id).all()
        dep_history=db.session.query(DepLine,DepRun).join(DepRun,DepLine.run_id==DepRun.id).filter(DepLine.asset_id==a.id).order_by(DepRun.period.desc()).limit(36).all()
        return render_template('fixed_assets/asset_detail.html',a=a,transfers=transfers,disposals=disposals,dep_history=dep_history)

    # Import mapping and staging
    FIELDS=['asset_number','placed_in_service','description','major_category','minor_category','department','location','tag_number','serial_number','supplier','invoice_number','purchase_order_number','purchase_date','cost','residual_value','useful_life_months','depreciation_method','total_units_of_production','opening_accum_dep','ytd_depreciation','accumulated_dep','nbv','status']
    SYNONYMS={
      'asset_number':['asset number','asset no','asset no.','asset code','asset id'], 'placed_in_service':['date placed in service','placed in service','in service date'],
      'description':['description','asset description','name'], 'major_category':['major category','asset category','category'], 'minor_category':['minor category','sub category','subcategory'],
      'department':['department','dept'], 'location':['location','branch','site'], 'tag_number':['tag number','asset tag','tag no'], 'serial_number':['serial number','serial no','serial'],
      'supplier':['supplier','vendor'], 'invoice_number':['invoice number','invoice no'], 'purchase_order_number':['purchase order number','po number','po no'],
      'purchase_date':['purchase date','acquisition date'], 'cost':['cost','asset cost','gross cost'], 'residual_value':['residual value','salvage value'],
      'useful_life_months':['useful life months','useful life','life months'], 'depreciation_method':['depreciation method','method'], 'total_units_of_production':['total units of production','estimated total units','total production units'],
      'opening_accum_dep':['oad','opening accumulated depreciation','opening acc depreciation'], 'ytd_depreciation':['ytd depreciation','current year depreciation','depreciation charge'],
      'accumulated_dep':['accumulated depreciation','accum depreciation','accum dep'], 'nbv':['net book value','nbv'], 'status':['asset status','status']}
    def normalize_header(x): return re.sub(r'[^a-z0-9 ]','',str(x or '').lower()).strip()
    def read_rows(file):
        filename=secure_filename(file.filename or 'upload')
        raw=file.read(); file.stream.seek(0)
        if filename.lower().endswith('.csv'):
            text=raw.decode('utf-8-sig',errors='replace'); rows=list(csv.reader(StringIO(text)))
        elif filename.lower().endswith(('.xlsx','.xlsm')):
            wb=load_workbook(BytesIO(raw),read_only=True,data_only=True); ws=wb.active; rows=list(ws.iter_rows(values_only=True)); wb.close()
        else: raise ValueError('Upload an .xlsx or .csv file.')
        if not rows or len(rows)<2: raise ValueError('The file must contain a header row and at least one asset row.')
        headers=[str(x or '').strip() for x in rows[0]]
        records=[]
        for n,row in enumerate(rows[1:],start=2):
            if not any(x not in (None,'') for x in row): continue
            records.append({headers[i]: (row[i].isoformat() if isinstance(row[i],(date,datetime)) else row[i]) for i in range(min(len(headers),len(row))) if headers[i]})
        return filename,headers,records
    def auto_mapping(headers):
        out={}
        norm={normalize_header(h):h for h in headers}
        for field,aliases in SYNONYMS.items():
            for alias in aliases:
                if normalize_header(alias) in norm: out[field]=norm[normalize_header(alias)]; break
        return out
    def mapped_record(raw,mapping):
        return {field:raw.get(header) for field,header in mapping.items() if header and header in raw}
    def validate_import(data, seen_assets, seen_tags, seen_serials, existing_assets, existing_tags, existing_serials):
        errors=[]; warnings=[]
        required=['description','major_category','minor_category','placed_in_service','cost']
        for k in required:
            if data.get(k) in (None,''): errors.append(f'Missing {k.replace("_"," ")}')
        if errors: return errors, warnings
        placed=parse_date(data.get('placed_in_service'))
        if not placed: errors.append('Invalid placed-in-service date')
        if not data.get('location'): warnings.append('Missing location')
        if not data.get('department'): warnings.append('Missing department')
        try: cost=money(data.get('cost')); opening=money(data.get('opening_accum_dep')); ytd=money(data.get('ytd_depreciation'))
        except Exception: cost=opening=ytd=Decimal('0'); errors.append('Invalid financial amount')
        acc=money(data.get('accumulated_dep')) if data.get('accumulated_dep') not in (None,'') else opening+ytd
        nbv=money(data.get('nbv')) if data.get('nbv') not in (None,'') else cost-acc
        if cost<=0: errors.append('Cost must be positive')
        if opening<0 or ytd<0 or acc<0 or acc>cost: errors.append('Invalid accumulated depreciation')
        if nbv<0 or nbv != cost-acc: errors.append('NBV must equal Cost less Accumulated Depreciation')
        if money(opening+ytd) != money(acc): errors.append('Opening accumulated depreciation plus YTD depreciation must equal accumulated depreciation')
        try:
            if int(data.get('useful_life_months') or 0)<=0: warnings.append('Missing / invalid useful life; depreciation is suspended until corrected')
        except Exception: warnings.append('Invalid useful life; depreciation is suspended until corrected')
        tag=str(data.get('tag_number') or '').strip()
        if tag and tag in seen_tags: errors.append('Duplicate tag number in import')
        if tag and tag in existing_tags: errors.append('Tag number already exists')
        serial=str(data.get('serial_number') or '').strip()
        if serial and serial in seen_serials: errors.append('Duplicate serial number in import')
        if serial and serial in existing_serials: errors.append('Serial number already exists')
        num=str(data.get('asset_number') or '').strip()
        if num and (num in seen_assets or num in existing_assets): errors.append('Duplicate asset number')
        return errors, warnings

    @bp.route('/import',methods=['GET','POST'])
    @required
    def import_far():
        if request.method=='POST':
            try:
                f=request.files.get('file')
                if not f or not f.filename: raise ValueError('Select an Excel or CSV file.')
                filename,headers,records=read_rows(f)
                if len(records)>100000: raise ValueError('A single import is limited to 100,000 data rows.')
                mapping=auto_mapping(headers); existing_assets={x[0] for x in db.session.query(Asset.asset_number).all()}; existing_tags={x[0] for x in db.session.query(Asset.tag_number).filter(Asset.tag_number.isnot(None)).all()}; existing_serials={x[0] for x in db.session.query(Asset.serial_number).filter(Asset.serial_number.isnot(None)).all()}; batch=ImportBatch(batch_reference='FAR-'+datetime.utcnow().strftime('%Y%m%d%H%M%S')+'-'+secrets.token_hex(2).upper(),file_name=filename,total_rows=len(records),uploaded_by=actor(),column_mapping=mapping)
                db.session.add(batch); db.session.flush(); seen_assets=set(); seen_tags=set(); good=bad=0; seen_serials=set()
                for i,raw in enumerate(records, start=2):
                    mapped=mapped_record(raw,mapping); errors,warnings=validate_import(mapped,seen_assets,seen_tags,seen_serials,existing_assets,existing_tags,existing_serials)
                    if not errors:
                        good+=1
                        if mapped.get('asset_number'): seen_assets.add(str(mapped['asset_number']).strip())
                        if mapped.get('tag_number'): seen_tags.add(str(mapped['tag_number']).strip())
                        if mapped.get('serial_number'): seen_serials.add(str(mapped['serial_number']).strip())
                    else: bad+=1
                    db.session.add(ImportRow(batch_id=batch.id,row_number=i,raw_data=raw,mapped_data=mapped,errors=errors,warnings=warnings))
                batch.successful_rows=good; batch.failed_rows=bad; db.session.commit()
                return redirect(url_for('fixed_assets.import_preview',batch_id=batch.id))
            except Exception as e: db.session.rollback(); flash(str(e),'danger')
        return render_template('fixed_assets/import.html')

    @bp.route('/import/<int:batch_id>')
    @required
    def import_preview(batch_id):
        batch=ImportBatch.query.get_or_404(batch_id); rows=ImportRow.query.filter_by(batch_id=batch.id).order_by(ImportRow.row_number).limit(150).all()
        headers=list((rows[0].raw_data or {}).keys()) if rows else []
        return render_template('fixed_assets/import_preview.html',batch=batch,rows=rows,headers=headers,fields=FIELDS,mapping=batch.column_mapping or {},now_month=date.today().strftime('%Y-%m'))

    @bp.route('/import/<int:batch_id>/mapping',methods=['POST'])
    @required
    def import_mapping(batch_id):
        batch=ImportBatch.query.get_or_404(batch_id)
        if batch.status!='STAGED':
            flash('Only staged imports can be remapped.','warning')
            return redirect(url_for('fixed_assets.import_preview',batch_id=batch.id))
        mapping={field:request.form.get('map_'+field) for field in FIELDS if request.form.get('map_'+field)}
        batch.column_mapping=mapping
        seen_assets=set(); seen_tags=set(); seen_serials=set(); good=bad=0
        existing_assets={x[0] for x in db.session.query(Asset.asset_number).all()}; existing_tags={x[0] for x in db.session.query(Asset.tag_number).filter(Asset.tag_number.isnot(None)).all()}; existing_serials={x[0] for x in db.session.query(Asset.serial_number).filter(Asset.serial_number.isnot(None)).all()}
        for row in ImportRow.query.filter_by(batch_id=batch.id).order_by(ImportRow.row_number).yield_per(1000):
            mapped=mapped_record(row.raw_data or {},mapping)
            errors,warnings=validate_import(mapped,seen_assets,seen_tags,seen_serials,existing_assets,existing_tags,existing_serials)
            row.mapped_data=mapped; row.errors=errors; row.warnings=warnings
            if errors: bad+=1
            else:
                good+=1
                if mapped.get('asset_number'): seen_assets.add(str(mapped['asset_number']).strip())
                if mapped.get('tag_number'): seen_tags.add(str(mapped['tag_number']).strip())
                if mapped.get('serial_number'): seen_serials.add(str(mapped['serial_number']).strip())
        batch.successful_rows=good; batch.failed_rows=bad
        audit('REMAP','FAR_IMPORT',batch,None,{'mapped_fields':list(mapping.keys()),'passed':good,'failed':bad})
        db.session.commit(); flash('Column mapping saved and validation refreshed.','success')
        return redirect(url_for('fixed_assets.import_preview',batch_id=batch.id))

    @bp.route('/import/<int:batch_id>/commit',methods=['POST'])
    @required
    def import_commit(batch_id):
        batch=ImportBatch.query.get_or_404(batch_id)
        if batch.status!='STAGED': flash('This import batch has already been processed.','warning'); return redirect(url_for('fixed_assets.import_preview',batch_id=batch.id))
        period=request.form.get('period') or date.today().strftime('%Y-%m')
        if period_locked(period): flash(f'Period {period} is locked.','danger'); return redirect(url_for('fixed_assets.import_preview',batch_id=batch.id))
        inserted=0; errors=0; number_counters={}
        existing_assets={x[0] for x in db.session.query(Asset.asset_number).all()}; existing_tags={x[0] for x in db.session.query(Asset.tag_number).filter(Asset.tag_number.isnot(None)).all()}; existing_serials={x[0] for x in db.session.query(Asset.serial_number).filter(Asset.serial_number.isnot(None)).all()}
        try:
            rows=ImportRow.query.filter_by(batch_id=batch.id).order_by(ImportRow.row_number).yield_per(1000)
            pending_asset_links=[]
            for row in rows:
                data=row.mapped_data or {}; issues=list(row.errors or [])
                if issues: errors+=1; continue
                # Re-check duplicates at commit time to protect against concurrent uploads.
                num=str(data.get('asset_number') or '').strip() or asset_number(str(data.get('major_category') or 'ASSET'),number_counters)
                tag=str(data.get('tag_number') or '').strip() or None
                serial=str(data.get('serial_number') or '').strip() or None
                if num in existing_assets or (tag and (tag in existing_tags)) or (serial and serial in existing_serials):
                    row.errors=['Duplicate detected at commit']; errors+=1; continue
                cost=money(data.get('cost')); opening=money(data.get('opening_accum_dep')); ytd=money(data.get('ytd_depreciation'))
                acc=money(data.get('accumulated_dep')) if data.get('accumulated_dep') not in (None,'') else opening+ytd
                nbv=money(data.get('nbv')) if data.get('nbv') not in (None,'') else cost-acc
                placed=parse_date(data.get('placed_in_service'))
                if not placed or cost<=0 or acc<0 or acc>cost or nbv<0 or nbv!=cost-acc or money(opening+ytd)!=money(acc):
                    row.errors=['Financial or date validation failed at commit']; errors+=1; continue
                a=Asset(asset_number=num,description=str(data.get('description'))[:255],major_category=str(data.get('major_category'))[:120],minor_category=str(data.get('minor_category'))[:120],
                    department=str(data.get('department') or '')[:120] or None,location=str(data.get('location') or '')[:150] or None,custodian=None,
                    tag_number=tag,serial_number=serial,supplier=str(data.get('supplier') or '')[:180] or None,
                    invoice_number=str(data.get('invoice_number') or '')[:100] or None,purchase_order_number=str(data.get('purchase_order_number') or '')[:100] or None,
                    purchase_date=parse_date(data.get('purchase_date')),placed_in_service=placed,cost=cost,residual_value=money(data.get('residual_value')),
                    useful_life_months=int(data.get('useful_life_months') or 0),depreciation_method=str(data.get('depreciation_method') or 'STRAIGHT_LINE').upper(),total_units_of_production=money(data.get('total_units_of_production')) if data.get('total_units_of_production') not in (None,'') else None,
                    opening_accum_dep=opening,ytd_depreciation=ytd,accumulated_dep=acc,nbv=nbv,status=str(data.get('status') or 'ACTIVE').upper(),
                    is_intangible='INTANG' in str(data.get('major_category') or '').upper() or 'SOFTWARE' in str(data.get('major_category') or '').upper(),
                    source_batch_id=batch.id,created_by=actor())
                db.session.add(a); pending_asset_links.append((row,a)); inserted+=1
                existing_assets.add(num)
                if tag: existing_tags.add(tag)
                if serial: existing_serials.add(serial)
                if inserted % 1000==0:
                    db.session.flush()
                    for import_row, asset_obj in pending_asset_links: import_row.imported_asset_id=asset_obj.id
                    pending_asset_links.clear()
            if pending_asset_links:
                db.session.flush()
                for import_row, asset_obj in pending_asset_links: import_row.imported_asset_id=asset_obj.id
            batch.status='IMPORTED' if errors==0 else ('PARTIAL' if inserted else 'FAILED'); batch.successful_rows=inserted; batch.failed_rows=errors
            audit('IMPORT','FAR_IMPORT',batch,None,{'inserted':inserted,'errors':errors}); db.session.commit()
            flash(f'Import completed: {inserted:,} assets created; {errors:,} rows rejected.','success' if not errors else 'warning')
        except Exception as e: db.session.rollback(); flash(f'Import failed and was rolled back: {e}','danger')
        return redirect(url_for('fixed_assets.import_preview',batch_id=batch.id))

    @bp.route('/depreciation/usage',methods=['POST'])
    @required
    def depreciation_usage():
        f=request.form
        try:
            a=Asset.query.get_or_404(int(f.get('asset_id') or 0)); period=f.get('period',''); datetime.strptime(period,'%Y-%m')
            units=Decimal(str(f.get('units_produced') or '0'))
            if a.depreciation_method!='UNITS_OF_PRODUCTION' or Decimal(str(a.total_units_of_production or 0))<=0 or units<0: raise ValueError('Select a units-of-production asset with total expected units and enter valid period usage.')
            if period_locked(period) or DepRun.query.filter_by(period=period).first(): raise ValueError('The period is locked or depreciation has already been posted.')
            if Usage.query.filter_by(asset_id=a.id,period=period).first(): raise ValueError('Usage has already been captured for this asset and period.')
            row=Usage(asset_id=a.id,period=period,units_produced=units,entered_by=actor()); db.session.add(row); audit('CAPTURE_USAGE','DEPRECIATION',row,None,{'asset_id':a.id,'period':period,'units':str(units)}); db.session.commit(); flash('Production usage recorded.','success')
        except Exception as e: db.session.rollback(); flash(str(e),'danger')
        return redirect(url_for('fixed_assets.depreciation'))

    @bp.route('/depreciation',methods=['GET','POST'])
    @required
    def depreciation():
        if request.method=='POST':
            period=request.form.get('period','').strip()
            try:
                datetime.strptime(period,'%Y-%m')
                if period_locked(period): raise ValueError(f'Period {period} is locked.')
                if DepRun.query.filter_by(period=period).first(): raise ValueError(f'Depreciation has already been processed for {period}. Reverse through an authorized adjustment; do not rerun.')
                year,month=map(int,period.split('-')); cutoff=date(year,month,1)
                assets=Asset.query.filter(Asset.archived_at.is_(None),Asset.status=='ACTIVE',Asset.placed_in_service<cutoff).yield_per(1000)
                run=DepRun(period=period,status='POSTED',created_by=actor()); db.session.add(run); db.session.flush(); total=Decimal('0.00'); count=0
                fy_start=max(1,min(12,int(os.environ.get('FA_FY_START_MONTH','1'))))
                for a in assets:
                    if a.placed_in_service>=date(year,month,1): continue
                    if month==fy_start:
                        a.opening_accum_dep=money(a.accumulated_dep); a.ytd_depreciation=Decimal('0.00')
                    opening=money(a.nbv); depreciable=max(Decimal('0'),money(opening-money(a.residual_value)))
                    if a.useful_life_months<=0 and a.depreciation_method=='STRAIGHT_LINE':
                        continue
                    if a.depreciation_method=='REDUCING_BALANCE':
                        rate=Decimal(str(a.depreciation_rate or 0))
                        charge=(opening*rate/Decimal('12')).quantize(MONEY,rounding=ROUND_HALF_UP)
                    elif a.depreciation_method=='UNITS_OF_PRODUCTION':
                        usage=Usage.query.filter_by(asset_id=a.id,period=period).first()
                        total_units=Decimal(str(a.total_units_of_production or 0))
                        if not usage or total_units<=0: continue
                        charge=(max(Decimal('0'),money(a.cost-money(a.residual_value)))*Decimal(str(usage.units_produced))/total_units).quantize(MONEY,rounding=ROUND_HALF_UP)
                    else:
                        if a.useful_life_months<=0: continue
                        charge=(max(Decimal('0'),money(a.cost-money(a.residual_value)))/Decimal(a.useful_life_months)).quantize(MONEY,rounding=ROUND_HALF_UP)
                    charge=min(max(Decimal('0'),charge),depreciable)
                    if charge<=0: continue
                    closing=money(opening-charge); a.accumulated_dep=money(a.accumulated_dep+charge); a.ytd_depreciation=money(a.ytd_depreciation+charge); a.nbv=closing
                    db.session.add(DepLine(run_id=run.id,asset_id=a.id,opening_nbv=opening,charge=charge,closing_nbv=closing)); total+=charge; count+=1
                run.total_amount=total; run.asset_count=count; audit('POST','DEPRECIATION',run,None,{'period':period,'charge':str(total),'assets':count}); db.session.commit()
                flash(f'Depreciation posted for {period}: {count:,} assets; TZS {total:,.2f}.','success')
            except Exception as e: db.session.rollback(); flash(str(e),'danger')
            return redirect(url_for('fixed_assets.depreciation'))
        runs=DepRun.query.order_by(DepRun.period.desc()).limit(24).all()
        uop_assets=Asset.query.filter(Asset.archived_at.is_(None),Asset.status=='ACTIVE',Asset.depreciation_method=='UNITS_OF_PRODUCTION').order_by(Asset.asset_number).all()
        return render_template('fixed_assets/depreciation.html',runs=runs,uop_assets=uop_assets)

    @bp.route('/trial-balance',methods=['GET','POST'])
    @required
    def trial_balance():
        if request.method=='POST':
            f=request.files.get('file'); period=request.form.get('period','').strip()
            try:
                datetime.strptime(period,'%Y-%m')
                if not f or not f.filename: raise ValueError('Select a TB Excel or CSV file.')
                filename,headers,records=read_rows(f); mapping=auto_mapping(headers)
                # TB has its own field aliases.
                hmap={normalize_header(h):h for h in headers}
                def find_alias(aliases): return next((hmap[normalize_header(x)] for x in aliases if normalize_header(x) in hmap),None)
                acct=find_alias(['account number','account code','gl code','account']); name=find_alias(['account name','description','gl description']); bal=find_alias(['balance','closing balance','net balance'])
                if not acct or not name or not bal: raise ValueError('TB file must contain Account Number, Account Name and Balance columns.')
                batch=TBImport(batch_reference='TB-'+datetime.utcnow().strftime('%Y%m%d%H%M%S')+'-'+secrets.token_hex(2).upper(),period=period,file_name=filename,uploaded_by=actor(),row_count=len(records)); db.session.add(batch); db.session.flush()
                for raw in records:
                    try: amount=Decimal(str(raw.get(bal) or 0).replace(',',''))
                    except Exception: continue
                    db.session.add(TBLine(import_id=batch.id,account_number=str(raw.get(acct) or '').strip(),account_name=str(raw.get(name) or '').strip(),balance=amount))
                audit('IMPORT','TRIAL_BALANCE',batch,None,{'period':period,'rows':len(records)}); db.session.commit(); flash(f'Trial Balance imported for {period}.','success')
            except Exception as e: db.session.rollback(); flash(str(e),'danger')
            return redirect(url_for('fixed_assets.trial_balance'))
        batches=TBImport.query.order_by(TBImport.created_at.desc()).limit(30).all()
        mappings=GLMap.query.order_by(GLMap.major_category,GLMap.balance_type).all()
        return render_template('fixed_assets/trial_balance.html',batches=batches,mappings=mappings,categories=category_values())

    @bp.route('/gl-mapping',methods=['POST'])
    @required
    def gl_mapping():
        f=request.form; major=f.get('major_category','').strip(); typ=f.get('balance_type','COST'); account=f.get('account_number','').strip()
        if not major or not account or typ not in ('COST','ACCUM_DEP'):
            flash('Provide category, account and valid balance type.','danger')
        else:
            row=GLMap.query.filter_by(major_category=major,minor_category=f.get('minor_category') or None,balance_type=typ,account_number=account).first()
            if not row:
                db.session.add(GLMap(major_category=major,minor_category=f.get('minor_category') or None,balance_type=typ,account_number=account,account_name=f.get('account_name') or None))
                audit('CREATE','GL_MAPPING',None,None,{'category':major,'type':typ,'account':account}); db.session.commit(); flash('GL mapping saved.','success')
            else: flash('This GL mapping already exists.','warning')
        return redirect(url_for('fixed_assets.trial_balance'))

    @bp.route('/reconciliation',methods=['GET','POST'])
    @required
    def reconciliation():
        if request.method=='POST':
            period=request.form.get('period','').strip()
            try:
                datetime.strptime(period,'%Y-%m')
                batch=TBImport.query.filter_by(period=period).order_by(TBImport.created_at.desc()).first()
                if not batch: raise ValueError('Import the Trial Balance for this period first.')
                run_reference='REC-'+period.replace('-','')+'-'+secrets.token_hex(3).upper()
                # First reconciliation for a period freezes the FAR balance set used for that period.
                if Snapshot.query.filter_by(period=period).count()==0:
                    for a in Asset.query.filter(Asset.archived_at.is_(None)).yield_per(1000):
                        db.session.add(Snapshot(period=period,asset_id=a.id,asset_number=a.asset_number,major_category=a.major_category,cost=a.cost,accumulated_dep=a.accumulated_dep,nbv=a.nbv,status=a.status))
                    db.session.flush()
                mappings=GLMap.query.filter_by(active=True).all(); grouped={}
                for m in mappings:
                    key=(m.major_category,m.balance_type); grouped.setdefault(key,[]).append(m.account_number)
                for (major,typ),accounts in grouped.items():
                    farq=Asset.query.filter(Asset.archived_at.is_(None),Asset.major_category==major)
                    if typ=='COST': far=money(db.session.query(func.coalesce(func.sum(Snapshot.cost),0)).filter(Snapshot.period==period,Snapshot.major_category==major,Snapshot.status.notin_(['DISPOSED','WRITTEN_OFF'])).scalar())
                    else: far=money(db.session.query(func.coalesce(func.sum(Snapshot.accumulated_dep),0)).filter(Snapshot.period==period,Snapshot.major_category==major,Snapshot.status.notin_(['DISPOSED','WRITTEN_OFF'])).scalar())
                    tb=money(db.session.query(func.coalesce(func.sum(TBLine.balance),0)).filter(TBLine.import_id==batch.id,TBLine.account_number.in_(accounts)).scalar())
                    if typ=='ACCUM_DEP': tb=abs(tb)
                    variance=money(far-tb)
                    db.session.add(Recon(period=period,run_reference=run_reference,major_category=major,balance_type=typ,far_balance=far,tb_balance=tb,variance=variance,status='RECONCILED' if variance==0 else 'OPEN',created_by=actor()))
                for major in sorted(set(k[0] for k in grouped)):
                    cost_accounts=grouped.get((major,'COST'),[]); dep_accounts=grouped.get((major,'ACCUM_DEP'),[])
                    if cost_accounts and dep_accounts:
                        far_cost=money(db.session.query(func.coalesce(func.sum(Snapshot.cost),0)).filter(Snapshot.period==period,Snapshot.major_category==major,Snapshot.status.notin_(['DISPOSED','WRITTEN_OFF'])).scalar())
                        far_dep=money(db.session.query(func.coalesce(func.sum(Snapshot.accumulated_dep),0)).filter(Snapshot.period==period,Snapshot.major_category==major,Snapshot.status.notin_(['DISPOSED','WRITTEN_OFF'])).scalar())
                        tb_cost=money(db.session.query(func.coalesce(func.sum(TBLine.balance),0)).filter(TBLine.import_id==batch.id,TBLine.account_number.in_(cost_accounts)).scalar())
                        tb_dep=abs(money(db.session.query(func.coalesce(func.sum(TBLine.balance),0)).filter(TBLine.import_id==batch.id,TBLine.account_number.in_(dep_accounts)).scalar()))
                        far_nbv=money(far_cost-far_dep); tb_nbv=money(tb_cost-tb_dep); variance=money(far_nbv-tb_nbv)
                        db.session.add(Recon(period=period,run_reference=run_reference,major_category=major,balance_type='NBV',far_balance=far_nbv,tb_balance=tb_nbv,variance=variance,status='RECONCILED' if variance==0 else 'OPEN',created_by=actor()))
                audit('RUN','RECONCILIATION',None,None,{'period':period,'tb_batch':batch.batch_reference,'run_reference':run_reference}); db.session.commit(); flash(f'Reconciliation generated for {period}.','success')
            except Exception as e: db.session.rollback(); flash(str(e),'danger')
            return redirect(url_for('fixed_assets.reconciliation',period=period))
        period=request.args.get('period') or date.today().strftime('%Y-%m')
        latest_run=Recon.query.filter_by(period=period).order_by(Recon.created_at.desc()).first()
        rows=Recon.query.filter_by(period=period,run_reference=latest_run.run_reference).order_by(Recon.major_category,Recon.balance_type).all() if latest_run else []
        return render_template('fixed_assets/reconciliation.html',period=period,rows=rows)

    @bp.route('/reconciliation/<int:recon_id>/investigate',methods=['POST'])
    @required
    def investigate(recon_id):
        row=Recon.query.get_or_404(recon_id); cause=request.form.get('cause','').strip(); desc=request.form.get('description','').strip()
        if not cause or not desc: flash('Select a cause and provide investigation notes.','danger')
        else:
            db.session.add(Investigation(reconciliation_id=row.id,cause=cause,description=desc,resolution=request.form.get('resolution') or None,resolved_by=actor() if request.form.get('resolution') else None,resolved_at=datetime.utcnow() if request.form.get('resolution') else None))
            if request.form.get('resolution'): row.status='RESOLVED'
            audit('INVESTIGATE','RECONCILIATION',row,None,{'cause':cause,'description':desc}); db.session.commit(); flash('Investigation note saved.','success')
        return redirect(url_for('fixed_assets.reconciliation',period=row.period))

    @bp.route('/assets/<int:asset_id>/dispose',methods=['POST'])
    @required
    def dispose(asset_id):
        a=Asset.query.get_or_404(asset_id); f=request.form
        try:
            if a.status!='ACTIVE': raise ValueError('Only active assets can be disposed.')
            d=parse_date(f.get('disposal_date')); proceeds=money(f.get('proceeds')); nbv=money(a.nbv)
            if not d or not f.get('reason'): raise ValueError('Disposal date and reason are required.')
            if period_locked(d.strftime('%Y-%m')): raise ValueError('The disposal period is locked.')
            gain=money(proceeds-nbv)
            row=Disposal(asset_id=a.id,disposal_type=f.get('disposal_type'),disposal_date=d,proceeds=proceeds,nbv_at_disposal=nbv,gain_loss=gain,buyer=f.get('buyer') or None,reason=f.get('reason'),approval_reference=f.get('approval_reference') or None,requested_by=actor(),approved_by=actor())
            old={'status':a.status,'nbv':str(a.nbv)}; a.status='DISPOSED'; a.disposed_at=d; a.disposed_proceeds=proceeds; a.disposal_gain_loss=gain; a.nbv=Decimal('0.00')
            db.session.add(row); audit('DISPOSE','ASSET',a,old,{'status':'DISPOSED','proceeds':str(proceeds),'gain_loss':str(gain)}); db.session.commit()
            flash(f'Asset disposed. Gain/(loss): TZS {gain:,.2f}.','success')
        except Exception as e: db.session.rollback(); flash(str(e),'danger')
        return redirect(url_for('fixed_assets.asset_detail',asset_id=asset_id))

    @bp.route('/assets/<int:asset_id>/transfer',methods=['POST'])
    @required
    def transfer(asset_id):
        a=Asset.query.get_or_404(asset_id); f=request.form
        try:
            d=parse_date(f.get('transfer_date'))
            if not d or not f.get('reason'): raise ValueError('Transfer date and reason are required.')
            if period_locked(d.strftime('%Y-%m')): raise ValueError('The transfer period is locked.')
            old={'location':a.location,'department':a.department,'custodian':a.custodian}
            row=Transfer(asset_id=a.id,from_location=a.location,to_location=f.get('to_location') or a.location,from_department=a.department,to_department=f.get('to_department') or a.department,from_custodian=a.custodian,to_custodian=f.get('to_custodian') or a.custodian,transfer_date=d,reason=f.get('reason'),requested_by=actor(),approved_by=actor())
            a.location=row.to_location; a.department=row.to_department; a.custodian=row.to_custodian; audit('TRANSFER','ASSET',a,old,{'location':a.location,'department':a.department,'custodian':a.custodian}); db.session.add(row); db.session.commit(); flash('Asset transfer recorded.','success')
        except Exception as e: db.session.rollback(); flash(str(e),'danger')
        return redirect(url_for('fixed_assets.asset_detail',asset_id=asset_id))

    @bp.route('/periods',methods=['GET','POST'])
    @required
    def periods():
        if request.method=='POST':
            period=request.form.get('period','').strip(); action=request.form.get('action')
            try:
                datetime.strptime(period,'%Y-%m'); row=PeriodLock.query.filter_by(period=period).first()
                if not row: row=PeriodLock(period=period); db.session.add(row)
                if action=='lock': row.status='LOCKED'; row.locked_by=actor(); row.locked_at=datetime.utcnow(); audit('LOCK','PERIOD',row,None,{'status':'LOCKED'})
                elif action=='reopen':
                    reason=request.form.get('reason','').strip()
                    if not reason: raise ValueError('A reason is required to reopen a period.')
                    row.status='OPEN'; row.reopened_by=actor(); row.reopened_at=datetime.utcnow(); row.reopen_reason=reason; audit('REOPEN','PERIOD',row,{'status':'LOCKED'},{'status':'OPEN','reason':reason})
                db.session.commit(); flash(f'Period {period} updated.','success')
            except Exception as e: db.session.rollback(); flash(str(e),'danger')
            return redirect(url_for('fixed_assets.periods'))
        rows=PeriodLock.query.order_by(PeriodLock.period.desc()).all()
        return render_template('fixed_assets/periods.html',rows=rows)

    @bp.route('/export.xlsx')
    @required
    def export_xlsx():
        wb=Workbook(); ws=wb.active; ws.title='Master FAR'
        headers=['Asset Number','Date Placed in Service','Description','Major Category','Minor Category','Department','Location','Custodian','Tag Number','Serial Number','Cost','Opening Accumulated Depreciation','Current Year Depreciation','Accumulated Depreciation','Net Book Value','Useful Life (Months)','Depreciation Method','Status','Disposal Date','Disposal Proceeds','Gain/(Loss)']
        ws.append(headers)
        assets=Asset.query.filter(Asset.archived_at.is_(None)).order_by(Asset.asset_number).yield_per(2000)
        totals={}
        for a in assets:
            ws.append([safe_text(v) if isinstance(v,str) else v for v in [a.asset_number,a.placed_in_service,a.description,a.major_category,a.minor_category,a.department,a.location,a.custodian,a.tag_number,a.serial_number,float(a.cost),float(a.opening_accum_dep),float(a.ytd_depreciation),float(a.accumulated_dep),float(a.nbv),a.useful_life_months,a.depreciation_method,a.status,a.disposed_at,float(a.disposed_proceeds or 0),float(a.disposal_gain_loss or 0)]])
            g=totals.setdefault(a.major_category,[0,0,0,0]); g[0]+=float(a.cost); g[1]+=float(a.accumulated_dep); g[2]+=float(a.nbv); g[3]+=1
        summary=wb.create_sheet('Category Summary'); summary.append(['Category','Asset Count','Cost','Accumulated Depreciation','NBV'])
        for k,v in sorted(totals.items()): summary.append([k,v[3],v[0],v[1],v[2]])
        branch_totals={}
        for a in Asset.query.filter(Asset.archived_at.is_(None)).yield_per(2000):
            k=a.location or 'Unassigned'; v=branch_totals.setdefault(k,[0,0,0,0]); v[0]+=float(a.cost); v[1]+=float(a.accumulated_dep); v[2]+=float(a.nbv); v[3]+=1
        branch=wb.create_sheet('Branch Summary'); branch.append(['Branch / Location','Asset Count','Cost','Accumulated Depreciation','NBV'])
        for k,v in sorted(branch_totals.items()): branch.append([k,v[3],v[0],v[1],v[2]])
        company=wb.create_sheet('Company Summary'); company.append(['Metric','Value']); company.append(['Asset Count',sum(v[3] for v in totals.values())]); company.append(['Total Cost',sum(v[0] for v in totals.values())]); company.append(['Accumulated Depreciation',sum(v[1] for v in totals.values())]); company.append(['Net Book Value',sum(v[2] for v in totals.values())])
        for sh in wb.worksheets:
            sh.freeze_panes='A2'; sh.auto_filter.ref=sh.dimensions
            for cell in sh[1]: cell.font=cell.font.copy(bold=True)
        out=BytesIO(); wb.save(out); out.seek(0)
        audit('EXPORT','MASTER_FAR',None,None,{'format':'xlsx','assets':sum(x[3] for x in totals.values())}); db.session.commit()
        return send_file(out,mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',as_attachment=True,download_name=f'Master_FAR_{date.today().isoformat()}.xlsx')


    @bp.route('/cwip',methods=['GET','POST'])
    @required
    def cwip():
        if request.method=='POST':
            f=request.form
            try:
                name=f.get('name','').strip(); code=f.get('project_code','').strip(); start=parse_date(f.get('start_date'))
                if not name or not code or not start: raise ValueError('Project code, name and start date are required.')
                row=Cwip.query.filter_by(project_code=code).first()
                if row: raise ValueError('Project code already exists.')
                row=Cwip(project_code=code,name=name,description=f.get('description'),department=f.get('department'),start_date=start,expected_completion=parse_date(f.get('expected_completion')),created_by=actor())
                db.session.add(row); audit('CREATE','CWIP',row,None,{'project_code':code,'name':name}); db.session.commit(); flash('CWIP project created.','success')
            except Exception as e: db.session.rollback(); flash(str(e),'danger')
            return redirect(url_for('fixed_assets.cwip'))
        projects=Cwip.query.order_by(Cwip.created_at.desc()).all()
        return render_template('fixed_assets/cwip.html',projects=projects)

    @bp.route('/cwip/<int:project_id>/expenditure',methods=['POST'])
    @required
    def cwip_expenditure(project_id):
        project=Cwip.query.get_or_404(project_id); f=request.form
        try:
            d=parse_date(f.get('expenditure_date')); amount=money(f.get('amount'))
            if project.status!='IN_PROGRESS' or not d or amount<=0 or not f.get('description'): raise ValueError('Provide valid expenditure details for an active project.')
            if period_locked(d.strftime('%Y-%m')): raise ValueError('The expenditure period is locked.')
            row=CwipExp(project_id=project.id,expenditure_date=d,amount=amount,description=f.get('description'),reference=f.get('reference'),created_by=actor())
            project.total_cost=money(project.total_cost+amount); db.session.add(row); audit('ADD_EXPENDITURE','CWIP',project,None,{'amount':str(amount),'reference':row.reference}); db.session.commit(); flash('CWIP expenditure recorded.','success')
        except Exception as e: db.session.rollback(); flash(str(e),'danger')
        return redirect(url_for('fixed_assets.cwip'))

    @bp.route('/cwip/<int:project_id>/capitalize',methods=['POST'])
    @required
    def cwip_capitalize(project_id):
        project=Cwip.query.get_or_404(project_id); f=request.form
        try:
            d=parse_date(f.get('placed_in_service')); life=int(f.get('useful_life_months') or 0)
            if project.status!='IN_PROGRESS' or money(project.total_cost)<=0 or not d or life<=0: raise ValueError('Project must have expenditure, placed-in-service date and useful life before capitalization.')
            if period_locked(d.strftime('%Y-%m')): raise ValueError('Capitalization period is locked.')
            major=f.get('major_category','').strip(); minor=f.get('minor_category','').strip()
            if not major or not minor: raise ValueError('Select the capitalization category.')
            num=asset_number(major); cost=money(project.total_cost)
            a=Asset(asset_number=num,description=project.name,major_category=major,minor_category=minor,department=project.department,location=f.get('location'),placed_in_service=d,cost=cost,residual_value=0,useful_life_months=life,depreciation_method=f.get('depreciation_method','STRAIGHT_LINE'),opening_accum_dep=0,ytd_depreciation=0,accumulated_dep=0,nbv=cost,status='ACTIVE',created_by=actor())
            db.session.add(a); db.session.flush(); project.status='CAPITALIZED'; project.capitalized_asset_id=a.id; audit('CAPITALIZE','CWIP',project,None,{'asset_number':num,'cost':str(cost)}); db.session.commit(); flash(f'CWIP capitalized into asset {num}. Depreciation will start in the following month under the current convention.','success')
        except Exception as e: db.session.rollback(); flash(str(e),'danger')
        return redirect(url_for('fixed_assets.cwip'))

    @bp.route('/verification',methods=['GET','POST'])
    @required
    def verification():
        if request.method=='POST':
            f=request.form; a=Asset.query.get_or_404(int(f.get('asset_id') or 0)); outcome=f.get('outcome')
            if outcome not in ('FOUND','MISSING','DAMAGED','DISPOSED'):
                flash('Select a valid verification result.','danger')
            else:
                row=Verify(asset_id=a.id,outcome=outcome,verified_by=actor(),notes=f.get('notes'))
                if outcome=='MISSING': a.status='MISSING'
                elif outcome=='FOUND' and a.status=='MISSING': a.status='ACTIVE'
                audit('VERIFY','ASSET',a,None,{'outcome':outcome,'notes':f.get('notes')}); db.session.add(row); db.session.commit(); flash('Physical verification result recorded.','success')
            return redirect(url_for('fixed_assets.verification'))
        assets=Asset.query.filter(Asset.archived_at.is_(None)).order_by(Asset.asset_number).limit(500).all()
        rows=Verify.query.order_by(Verify.verified_at.desc()).limit(200).all()
        return render_template('fixed_assets/verification.html',assets=assets,rows=rows)

    @bp.route('/assets/<int:asset_id>/qr.png')
    @required
    def asset_qr(asset_id):
        import qrcode
        a=Asset.query.get_or_404(asset_id)
        payload=f"{request.url_root.rstrip('/')}/fixed-assets/assets/{a.id}"
        img=qrcode.make(payload); out=BytesIO(); img.save(out,format='PNG'); out.seek(0)
        return send_file(out,mimetype='image/png',download_name=f'{a.asset_number}_QR.png')

    @bp.route('/insurance',methods=['GET','POST'])
    @required
    def insurance():
        if request.method=='POST':
            f=request.form
            try:
                a=Asset.query.get_or_404(int(f.get('asset_id') or 0)); renewal=parse_date(f.get('renewal_date')); expiry=parse_date(f.get('expiry_date'))
                insured=money(f.get('insured_amount')); coverage=money(f.get('coverage_amount'))
                if not f.get('policy_number') or not f.get('insurer') or insured<=0 or coverage<0: raise ValueError('Provide policy, insurer and valid insured / coverage amounts.')
                row=Insurance(asset_id=a.id,policy_number=f.get('policy_number'),insurer=f.get('insurer'),insured_amount=insured,coverage_amount=coverage,renewal_date=renewal,expiry_date=expiry)
                db.session.add(row); audit('CREATE','INSURANCE',row,None,{'asset_id':a.id,'policy_number':row.policy_number}); db.session.commit(); flash('Insurance policy recorded.','success')
            except Exception as e: db.session.rollback(); flash(str(e),'danger')
            return redirect(url_for('fixed_assets.insurance'))
        rows=Insurance.query.order_by(Insurance.expiry_date.asc()).all(); assets=Asset.query.filter(Asset.archived_at.is_(None),Asset.status=='ACTIVE').order_by(Asset.asset_number).limit(1000).all()
        claims=InsuranceClaim.query.order_by(InsuranceClaim.claim_date.desc()).limit(200).all()
        return render_template('fixed_assets/insurance.html',rows=rows,assets=assets,today=date.today(),claims=claims)

    @bp.route('/insurance/claims',methods=['POST'])
    @required
    def insurance_claim():
        f=request.form; policy=Insurance.query.get_or_404(int(f.get('policy_id') or 0))
        try:
            d=parse_date(f.get('claim_date')); amount=money(f.get('claim_amount'))
            if not f.get('claim_reference') or not d or amount<=0: raise ValueError('Provide claim reference, date and a positive claim amount.')
            row=InsuranceClaim(policy_id=policy.id,claim_reference=f.get('claim_reference'),claim_date=d,claim_amount=amount,status=f.get('status','OPEN'),notes=f.get('notes'))
            db.session.add(row); audit('CREATE','INSURANCE_CLAIM',row,None,{'policy_id':policy.id,'claim_reference':row.claim_reference,'amount':str(amount)}); db.session.commit(); flash('Insurance claim recorded.','success')
        except Exception as e: db.session.rollback(); flash(str(e),'danger')
        return redirect(url_for('fixed_assets.insurance'))

    @bp.route('/tax-schedules',methods=['GET','POST'])
    @required
    def tax_schedules():
        if request.method=='POST':
            f=request.form
            try:
                a=Asset.query.get_or_404(int(f.get('asset_id') or 0)); period=f.get('period',''); datetime.strptime(period,'%Y-%m')
                if period_locked(period): raise ValueError('Tax schedule period is locked.')
                tax_wdv=money(f.get('tax_wdv')); rate=Decimal(str(f.get('tax_rate') or '0'))/Decimal('100')
                if tax_wdv<0 or rate<0 or rate>1: raise ValueError('Enter valid tax WDV and tax rate.')
                diff=money(money(a.nbv)-tax_wdv); deferred=money(diff*rate)
                old=Tax.query.filter_by(asset_id=a.id,period=period).first()
                if old: raise ValueError('A tax schedule already exists for this asset and period.')
                row=Tax(asset_id=a.id,period=period,tax_wdv=tax_wdv,accounting_nbv=money(a.nbv),temporary_difference=diff,tax_rate=rate,deferred_tax=deferred)
                db.session.add(row); audit('CREATE','TAX_SCHEDULE',row,None,{'asset_id':a.id,'period':period,'tax_wdv':str(tax_wdv),'deferred_tax':str(deferred)}); db.session.commit(); flash('Tax and deferred tax schedule saved. Positive deferred tax is a liability; negative is an asset, subject to IAS 12 recognition criteria.','success')
            except Exception as e: db.session.rollback(); flash(str(e),'danger')
            return redirect(url_for('fixed_assets.tax_schedules'))
        rows=Tax.query.order_by(Tax.period.desc()).limit(500).all(); assets=Asset.query.filter(Asset.archived_at.is_(None)).order_by(Asset.asset_number).limit(1000).all()
        return render_template('fixed_assets/tax.html',rows=rows,assets=assets)

    @bp.route('/export.csv')
    @required
    def export_csv():
        out=StringIO(); writer=csv.writer(out)
        writer.writerow(['Asset Number','Date Placed in Service','Description','Major Category','Minor Category','Department','Location','Custodian','Tag Number','Cost','Opening Accumulated Depreciation','Current Year Depreciation','Accumulated Depreciation','Net Book Value','Useful Life (Months)','Depreciation Method','Status','Disposal Date','Disposal Proceeds','Gain/Loss'])
        for a in Asset.query.filter(Asset.archived_at.is_(None)).order_by(Asset.asset_number).yield_per(2000):
            writer.writerow([safe_text(v) if isinstance(v,str) else v for v in [a.asset_number,a.placed_in_service,a.description,a.major_category,a.minor_category,a.department,a.location,a.custodian,a.tag_number,float(a.cost),float(a.opening_accum_dep),float(a.ytd_depreciation),float(a.accumulated_dep),float(a.nbv),a.useful_life_months,a.depreciation_method,a.status,a.disposed_at,float(a.disposed_proceeds or 0),float(a.disposal_gain_loss or 0)]])
        audit('EXPORT','MASTER_FAR',None,None,{'format':'csv'}); db.session.commit()
        return send_file(BytesIO(('\ufeff'+out.getvalue()).encode('utf-8')),mimetype='text/csv',as_attachment=True,download_name=f'Master_FAR_{date.today().isoformat()}.csv')

    @bp.route('/export.pdf')
    @required
    def export_pdf():
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        out=BytesIO(); doc=SimpleDocTemplate(out,pagesize=landscape(A4),rightMargin=22,leftMargin=22,topMargin=24,bottomMargin=24)
        styles=getSampleStyleSheet(); story=[Paragraph('Fixed Asset Register',styles['Title']),Paragraph(f'Generated {datetime.utcnow():%d %B %Y %H:%M} UTC · Currency: TZS',styles['Normal']),Spacer(1,10)]
        data=[['Asset Number','Description','Category','Location','Cost','Accum. Dep.','NBV','Status']]
        for a in Asset.query.filter(Asset.archived_at.is_(None)).order_by(Asset.asset_number).yield_per(1000):
            data.append([a.asset_number,Paragraph(xml_escape((a.description or '')[:70]),styles['BodyText']),Paragraph(xml_escape((a.major_category or '')[:35]),styles['BodyText']),Paragraph(xml_escape((a.location or '')[:25]),styles['BodyText']),f'{float(a.cost):,.2f}',f'{float(a.accumulated_dep):,.2f}',f'{float(a.nbv):,.2f}',a.status])
        table=Table(data,repeatRows=1,colWidths=[72,150,90,75,75,75,75,65])
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#17365D')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),7),('GRID',(0,0),(-1,-1),0.25,colors.HexColor('#D9E2F3')),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F4F7FB')])]))
        story.append(table); doc.build(story); out.seek(0)
        audit('EXPORT','MASTER_FAR',None,None,{'format':'pdf'}); db.session.commit()
        return send_file(out,mimetype='application/pdf',as_attachment=True,download_name=f'Master_FAR_{date.today().isoformat()}.pdf')

    @bp.route('/audit-pack.xlsx')
    @required
    def audit_pack():
        from openpyxl.styles import Font, PatternFill
        wb=Workbook(); wb.remove(wb.active)
        def sheet(name,headers,rows):
            ws=wb.create_sheet(name); ws.append(headers)
            for row in rows: ws.append([safe_text(v) if isinstance(v,str) else v for v in row])
            ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
            for cell in ws[1]: cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='17365D')
            return ws
        assets=Asset.query.filter(Asset.archived_at.is_(None)).order_by(Asset.asset_number).all()
        sheet('Master FAR',['Asset Number','Placed in Service','Description','Major Category','Minor Category','Department','Location','Custodian','Tag Number','Cost','OAD','YTD Depreciation','Accumulated Depreciation','NBV','Useful Life Months','Method','Status','Disposal Date','Proceeds','Gain Loss'],[[a.asset_number,a.placed_in_service,a.description,a.major_category,a.minor_category,a.department,a.location,a.custodian,a.tag_number,float(a.cost),float(a.opening_accum_dep),float(a.ytd_depreciation),float(a.accumulated_dep),float(a.nbv),a.useful_life_months,a.depreciation_method,a.status,a.disposed_at,float(a.disposed_proceeds or 0),float(a.disposal_gain_loss or 0)] for a in assets])
        sheet('Asset Additions',['Asset Number','Date','Description','Category','Cost','Batch'],[[a.asset_number,a.created_at,a.description,a.major_category,float(a.cost),a.source_batch_id] for a in assets])
        disposals=Disposal.query.order_by(Disposal.disposal_date).all(); sheet('Asset Disposals',['Asset Number','Date','Type','Proceeds','NBV','Gain Loss','Buyer','Reason','Approval Ref'],[[Asset.query.get(d.asset_id).asset_number if Asset.query.get(d.asset_id) else '',d.disposal_date,d.disposal_type,float(d.proceeds),float(d.nbv_at_disposal),float(d.gain_loss),d.buyer,d.reason,d.approval_reference] for d in disposals])
        transfers=Transfer.query.order_by(Transfer.transfer_date).all(); sheet('Asset Transfers',['Asset ID','Date','From Location','To Location','From Department','To Department','From Custodian','To Custodian','Reason'],[[t.asset_id,t.transfer_date,t.from_location,t.to_location,t.from_department,t.to_department,t.from_custodian,t.to_custodian,t.reason] for t in transfers])
        runs=DepRun.query.order_by(DepRun.period).all(); sheet('Depreciation Schedule',['Period','Asset ID','Opening NBV','Charge','Closing NBV'],[[r.period,l.asset_id,float(l.opening_nbv),float(l.charge),float(l.closing_nbv)] for r in runs for l in DepLine.query.filter_by(run_id=r.id).all()])
        sheet('Intangible Register',['Asset Number','Description','Category','Cost','Accum Dep','NBV','Useful Life'],[[a.asset_number,a.description,a.major_category,float(a.cost),float(a.accumulated_dep),float(a.nbv),a.useful_life_months] for a in assets if a.is_intangible])
        projects=Cwip.query.all(); sheet('CWIP Register',['Project Code','Project','Department','Start Date','Expected Completion','Status','Total Cost','Capitalized Asset ID'],[[p.project_code,p.name,p.department,p.start_date,p.expected_completion,p.status,float(p.total_cost),p.capitalized_asset_id] for p in projects])
        verifies=Verify.query.order_by(Verify.verified_at).all(); sheet('Physical Verification',['Asset ID','Outcome','Verified By','Verified At','Notes'],[[v.asset_id,v.outcome,v.verified_by,v.verified_at,v.notes] for v in verifies])
        policies=Insurance.query.all(); claims=InsuranceClaim.query.all(); sheet('Insurance Register',['Asset ID','Policy','Insurer','Insured Amount','Coverage Amount','Renewal','Expiry','Claim Reference','Claim Date','Claim Amount','Claim Status'],[[i.asset_id,i.policy_number,i.insurer,float(i.insured_amount),float(i.coverage_amount),i.renewal_date,i.expiry_date,None,None,None,None] for i in policies]+[[None,None,None,None,None,None,None,c.claim_reference,c.claim_date,float(c.claim_amount),c.status] for c in claims])
        recons=Recon.query.order_by(Recon.period,Recon.major_category).all(); sheet('FAR TB Reconciliation',['Period','Category','Type','FAR','TB','Variance','Status'],[[r.period,r.major_category,r.balance_type,float(r.far_balance),float(r.tb_balance),float(r.variance),r.status] for r in recons])
        taxes=Tax.query.order_by(Tax.period).all(); sheet('Deferred Tax Schedule',['Asset ID','Period','Tax WDV','Accounting NBV','Temporary Difference','Tax Rate','Deferred Tax'],[[t.asset_id,t.period,float(t.tax_wdv),float(t.accounting_nbv),float(t.temporary_difference),float(t.tax_rate),float(t.deferred_tax)] for t in taxes])
        exceptions=[]
        for a in assets:
            issues=[]
            if not a.major_category or not a.minor_category: issues.append('Missing category')
            if not a.location: issues.append('Missing location')
            if not a.department: issues.append('Missing department')
            if a.useful_life_months<=0: issues.append('Invalid useful life')
            if a.status not in ('DISPOSED','WRITTEN_OFF') and money(a.cost-money(a.accumulated_dep))!=money(a.nbv): issues.append('NBV does not equal cost less accumulated depreciation')
            if a.nbv<0: issues.append('Negative NBV')
            if issues: exceptions.append([a.asset_number,a.description,'; '.join(issues)])
        sheet('Exception Report',['Asset Number','Description','Exceptions'],exceptions)
        out=BytesIO(); wb.save(out); out.seek(0); audit('EXPORT','AUDIT_PACK',None,None,{'assets':len(assets),'sheets':len(wb.sheetnames)}); db.session.commit()
        return send_file(out,mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',as_attachment=True,download_name=f'Fixed_Asset_Audit_Pack_{date.today().isoformat()}.xlsx')

    @bp.route('/audit-log')
    @required
    def audit_log():
        rows=Audit.query.order_by(Audit.created_at.desc()).limit(500).all()
        return render_template('fixed_assets/audit_log.html',rows=rows)

    return bp
