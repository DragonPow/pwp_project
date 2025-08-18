// Copyright (c) 2025, Government Agency and contributors
// For license information, please see license.txt

frappe.ui.form.on('Document Version', {
    refresh: function(frm) {
        // Add Set as Current button if not current
        if (!frm.doc.is_current) {
            frm.add_custom_button(__('Set as Current'), function() {
                frappe.confirm(
                    __('Are you sure you want to set this version as current? This will update the document status.'),
                    function() {
                        frappe.call({
                            method: 'electronic_office.electronic_office.doctype.document_version.document_version.set_as_current',
                            args: {
                                docname: frm.doc.name
                            },
                            callback: function(r) {
                                if (!r.exc) {
                                    frappe.show_alert(__('Version set as current successfully'));
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }).addClass('btn-primary');
        }
        
        // Add View Document button
        frm.add_custom_button(__('View Document'), function() {
            frappe.set_route('Form', 'Document', frm.doc.document);
        });
        
        // Add Restore to Document button if not current
        if (!frm.doc.is_current && frm.doc.content_snapshot) {
            frm.add_custom_button(__('Restore to Document'), function() {
                frappe.confirm(
                    __('Are you sure you want to restore this version to the document? This will replace the current document content.'),
                    function() {
                        frappe.call({
                            method: 'electronic_office.electronic_office.doctype.document_version.document_version.restore_to_document',
                            args: {
                                docname: frm.doc.name
                            },
                            callback: function(r) {
                                if (!r.exc) {
                                    frappe.show_alert(__('Version restored to document successfully'));
                                    frappe.set_route('Form', 'Document', r.message);
                                }
                            }
                        });
                    }
                );
            });
        }
        
        // Add Compare with Previous button
        frm.add_custom_button(__('Compare with Previous'), function() {
            frappe.call({
                method: 'electronic_office.electronic_office.doctype.document_version.document_version.get_previous_version',
                args: {
                    docname: frm.doc.name
                },
                callback: function(r) {
                    if (!r.exc && r.message) {
                        show_version_comparison(frm.doc, r.message);
                    } else {
                        frappe.show_alert(__('No previous version found'));
                    }
                }
            });
        });
        
        // Add Compare with Specific Version button
        frm.add_custom_button(__('Compare with Version'), function() {
            show_version_compare_dialog(frm);
        });
        
        // Add View Content Snapshot button if available
        if (frm.doc.content_snapshot) {
            frm.add_custom_button(__('View Content Snapshot'), function() {
                show_content_snapshot_dialog(frm);
            });
        }
    },
    
    onload: function(frm) {
        // Set read-only fields
        frm.set_df_property('version_number', 'read_only', 1);
        frm.set_df_property('created_by', 'read_only', 1);
        frm.set_df_property('created_on', 'read_only', 1);
        frm.set_df_property('file_hash', 'read_only', 1);
        frm.set_df_property('is_current', 'read_only', 1);
    },
    
    document: function(frm) {
        if (frm.doc.document) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Document',
                    name: frm.doc.document
                },
                callback: function(r) {
                    if (!r.exc && r.message) {
                        frm.set_value('file_hash', r.message.file_hash || '');
                        if (!frm.doc.status) {
                            frm.set_value('status', r.message.status || 'Draft');
                        }
                    }
                }
            });
        }
    }
});

function show_version_comparison(current_version, previous_version) {
    let dialog = new frappe.ui.Dialog({
        title: __('Version Comparison'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'comparison_html'
            }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            dialog.hide();
        }
    });
    
    let html = `
        <div class="row">
            <div class="col-sm-6">
                <h4>${__('Previous Version')} (${previous_version.version_number})</h4>
                <p><strong>${__('Description')}:</strong> ${previous_version.version_description || ''}</p>
                <p><strong>${__('Created By')}:</strong> ${previous_version.created_by}</p>
                <p><strong>${__('Created On')}:</strong> ${frappe.datetime.str_to_user(previous_version.created_on)}</p>
                <p><strong>${__('Status')}:</strong> ${previous_version.status || ''}</p>
            </div>
            <div class="col-sm-6">
                <h4>${__('Current Version')} (${current_version.version_number})</h4>
                <p><strong>${__('Description')}:</strong> ${current_version.version_description || ''}</p>
                <p><strong>${__('Created By')}:</strong> ${current_version.created_by}</p>
                <p><strong>${__('Created On')}:</strong> ${frappe.datetime.str_to_user(current_version.created_on)}</p>
                <p><strong>${__('Status')}:</strong> ${current_version.status || ''}</p>
            </div>
        </div>
    `;
    
    dialog.set_values({
        'comparison_html': html
    });
    
    dialog.show();
}

function show_version_compare_dialog(frm) {
    // Get all versions for this document
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Document Version',
            filters: {
                document: frm.doc.document,
                name: ['!=', frm.doc.name]
            },
            fields: ['name', 'version_number', 'version_description', 'created_by', 'created_on'],
            order_by: 'version_number desc'
        },
        callback: function(r) {
            if (!r.exc && r.message) {
                let dialog = new frappe.ui.Dialog({
                    title: __('Compare with Version'),
                    fields: [
                        {
                            fieldname: 'compare_version',
                            label: __('Select Version'),
                            fieldtype: 'Select',
                            options: r.message.map(v => `${v.version_number}: ${v.version_description || 'No description'}`).join('\n'),
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Compare'),
                    primary_action: function() {
                        let values = dialog.get_values();
                        let selected_version = r.message[values.compare_version];
                        
                        frappe.call({
                            method: 'electronic_office.electronic_office.doctype.document_version.document_version.compare_with_version',
                            args: {
                                docname: frm.doc.name,
                                other_version_name: selected_version.name
                            },
                            callback: function(r) {
                                if (!r.exc && r.message) {
                                    show_detailed_version_comparison(r.message);
                                }
                            }
                        });
                        
                        dialog.hide();
                    }
                });
                
                dialog.show();
            } else {
                frappe.show_alert(__('No other versions found for comparison'));
            }
        }
    });
}

