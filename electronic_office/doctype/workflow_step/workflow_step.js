frappe.ui.form.on('Workflow Step', {
    refresh: function(frm) {
        // Handle field visibility based on step type
        handle_step_type_visibility(frm);
        
        // Handle field visibility based on assignee type
        handle_assignee_type_visibility(frm);
        
        // Add test button for dynamic assignee
        if (frm.doc.assignee_type === 'Dynamic') {
            frm.add_custom_button(__('Test Dynamic Assignee'), function() {
                test_dynamic_assignee(frm);
            });
        }
        
        // Add preview button
        frm.add_custom_button(__('Preview Step'), function() {
            preview_step(frm);
        });
    },
    
    onload: function(frm) {
        // Set default values for new documents
        if (frm.is_new()) {
            frm.set_value('step_order', 1);
            frm.set_value('notify_on_timeout', 1);
            frm.set_value('notify_on_escalation', 1);
        }
    },
    
    step_type: function(frm) {
        handle_step_type_visibility(frm);
    },
    
    assignee_type: function(frm) {
        handle_assignee_type_visibility(frm);
    }
});

function handle_step_type_visibility(frm) {
    const is_start_or_end = frm.doc.step_type === 'Start' || frm.doc.step_type === 'End';
    const is_notification = frm.doc.step_type === 'Notification';
    
    // Hide assignee fields for Start and End steps
    frm.set_df_property('assignee_type', 'hidden', is_start_or_end);
    frm.set_df_property('assignee_value', 'hidden', is_start_or_end);
    frm.set_df_property('allowed_roles', 'hidden', is_start_or_end);
    
    // Hide timeout and escalation fields for Start, End, and Notification steps
    frm.set_df_property('time_limit', 'hidden', is_start_or_end || is_notification);
    frm.set_df_property('timeout_days', 'hidden', is_start_or_end || is_notification);
    frm.set_df_property('escalation_days', 'hidden', is_start_or_end || is_notification);
    frm.set_df_property('notify_on_timeout', 'hidden', is_start_or_end || is_notification);
    frm.set_df_property('notify_on_escalation', 'hidden', is_start_or_end || is_notification);
    
    // Hide action fields for End and Notification steps
    frm.set_df_property('allow_skip', 'hidden', is_start_or_end || is_notification);
    frm.set_df_property('allow_reject', 'hidden', is_start_or_end || is_notification);
    frm.set_df_property('actions', 'hidden', is_start_or_end || is_notification);
    
    // Set default values for Start and End steps
    if (is_start_or_end) {
        frm.set_value('assignee_type', 'None');
        frm.set_value('assignee_value', '');
        frm.set_value('allowed_roles', []);
        frm.set_value('time_limit', 0);
        frm.set_value('timeout_days', 0);
        frm.set_value('escalation_days', 0);
        frm.set_value('notify_on_timeout', 0);
        frm.set_value('notify_on_escalation', 0);
        frm.set_value('allow_skip', 0);
        frm.set_value('allow_reject', 0);
    }
}

function handle_assignee_type_visibility(frm) {
    const is_none = frm.doc.assignee_type === 'None';
    const is_dynamic = frm.doc.assignee_type === 'Dynamic';
    
    // Hide assignee value for None type
    frm.set_df_property('assignee_value', 'hidden', is_none);
    
    // Show custom script for Dynamic type, hide for others
    frm.set_df_property('custom_script', 'hidden', !is_dynamic);
    
    // Set query for assignee value based on type
    if (!is_none) {
        if (frm.doc.assignee_type === 'Role') {
            frm.set_query('assignee_value', function() {
                return {
                    filters: {
                        'disabled': 0
                    }
                };
            });
        } else if (frm.doc.assignee_type === 'User') {
            frm.set_query('assignee_value', function() {
                return {
                    filters: {
                        'enabled': 1
                    }
                };
            });
        }
    }
}

function test_dynamic_assignee(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Test Dynamic Assignee'),
        fields: [
            { fieldtype: 'Link', fieldname: 'document', label: __('Test Document'), options: 'Document', reqd: 1 },
            { fieldtype: 'HTML', fieldname: 'result' }
        ],
        primary_action_label: __('Test'),
        primary_action: function() {
            const document_name = dialog.get_value('document');
            
            frappe.call({
                method: 'electronic_office.electronic_office.doctype.workflow_step.workflow_step.get_assignees',
                args: {
                    step_name: frm.doc.name,
                    document: document_name
                },
                callback: function(r) {
                    if (r.message) {
                        const result_html = generate_test_result_html(r.message);
                        dialog.get_field('result').$wrapper.html(result_html);
                    }
                }
            });
        }
    });
    
    dialog.show();
}

function generate_test_result_html(assignees) {
    let html = '<div class="test-result">';
    
    if (assignees.length === 0) {
        html += '<p class="text-muted">' + __('No assignees found') + '</p>';
    } else {
        html += '<h5>' + __('Assignees') + '</h5>';
        html += '<ul class="assignee-list">';
        assignees.forEach(assignee => {
            html += '<li>' + assignee + '</li>';
        });
        html += '</ul>';
    }
    
    html += '</div>';
    return html;
}

function preview_step(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Step Preview'),
        fields: [
            { fieldtype: 'HTML', fieldname: 'preview' }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            dialog.hide();
        }
    });
    
    const preview_html = generate_step_preview_html(frm.doc);
    dialog.get_field('preview').$wrapper.html(preview_html);
    dialog.show();
}

