// Copyright (c) 2025, Government Agency and contributors
// For license information, please see license.txt

frappe.ui.form.on('Digital Signature', {
    refresh: function(frm) {
        if (frm.doc.verification_status === 'Pending') {
            frm.add_custom_button(__('Verify Signature'), function() {
                frappe.call({
                    method: 'pwp_project.pwp_project.doctype.digital_signature.digital_signature.verify_signature',
                    args: {
                        docname: frm.doc.name
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert(__('Signature verification completed'));
                            frm.reload_doc();
                        }
                    }
                });
            });
        }

        if (frm.doc.verification_status === 'Verified') {
            frm.add_custom_button(__('Revoke Signature'), function() {
                frappe.prompt([
                    {
                        fieldname: 'reason',
                        label: __('Revocation Reason'),
                        fieldtype: 'Text',
                        reqd: 1
                    }
                ], function(values) {
                    frappe.call({
                        method: 'pwp_project.pwp_project.doctype.digital_signature.digital_signature.revoke_signature',
                        args: {
                            docname: frm.doc.name,
                            reason: values.reason
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert(__('Signature revoked'));
                                frm.reload_doc();
                            }
                        }
                    });
                }, __('Revoke Signature'), __('Revoke'));
            });
        }

        frm.add_custom_button(__('View Document'), function() {
            frappe.set_route('Form', 'Document', frm.doc.document);
        });

        frm.add_custom_button(__('View Document Version'), function() {
            frappe.set_route('Form', 'Document Version', frm.doc.document_version);
        });

        // Show verification status with color coding
        if (frm.doc.verification_status === 'Verified') {
            frm.dashboard.add_indicator(__('Verified'), 'green');
        } else if (frm.doc.verification_status === 'Failed') {
            frm.dashboard.add_indicator(__('Verification Failed'), 'red');
        } else {
            frm.dashboard.add_indicator(__('Pending Verification'), 'orange');
        }

        // Add signature capture button for internal signatures
        if (frm.doc.signature_provider === 'Internal' && !frm.doc.signature_data) {
            frm.add_custom_button(__('Capture Signature'), function() {
                show_signature_pad(frm);
            });
        }

        // Display signature if available
        if (frm.doc.signature_data) {
            display_signature(frm);
        }
    },

    document: function(frm) {
        if (frm.doc.document) {
            // Get current document version
            frappe.call({
                method: 'pwp_project.pwp_project.doctype.document.document.get_latest_version',
                args: {
                    docname: frm.doc.document
                },
                callback: function(r) {
                    if (!r.exc && r.message) {
                        frm.set_value('document_version', r.message.name);
                    }
                }
            });
        }
    },

    signature_provider: function(frm) {
        if (frm.doc.signature_provider === 'Internal') {
            frm.set_df_property('signature_data', 'hidden', 1);
        } else {
            frm.set_df_property('signature_data', 'hidden', 0);
        }
    }
});

function show_signature_pad(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Capture Signature'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'signature_pad'
            }
        ],
        primary_action_label: __('Save Signature'),
        primary_action: function() {
            let signature_data = signaturePad.toDataURL();
            frm.set_value('signature_data', signature_data);
            dialog.hide();
            frm.save();
        }
    });

    dialog.show();

    // Initialize signature pad
    let canvas = dialog.get_field('signature_pad').$wrapper.find('canvas')[0];
    canvas.width = dialog.get_field('signature_pad').$wrapper.width();
    canvas.height = 200;

    let signaturePad = new SignaturePad(canvas, {
        backgroundColor: 'rgb(255, 255, 255)',
        penColor: 'rgb(0, 0, 0)'
    });

    // Add clear button
    let clear_button = $('<button class="btn btn-default btn-sm">Clear</button>').click(function() {
        signaturePad.clear();
    });

    dialog.get_field('signature_pad').$wrapper.append(clear_button);
}

function display_signature(frm) {
    if (frm.doc.signature_provider === 'Internal') {
        // Display image signature
        let signature_html = `
            <div class="signature-display">
                <img src="${frm.doc.signature_data}" style="max-width: 100%; height: auto; border: 1px solid #d1d8dd; padding: 10px;">
            </div>
        `;

        frm.fields_dict.signature_data.$wrapper.html(signature_html);
    } else {
        // Display text representation of signature data
        let signature_html = `
            <div class="signature-display">
                <div class="alert alert-info">
                    <strong>${__('Signature Provider')}:</strong> ${frm.doc.signature_provider}<br>
                    <strong>${__('Certificate Info')}:</strong> ${frm.doc.certificate_info || __('Not available')}
                </div>
                <div class="signature-data">
                    <pre>${frm.doc.signature_data.substring(0, 200)}${frm.doc.signature_data.length > 200 ? '...' : ''}</pre>
                </div>
            </div>
        `;

        frm.fields_dict.signature_data.$wrapper.html(signature_html);
    }
}
