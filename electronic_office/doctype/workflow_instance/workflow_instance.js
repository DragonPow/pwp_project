frappe.ui.form.on('Workflow Instance', {
    refresh: function(frm) {
        if (frm.doc.status === 'In Progress') {
            frm.add_custom_button(__('View Document'), function() {
                frappe.set_route('Form', 'Document', frm.doc.document);
            }).addClass('btn-primary');
            
            frm.add_custom_button(__('Reassign Step'), function() {
                reassign_step(frm);
            });
            
            frm.add_custom_button(__('Cancel Workflow'), function() {
                cancel_workflow(frm);
            });
        }
        
        if (frm.doc.status === 'Pending') {
            frm.add_custom_button(__('Start Workflow'), function() {
                start_workflow(frm);
            }).addClass('btn-primary');
        }
        
        if (frm.doc.status === 'Completed' || frm.doc.status === 'Cancelled') {
            frm.add_custom_button(__('View Document'), function() {
                frappe.set_route('Form', 'Document', frm.doc.document);
            }).addClass('btn-primary');
        }
        
        if (frm.doc.status !== 'Pending') {
            frm.add_custom_button(__('Workflow History'), function() {
                show_workflow_history(frm);
            });
        }
        
        if (frm.doc.status === 'In Progress') {
            load_pending_actions(frm);
        }
        
        // Add assignees field
        if (frm.doc.current_assignees && frm.doc.current_assignees.length > 0) {
            const assignees_html = frm.doc.current_assignees.map(assignee => {
                return `<span class="label label-info">${assignee}</span>`;
            }).join(' ');
            
            $(frm.fields_dict.current_assignees.wrapper).html(assignees_html);
        }
    },
    
    onload: function(frm) {
        if (frm.doc.status === 'In Progress') {
            load_workflow_visualization(frm);
        }
    }
});

function load_pending_actions(frm) {
    frappe.call({
        method: 'electronic_office.electronic_office.doctype.workflow_instance.workflow_instance.get_workflow_instance_details',
        args: {
            workflow_instance_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.pending_actions) {
                const actions_wrapper = frm.fields_dict['pending_actions'].$wrapper;
                actions_wrapper.empty();
                
                if (r.message.pending_actions.length > 0) {
                    const actions_html = r.message.pending_actions.map(action => {
                        let button_class = 'btn-sm';
                        
                        // Set button color based on action type
                        if (action.action_type === 'Approval') {
                            button_class += ' btn-success';
                        } else if (action.action_type === 'Rejection') {
                            button_class += ' btn-danger';
                        } else if (action.action_type === 'Forward') {
                            button_class += ' btn-primary';
                        } else {
                            button_class += ' btn-default';
                        }
                        
                        return `<button class="btn ${button_class}" data-action="${action.action_name}" data-action-type="${action.action_type}">${action.action_name}</button>`;
                    }).join(' ');
                    
                    actions_wrapper.html(actions_html);
                    
                    actions_wrapper.find('button').on('click', function() {
                        const action_name = $(this).data('action');
                        const action_type = $(this).data('action-type');
                        execute_workflow_action(frm, action_name, action_type);
                    });
                } else {
                    actions_wrapper.html('<p class="text-muted">' + __('No pending actions') + '</p>');
                }
            }
        }
    });
}