function show_detailed_version_comparison(comparison_data) {
    let dialog = new frappe.ui.Dialog({
        title: __('Detailed Version Comparison'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'comparison_html'
            }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            dialog.hide();
        }
    });
    
    let html = `
        <div class="row">
            <div class="col-sm-6">
                <h4>${__('Version')} ${comparison_data.version1.version_number}</h4>
                <p><strong>${__('Description')}:</strong> ${comparison_data.version1.version_description || ''}</p>
                <p><strong>${__('Created By')}:</strong> ${comparison_data.version1.created_by}</p>
                <p><strong>${__('Created On')}:</strong> ${frappe.datetime.str_to_user(comparison_data.version1.created_on)}</p>
            </div>
            <div class="col-sm-6">
                <h4>${__('Version')} ${comparison_data.version2.version_number}</h4>
                <p><strong>${__('Description')}:</strong> ${comparison_data.version2.version_description || ''}</p>
                <p><strong>${__('Created By')}:</strong> ${comparison_data.version2.created_by}</p>
                <p><strong>${__('Created On')}:</strong> ${frappe.datetime.str_to_user(comparison_data.version2.created_on)}</p>
            </div>
        </div>
        
        <h4>${__('Differences')}</h4>
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>${__('Field')}</th>
                    <th>${__('Version')} ${comparison_data.version1.version_number}</th>
                    <th>${__('Version')} ${comparison_data.version2.version_number}</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    for (let field in comparison_data.differences) {
        html += `
            <tr>
                <td>${field}</td>
                <td>${comparison_data.differences[field].this_version || ''}</td>
                <td>${comparison_data.differences[field].other_version || ''}</td>
            </tr>
        `;
    }
    
    if (Object.keys(comparison_data.differences).length === 0) {
        html += `
            <tr>
                <td colspan="3">${__('No differences found')}</td>
            </tr>
        `;
    }
    
    html += `
            </tbody>
        </table>
    `;
    
    dialog.set_values({
        'comparison_html': html
    });
    
    dialog.show();
}

function show_content_snapshot_dialog(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Content Snapshot'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'snapshot_html'
            }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            dialog.hide();
        }
    });
    
    try {
        let snapshot = JSON.parse(frm.doc.content_snapshot);
        let html = `
            <div class="row">
                <div class="col-sm-6">
                    <h4>${__('Document Information')}</h4>
                    <p><strong>${__('Title')}:</strong> ${snapshot.title || ''}</p>
                    <p><strong>${__('Document Type')}:</strong> ${snapshot.document_type || ''}</p>
                    <p><strong>${__('Document Number')}:</strong> ${snapshot.document_number || ''}</p>
                    <p><strong>${__('Document Date')}:</strong> ${snapshot.document_date || ''}</p>
                    <p><strong>${__('Status')}:</strong> ${snapshot.status || ''}</p>
                    <p><strong>${__('Security Level')}:</strong> ${snapshot.security_level || ''}</p>
                    <p><strong>${__('Confidentiality Flag')}:</strong> ${snapshot.confidentiality_flag ? 'Yes' : 'No'}</p>
                    <p><strong>${__('Expiry Date')}:</strong> ${snapshot.expiry_date || ''}</p>
                    <p><strong>${__('Snapshot Time')}:</strong> ${frappe.datetime.str_to_user(snapshot.snapshot_time)}</p>
                </div>
                <div class="col-sm-6">
                    <h4>${__('Content')}</h4>
                    <div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 10px;">
                        ${snapshot.content || ''}
                    </div>
                </div>
            </div>
        `;
        
        dialog.set_values({
            'snapshot_html': html
        });
    } catch (e) {
        dialog.set_values({
            'snapshot_html': `<div class="alert alert-danger">${__('Invalid content snapshot format')}</div>`
        });
    }
    
    dialog.show();
}

function show_version_comparison(current_version, previous_version) {
    let dialog = new frappe.ui.Dialog({
        title: __('Version Comparison'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'comparison_html'
            }
        ]
    });
    
    let html = `
        <div class="row">
            <div class="col-sm-6">
                <h4>${__('Previous Version')} (${previous_version.version_number})</h4>
                <p><strong>${__('Notes')}:</strong> ${previous_version.version_notes || ''}</p>
                <p><strong>${__('Created By')}:</strong> ${previous_version.created_by}</p>
                <p><strong>${__('Created On')}:</strong> ${frappe.datetime.str_to_user(previous_version.created_on)}</p>
            </div>
            <div class="col-sm-6">
                <h4>${__('Current Version')} (${current_version.version_number})</h4>
                <p><strong>${__('Notes')}:</strong> ${current_version.version_notes || ''}</p>
                <p><strong>${__('Created By')}:</strong> ${current_version.created_by}</p>
                <p><strong>${__('Created On')}:</strong> ${frappe.datetime.str_to_user(current_version.created_on)}</p>
            </div>
        </div>
    `;
    
    dialog.set_values({
        'comparison_html': html
    });
    
    dialog.show();
}