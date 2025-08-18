// Copyright (c) 2025, Government Agency and contributors
// For license information, please see license.txt

frappe.ui.form.on('Task', {
    refresh: function(frm) {
        if (frm.doc.status === 'Pending') {
            frm.add_custom_button(__('Start Task'), function() {
                frappe.call({
                    method: 'electronic_office.electronic_office.doctype.task.task.start_task',
                    args: {
                        docname: frm.doc.name
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert(__('Task started successfully'));
                            frm.reload_doc();
                        }
                    }
                });
            });
        }
        
        if (frm.doc.status === 'In Progress') {
            frm.add_custom_button(__('Complete Task'), function() {
                frappe.call({
                    method: 'electronic_office.electronic_office.doctype.task.task.complete_task',
                    args: {
                        docname: frm.doc.name
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert(__('Task completed successfully'));
                            frm.reload_doc();
                        }
                    }
                });
            });
            
            frm.add_custom_button(__('Cancel Task'), function() {
                frappe.prompt([
                    {
                        fieldname: 'reason',
                        label: __('Cancellation Reason'),
                        fieldtype: 'Text',
                        reqd: 1
                    }
                ], function(values) {
                    frappe.call({
                        method: 'electronic_office.electronic_office.doctype.task.task.cancel_task',
                        args: {
                            docname: frm.doc.name,
                            reason: values.reason
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert(__('Task cancelled'));
                                frm.reload_doc();
                            }
                        }
                    });
                }, __('Cancel Task'), __('Cancel'));
            });
        }
        
        if (frm.doc.assigned_to) {
            frm.add_custom_button(__('Reassign Task'), function() {
                frappe.prompt([
                    {
                        fieldname: 'new_assignee',
                        label: __('New Assignee'),
                        fieldtype: 'Link',
                        options: 'User',
                        reqd: 1
                    }
                ], function(values) {
                    frappe.call({
                        method: 'electronic_office.electronic_office.doctype.task.task.reassign_task',
                        args: {
                            docname: frm.doc.name,
                            new_assignee: values.new_assignee
                        },
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert(__('Task reassigned successfully'));
                                frm.reload_doc();
                            }
                        }
                    });
                }, __('Reassign Task'), __('Reassign'));
            });
        }
        
        if (frm.doc.document) {
            frm.add_custom_button(__('View Document'), function() {
                frappe.set_route('Form', 'Document', frm.doc.document);
            });
        }
        
        // Show overdue indicator
        if (frm.doc.due_date && frm.doc.status !== 'Completed' && frm.doc.status !== 'Cancelled') {
            const due_date = frappe.datetime.str_to_obj(frm.doc.due_date);
            const today = frappe.datetime.str_to_obj(frappe.datetime.now_date());
            
            if (due_date < today) {
                frm.dashboard.add_indicator(__('Overdue'), 'red');
            } else if (due_date.getTime() - today.getTime() <= 2 * 24 * 60 * 60 * 1000) {
                frm.dashboard.add_indicator(__('Due Soon'), 'orange');
            } else {
                frm.dashboard.add_indicator(__('On Track'), 'green');
            }
        }
        
        // Highlight priority
        if (frm.doc.priority === 'Urgent') {
            $(frm.fields_dict.title.wrapper).addClass('text-danger');
        } else if (frm.doc.priority === 'High') {
            $(frm.fields_dict.title.wrapper).addClass('text-warning');
        }
    },
    
    status: function(frm) {
        if (frm.doc.status === 'Completed') {
            frm.set_df_property('completed_on', 'read_only', 0);
            frm.set_value('completed_on', frappe.datetime.now_datetime());
            frm.set_df_property('completed_on', 'read_only', 1);
        } else {
            frm.set_value('completed_on', '');
        }
    },
    
    assigned_to: function(frm) {
        if (frm.doc.assigned_to) {
            // Show user info
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'User',
                    name: frm.doc.assigned_to
                },
                callback: function(r) {
                    if (!r.exc && r.message) {
                        frm.fields_dict.assigned_to.$input.attr('title', r.message.full_name);
                    }
                }
            });
        }
    }
});