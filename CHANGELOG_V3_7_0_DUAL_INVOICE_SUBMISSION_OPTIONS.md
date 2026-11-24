# CETTP V3.7.0 – Dual Invoice Submission Options

## Summary
Adds a choice at the start of a new EFD request so Initiators can either create a Digital Tax Invoice in CETTP or upload an already-prepared manual Word invoice.

## Changes
- New EFD Request landing page presents two clear options: Digital Invoice and Upload Manual Invoice.
- Digital Invoice opens the existing digital invoice form, preserving VAT selection (0% or 18%), automatic calculations, Word preview and confirmation workflow.
- Manual Invoice provides a separate upload form for an existing `.doc` or `.docx` invoice, plus customer/insured name and purpose.
- Manual uploads are limited to 15 MB and validated server-side by extension and size.
- Manual requests enter the existing Tax Compliance workplace as Pending requests, retain the existing document review, return, reject and processed-document workflow, and create an EFD request audit entry.
- Manual submission uses the existing centralized email notification service and the current Tax Compliance notification recipient.
- No database schema change is required; both request types use the existing EFDInvoiceRequest model. Digital requests continue to use DigitalTaxInvoice for their structured invoice data.
- Initiator dashboard helper text updated to explain both submission methods.

## Compatibility and safeguards
- Existing request records and PostgreSQL data are not reset or deleted.
- Existing Tax Compliance processing, EFD portal handoff, processed Word upload and download routes are unchanged.
- Existing `/efd-requests/new` URL now opens the option-selection page. The digital form is available at `/efd-requests/digital/new`.