function execute_workflow_action(frm, action_name, action_type) {
    let fields = [
        { fieldtype: 'Text Editor', fieldname: 'comment', label: __('Comment') }
    ];
    
    // Add reason field for rejection or cancellation
    if (action_type === 'Rejection' || action_type === 'Cancel') {
        fields.push({ fieldtype: 'Text', fieldname: 'reason', label: __('Reason'), reqd: 1 });
    }
    
    // Add next step field for forward action
    if (action_type === 'Forward') {
        fields.push({ fieldtype: 'Select', fieldname: 'next_step', label: __('Next Step'), reqd: 1, options: get_next_step_options(frm) });
    }
    
    const dialog = new frappe.ui.Dialog({
        title: __('Execute Action: {0}', [action_name]),
        fields: fields,
        primary_action_label: __('Execute'),
        primary_action: function() {
            const values = dialog.get_values();
            
            frappe.call({
                method: 'electronic_office.electronic_office.doctype.workflow_instance.workflow_instance.execute_workflow_action',
                args: {
                    workflow_instance: frm.doc.name,
                    action_name: action_name,
                    comment: values.comment,
                    reason: values.reason,
                    next_step: values.next_step
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({ message: __('Action executed successfully'), indicator: 'green' });
                        dialog.hide();
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    
    dialog.show();
}

function get_next_step_options(frm) {
    // This would typically fetch available next steps from the server
    // For now, return an empty array
    return [];
}

function start_workflow(frm) {
    frappe.call({
        method: 'electronic_office.electronic_office.doctype.workflow_instance.workflow_instance.start_workflow',
        args: {
            workflow_instance: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({ message: __('Workflow started successfully'), indicator: 'green' });
                frm.reload_doc();
            }
        }
    });
}

function reassign_step(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Reassign Workflow Step'),
        fields: [
            { fieldtype: 'Link', fieldname: 'new_assignee', label: __('New Assignee'), options: 'User', reqd: 1 },
            { fieldtype: 'Text Editor', fieldname: 'reason', label: __('Reason') }
        ],
        primary_action_label: __('Reassign'),
        primary_action: function() {
            const new_assignee = dialog.get_value('new_assignee');
            const reason = dialog.get_value('reason');
            
            frappe.call({
                method: 'electronic_office.electronic_office.doctype.workflow_instance.workflow_instance.reassign_workflow_step',
                args: {
                    workflow_instance: frm.doc.name,
                    new_assignee: new_assignee
                },
                callback: function(r) {
                    if (r.message) {
                        if (reason) {
                            frm.add_comment('Comment', __('Step reassigned to {0}: {1}', [new_assignee, reason]));
                        }
                        frappe.show_alert({ message: __('Step reassigned successfully'), indicator: 'green' });
                        dialog.hide();
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    
    dialog.show();
}

function cancel_workflow(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Cancel Workflow'),
        fields: [
            { fieldtype: 'Text Editor', fieldname: 'reason', label: __('Reason'), reqd: 1 }
        ],
        primary_action_label: __('Cancel Workflow'),
        primary_action: function() {
            const reason = dialog.get_value('reason');
            
            frappe.call({
                method: 'electronic_office.electronic_office.doctype.workflow_instance.workflow_instance.cancel_workflow_instance',
                args: {
                    workflow_instance: frm.doc.name,
                    reason: reason
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({ message: __('Workflow cancelled successfully'), indicator: 'green' });
                        dialog.hide();
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    
    dialog.show();
}

function show_workflow_history(frm) {
    frappe.call({
        method: 'electronic_office.electronic_office.doctype.workflow_instance.workflow_instance.get_workflow_history',
        args: {
            workflow_instance: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                const dialog = new frappe.ui.Dialog({
                    title: __('Workflow History'),
                    fields: [
                        { fieldtype: 'HTML', fieldname: 'workflow_history' }
                    ],
                    primary_action_label: __('Close'),
                    primary_action: function() {
                        dialog.hide();
                    }
                });
                
                const history_html = generate_workflow_history_html(r.message);
                dialog.get_field('workflow_history').$wrapper.html(history_html);
                dialog.show();
            }
        }
    });
}

function generate_workflow_history_html(history) {
    let html = '<div class="workflow-history">';
    
    if (history.length === 0) {
        html += '<p class="text-muted">' + __('No workflow history found') + '</p>';
    } else {
        history.forEach(entry => {
            html += '<div class="history-item">';
            html += '<div class="history-header">';
            html += '<strong>' + entry.action + '</strong>';
            html += '<span class="pull-right">' + frappe.datetime.str_to_user(entry.timestamp) + '</span>';
            html += '</div>';
            html += '<div class="history-body">';
            html += '<p><strong>' + __('User') + ':</strong> ' + entry.user + '</p>';
            html += '<p><strong>' + __('Description') + ':</strong> ' + entry.description + '</p>';
            
            if (entry.step) {
                html += '<p><strong>' + __('Step') + ':</strong> ' + entry.step + '</p>';
            }
            
            html += '</div>';
            html += '</div>';
        });
    }
    
    html += '</div>';
    return html;
}

function load_workflow_visualization(frm) {
    frappe.call({
        method: 'electronic_office.electronic_office.doctype.workflow_instance.workflow_instance.get_workflow_instance_details',
        args: {
            workflow_instance_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                const visualization_wrapper = frm.fields_dict['workflow_visualization'].$wrapper;
                const visualization_html = generate_workflow_visualization_html(r.message);
                visualization_wrapper.html(visualization_html);
            }
        }
    });
}

function generate_workflow_visualization_html(data) {
    let html = '<div class="workflow-visualization">';
    
    if (data.workflow_definition && data.workflow_definition.steps) {
        const steps = data.workflow_definition.steps.sort((a, b) => a.step_order - b.step_order);
        
        html += '<div class="workflow-steps">';
        html += '<h4>' + __('Workflow Progress') + '</h4>';
        html += '<div class="step-container">';
        
        steps.forEach((step, index) => {
            const is_current = step.step_order === data.current_step;
            const is_completed = step.step_order < data.current_step;
            const is_pending = step.step_order > data.current_step;
            
            let step_class = 'step';
            if (is_current) {
                step_class += ' current';
            } else if (is_completed) {
                step_class += ' completed';
            } else if (is_pending) {
                step_class += ' pending';
            }
            
            html += '<div class="' + step_class + '">';
            html += '<div class="step-number">' + step.step_order + '</div>';
            html += '<div class="step-content">';
            html += '<div class="step-name">' + step.step_name + '</div>';
            html += '<div class="step-type">' + step.step_type + '</div>';
            
            if (is_current) {
                html += '<div class="step-status">' + __('Current Step') + '</div>';
            } else if (is_completed) {
                html += '<div class="step-status">' + __('Completed') + '</div>';
            } else if (is_pending) {
                html += '<div class="step-status">' + __('Pending') + '</div>';
            }
            
            html += '</div>';
            html += '</div>';
            
            if (index < steps.length - 1) {
                html += '<div class="step-arrow">→</div>';
            }
        });
        
        html += '</div>';
        html += '</div>';
    }
    
    html += '</div>';
    return html;
}