function generate_step_preview_html(step) {
    let html = '<div class="step-preview">';
    html += '<h3>' + step.step_name + '</h3>';
    html += '<p><strong>' + __('Type') + ':</strong> ' + step.step_type + '</p>';
    
    if (step.description) {
        html += '<p><strong>' + __('Description') + ':</strong> ' + step.description + '</p>';
    }
    
    html += '<p><strong>' + __('Order') + ':</strong> ' + step.step_order + '</p>';
    
    if (step.assignee_type !== 'None') {
        html += '<p><strong>' + __('Assignee Type') + ':</strong> ' + step.assignee_type + '</p>';
        
        if (step.assignee_value) {
            html += '<p><strong>' + __('Assignee Value') + ':</strong> ' + step.assignee_value + '</p>';
        }
        
        if (step.allowed_roles && step.allowed_roles.length > 0) {
            html += '<p><strong>' + __('Allowed Roles') + ':</strong> ' + step.allowed_roles.join(', ') + '</p>';
        }
    }
    
    if (step.time_limit) {
        html += '<p><strong>' + __('Time Limit') + ':</strong> ' + step.time_limit + ' ' + __('hours') + '</p>';
    }
    
    if (step.timeout_days) {
        html += '<p><strong>' + __('Timeout Days') + ':</strong> ' + step.timeout_days + '</p>';
    }
    
    if (step.escalation_days) {
        html += '<p><strong>' + __('Escalation Days') + ':</strong> ' + step.escalation_days + '</p>';
    }
    
    html += '<p><strong>' + __('Notify on Timeout') + ':</strong> ' + (step.notify_on_timeout ? __('Yes') : __('No')) + '</p>';
    html += '<p><strong>' + __('Notify on Escalation') + ':</strong> ' + (step.notify_on_escalation ? __('Yes') : __('No')) + '</p>';
    html += '<p><strong>' + __('Allow Skip') + ':</strong> ' + (step.allow_skip ? __('Yes') : __('No')) + '</p>';
    html += '<p><strong>' + __('Allow Reject') + ':</strong> ' + (step.allow_reject ? __('Yes') : __('No')) + '</p>';
    
    if (step.actions && step.actions.length > 0) {
        html += '<h5>' + __('Actions') + '</h5>';
        html += '<ul class="action-list">';
        step.actions.forEach(action => {
            html += '<li>' + action.action_name + ' (' + action.action_type + ')</li>';
        });
        html += '</ul>';
    }
    
    if (step.conditions && step.conditions.length > 0) {
        html += '<h5>' + __('Conditions') + '</h5>';
        html += '<ul class="condition-list">';
        step.conditions.forEach(condition => {
            html += '<li>' + condition.condition_name + '</li>';
        });
        html += '</ul>';
    }
    
    html += '</div>';
    return html;
}

frappe.ui.form.on('Workflow Step Action', {
    actions_add: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.action_type) {
            frappe.model.set_value(cdt, cdn, 'action_type', 'Approval');
        }
        if (!row.role) {
            frappe.model.set_value(cdt, cdn, 'role', 'All');
        }
    },
    
    action_type: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        
        // Hide/show next step based on action type
        if (row.action_type === 'Approval' || row.action_type === 'Rejection') {
            frappe.model.set_value(cdt, cdn, 'next_step', '');
            frm.set_df_property('next_step', 'hidden', 1, cdn);
        } else {
            frm.set_df_property('next_step', 'hidden', 0, cdn);
            
            // Set query for next step
            frm.set_query('next_step', cdt, cdn, function() {
                return {
                    filters: {
                        'parent': frm.doc.parent,
                        'parenttype': 'Workflow Definition',
                        'name': ['!=', row.name]
                    }
                };
            });
        }
    }
});

frappe.ui.form.on('Workflow Step Condition', {
    conditions_add: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.condition_type) {
            frappe.model.set_value(cdt, cdn, 'condition_type', 'Field-based');
        }
        if (!row.operator) {
            frappe.model.set_value(cdt, cdn, 'operator', 'equals');
        }
        if (!row.logical_operator) {
            frappe.model.set_value(cdt, cdn, 'logical_operator', 'AND');
        }
    },
    
    condition_type: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        
        if (row.condition_type === 'Field-based') {
            frm.set_df_property('field_name', 'hidden', 0, cdn);
            frm.set_df_property('operator', 'hidden', 0, cdn);
            frm.set_df_property('value', 'hidden', 0, cdn);
            frm.set_df_property('role', 'hidden', 1, cdn);
            
            // Set field options based on document type
            if (frm.doc.parent && frm.doc.parenttype === 'Workflow Definition') {
                const workflow_def = frappe.get_doc('Workflow Definition', frm.doc.parent);
                if (workflow_def.document_type) {
                    // This would typically fetch fields from the document type
                    // For now, we'll leave it as a text field
                }
            }
        } else if (row.condition_type === 'Role-based') {
            frm.set_df_property('field_name', 'hidden', 1, cdn);
            frm.set_df_property('operator', 'hidden', 1, cdn);
            frm.set_df_property('value', 'hidden', 1, cdn);
            frm.set_df_property('role', 'hidden', 0, cdn);
            
            // Set query for role
            frm.set_query('role', cdt, cdn, function() {
                return {
                    filters: {
                        'disabled': 0
                    }
                };
            });
        } else {
            frm.set_df_property('field_name', 'hidden', 0, cdn);
            frm.set_df_property('operator', 'hidden', 0, cdn);
            frm.set_df_property('value', 'hidden', 0, cdn);
            frm.set_df_property('role', 'hidden', 1, cdn);
        }
    }
});