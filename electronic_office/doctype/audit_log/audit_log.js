// Copyright (c) 2025, Government Agency and contributors
// For license information, please see license.txt

frappe.ui.form.on('Audit Log', {
    refresh: function(frm) {
        if (frm.doc.document) {
            frm.add_custom_button(__('View Document'), function() {
                frappe.set_route('Form', 'Document', frm.doc.document);
            });
        }
        
        if (frm.doc.performed_by) {
            frm.add_custom_button(__('View User'), function() {
                frappe.set_route('Form', 'User', frm.doc.performed_by);
            });
        }
        
        frm.add_custom_button(__('Export'), function() {
            show_export_dialog(frm);
        });
        
        // Add filter buttons for quick access
        frm.add_custom_button(__('Security Events'), function() {
            frappe.set_route('List', 'Audit Log', {
                'action': ['in', 'Login Failed, Password Changed, User Created, User Deleted, Role Changed, Permission Changed, Document Access Denied, Signature Verification Failed, Document Version Reverted']
            });
        }, __('Filter'));
        
        // Show location info if available
        if (frm.doc.ip_address) {
            frm.dashboard.add_indicator(__('IP: ') + frm.doc.ip_address, 'blue');
        }
    },
    
    performed_by: function(frm) {
        if (frm.doc.performed_by) {
            // Show user info
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'User',
                    name: frm.doc.performed_by
                },
                callback: function(r) {
                    if (!r.exc && r.message) {
                        frm.fields_dict.performed_by.$input.attr('title', r.message.full_name);
                    }
                }
            });
        }
    }
});

function show_export_dialog(frm) {
    let dialog = new frappe.ui.Dialog({
        title: __('Export Audit Log'),
        fields: [
            {
                fieldtype: 'Date',
                label: __('Start Date'),
                fieldname: 'start_date',
                reqd: 1
            },
            {
                fieldtype: 'Date',
                label: __('End Date'),
                fieldname: 'end_date',
                reqd: 1
            },
            {
                fieldtype: 'Select',
                label: __('Format'),
                fieldname: 'format',
                options: ['CSV', 'JSON'],
                default: 'CSV',
                reqd: 1
            },
            {
                fieldtype: 'Check',
                label: __('Current Document Only'),
                fieldname: 'document_only',
                default: 0
            }
        ],
        primary_action_label: __('Export'),
        primary_action: function() {
            let values = dialog.get_values();
            
            let filters = {
                'performed_on': ['>=', values.start_date],
                'performed_on': ['<=', values.end_date]
            };
            
            if (values.document_only && frm.doc.document) {
                filters['document'] = frm.doc.document;
            }
            
            frappe.call({
                method: 'electronic_office.electronic_office.doctype.audit_log.audit_log.export_audit_log',
                args: {
                    filters: filters,
                    format: values.format.toLowerCase()
                },
                callback: function(r) {
                    if (!r.exc && r.message) {
                        let filename = `audit_log_${values.start_date}_to_${values.end_date}.${values.format.toLowerCase()}`;
                        frappe.utils.download_file(r.message, filename);
                        dialog.hide();
                    }
                }
            });
        }
    });
    
    dialog.show();
}

// Add list view customizations
frappe.listview_settings['Audit Log'] = {
    add_fields: ['document', 'performed_by', 'performed_on', 'ip_address'],
    get_indicator: function(doc) {
        if (doc.action.includes('Failed')) {
            return [__('Failed'), 'red', 'action,=,' + doc.action];
        } else if (doc.action.includes('Deleted') || doc.action.includes('Revoked')) {
            return [__('Removed'), 'orange', 'action,=,' + doc.action];
        } else if (doc.action.includes('Created') || doc.action.includes('Added')) {
            return [__('Created'), 'green', 'action,=,' + doc.action];
        } else if (doc.action.includes('Updated') || doc.action.includes('Modified')) {
            return [__('Updated'), 'blue', 'action,=,' + doc.action];
        } else if (doc.action.includes('Verified') || doc.action.includes('Approved')) {
            return [__('Verified'), 'green', 'action,=,' + doc.action];
        } else {
            return [doc.action, 'gray', 'action,=,' + doc.action];
        }
    },
    onload: function(listview) {
        // Add custom filter for security events
        listview.page.add_menu_item(__('Security Events'), function() {
            listview.filter_area.add([
                listview.filter_area.new_filter('action'),
                'in',
                'Login Failed, Password Changed, User Created, User Deleted, Role Changed, Permission Changed, Document Access Denied, Signature Verification Failed, Document Version Reverted'
            ]);
        });
        
        // Add export option
        listview.page.add_menu_item(__('Export All'), function() {
            show_export_dialog({doc: {}});
        });
    }
};