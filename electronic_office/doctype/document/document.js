// Copyright (c) 2025, Government Agency and contributors
// For license information, please see license.txt

frappe.ui.form.on('Document', {
    refresh: function(frm) {
        // Add Create Version button
        frm.add_custom_button(__('Create Version'), function() {
            frappe.prompt([
                {
                    fieldname: 'version_notes',
                    label: __('Version Notes'),
                    fieldtype: 'Text',
                    reqd: 1
                }
            ], function(values) {
                frappe.call({
                    method: 'electronic_office.electronic_office.doctype.document.document.create_version',
                    args: {
                        docname: frm.doc.name,
                        version_notes: values.version_notes
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert(__('Version created successfully'));
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Create New Version'), __('Create'));
        }).addClass('btn-primary');
        
        // Add View Versions button
        frm.add_custom_button(__('View Versions'), function() {
            frappe.call({
                method: 'electronic_office.electronic_office.doctype.document.document.get_versions',
                args: {
                    docname: frm.doc.name
                },
                callback: function(r) {
                    if (!r.exc && r.message) {
                        show_versions_dialog(r.message);
                    }
                }
            });
        });
        
        // Add Export Document button
        frm.add_custom_button(__('Export Document'), function() {
            show_export_dialog(frm);
        });
        
        // Add Grant Access button
        if (frm.doc.owner === frappe.session.user || frappe.user.has_role('System Manager')) {
            frm.add_custom_button(__('Grant Access'), function() {
                show_grant_access_dialog(frm);
            });
        }
        
        // Set security level as read-only if Secret
        if (frm.doc.security_level === 'Secret') {
            frm.set_df_property('security_level', 'read_only', 1);
        }
        
        // Show/hide fields based on status
        if (frm.doc.status === 'Archived') {
            frm.set_df_property('status', 'read_only', 1);
        }
    },
    
    onload: function(frm) {
        // Set default document number if not set
        if (!frm.doc.document_number && frm.doc.is_new()) {
            frm.set_value('document_number', generate_document_number());
        }
    },
    
    document_type: function(frm) {
        // Set default security level from document type
        if (frm.doc.document_type && frm.doc.is_new()) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Document Type',
                    name: frm.doc.document_type
                },
                callback: function(r) {
                    if (!r.exc && r.message) {
                        if (!frm.doc.security_level) {
                            frm.set_value('security_level', r.message.default_security_level);
                        }
                    }
                }
            });
        }
    },
    
    security_level: function(frm) {
        if (frm.doc.security_level === 'Secret') {
            frappe.confirm(
                __('Are you sure you want to set this document as Secret? This will restrict access to System Managers only.'),
                function() {
                    frm.save();
                },
                function() {
                    frm.set_value('security_level', 'Internal');
                }
            );
        }
    },
    
    status: function(frm) {
        // Show confirmation for certain status changes
        if (frm.doc.status === 'Archived') {
            frappe.confirm(
                __('Are you sure you want to archive this document? It will no longer be actively available.'),
                function() {
                    frm.save();
                },
                function() {
                    frm.set_value('status', frm.doc.__last_status || 'Draft');
                }
            );
        }
    }
});

function generate_document_number() {
    // Generate a unique document number
    const timestamp = new Date().getTime();
    const random = Math.floor(Math.random() * 1000);
    return `DOC-${timestamp}-${random}`;
}

function show_versions_dialog(versions) {
    let dialog = new frappe.ui.Dialog({
        title: __('Document Versions'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'versions_html'
            }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            dialog.hide();
        }
    });
    
    let html = `
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>${__('Version Number')}</th>
                    <th>${__('Description')}</th>
                    <th>${__('Created By')}</th>
                    <th>${__('Created On')}</th>
                    <th>${__('Status')}</th>
                    <th>${__('Current')}</th>
                    <th>${__('Actions')}</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    versions.forEach(version => {
        html += `
            <tr>
                <td>${version.version_number}</td>
                <td>${version.version_description || ''}</td>
                <td>${version.created_by}</td>
                <td>${frappe.datetime.str_to_user(version.created_on)}</td>
                <td>${version.status || ''}</td>
                <td>${version.is_current ? '✓' : ''}</td>
                <td>
                    <button class="btn btn-xs btn-default" onclick="view_version_details('${version.name}')">
                        ${__('View')}
                    </button>
                    ${!version.is_current ? `<button class="btn btn-xs btn-default" onclick="restore_version('${version.name}')">
                        ${__('Restore')}
                    </button>` : ''}
                </td>
            </tr>
        `;
    });
    
    html += `
            </tbody>
        </table>
    `;
    
    dialog.set_values({
        'versions_html': html
    });
    
    dialog.show();
}

function view_version_details(version_name) {
    frappe.set_route('Form', 'Document Version', version_name);
}

function restore_version(version_name) {
    frappe.confirm(
        __('Are you sure you want to restore this version? This will replace the current document content.'),
        function() {
            frappe.call({
                method: 'electronic_office.electronic_office.doctype.document_version.document_version.restore_to_document',
                args: {
                    docname: version_name
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert(__('Version restored successfully'));
                        frappe.set_route('Form', 'Document', r.message);
                    }
                }
            });
        }
    );
}

function show_export_dialog(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Export Document'),
        fields: [
            {
                fieldname: 'export_format',
                label: __('Export Format'),
                fieldtype: 'Select',
                options: 'PDF\nJSON\nDOCX',
                default: 'PDF'
            }
        ],
        primary_action_label: __('Export'),
        primary_action: function() {
            let values = dialog.get_values();
            frappe.call({
                method: 'electronic_office.electronic_office.doctype.document.document.export_document',
                args: {
                    docname: frm.doc.name,
                    format: values.export_format
                },
                callback: function(r) {
                    if (!r.exc) {
                        if (values.export_format === 'JSON') {
                            // For JSON, show in a dialog
                            show_json_export_dialog(r.message);
                        } else {
                            frappe.show_alert(__('Document exported successfully'));
                        }
                    }
                }
            });
            dialog.hide();
        }
    });
    
    dialog.show();
}

function show_json_export_dialog(json_content) {
    let dialog = new frappe.ui.Dialog({
        title: __('Exported Document (JSON)'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'json_content'
            }
        ],
        primary_action_label: __('Download'),
        primary_action: function() {
            // Create a blob and download
            const blob = new Blob([json_content], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'document_export.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            dialog.hide();
        }
    });
    
    dialog.set_values({
        'json_content': `<pre style="max-height: 400px; overflow-y: auto;">${json_content}</pre>`
    });
    
    dialog.show();
}

function show_grant_access_dialog(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Grant Temporary Access'),
        fields: [
            {
                fieldname: 'user',
                label: __('User'),
                fieldtype: 'Link',
                options: 'User',
                reqd: 1
            },
            {
                fieldname: 'expiry_hours',
                label: __('Expiry Hours'),
                fieldtype: 'Int',
                default: 24,
                reqd: 1
            }
        ],
        primary_action_label: __('Grant Access'),
        primary_action: function() {
            let values = dialog.get_values();
            frappe.call({
                method: 'electronic_office.electronic_office.doctype.document.document.grant_temporary_access',
                args: {
                    docname: frm.doc.name,
                    user: values.user,
                    expiry_hours: values.expiry_hours
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert(__('Access granted successfully'));
                    }
                }
            });
            dialog.hide();
        }
    });
    
    dialog.show();
}

function show_versions_dialog(versions) {
    let dialog = new frappe.ui.Dialog({
        title: __('Document Versions'),
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'versions_html'
            }
        ]
    });
    
    let html = `
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>${__('Version Number')}</th>
                    <th>${__('Notes')}</th>
                    <th>${__('Created By')}</th>
                    <th>${__('Created On')}</th>
                    <th>${__('Current')}</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    versions.forEach(version => {
        html += `
            <tr>
                <td>${version.version_number}</td>
                <td>${version.version_notes || ''}</td>
                <td>${version.created_by}</td>
                <td>${frappe.datetime.str_to_user(version.created_on)}</td>
                <td>${version.is_current ? '✓' : ''}</td>
            </tr>
        `;
    });
    
    html += `
            </tbody>
        </table>
    `;
    
    dialog.set_values({
        'versions_html': html
    });
    
    dialog.show();
}