frappe.ui.form.on('Workflow Definition', {
    refresh: function(frm) {
        frm.add_custom_button(__('Preview Workflow'), function() {
            preview_workflow(frm);
        }).addClass('btn-primary');

        frm.add_custom_button(__('Test Workflow'), function() {
            test_workflow(frm);
        });

        if (frm.doc.is_active) {
            frm.add_custom_button(__('Deactivate'), function() {
                deactivate_workflow(frm);
            });
        } else {
            frm.add_custom_button(__('Activate'), function() {
                activate_workflow(frm);
            });
        }

        // Add workflow visualization button
        frm.add_custom_button(__('Visualize Workflow'), function() {
            visualize_workflow(frm);
        });

        // Add duplicate workflow button
        if (!frm.is_new()) {
            frm.add_custom_button(__('Duplicate Workflow'), function() {
                duplicate_workflow(frm);
            });
        }
    },

    onload: function(frm) {
        // Set default values for new documents
        if (frm.is_new()) {
            frm.set_value('is_active', 0);
            frm.set_value('notify_on_timeout', 1);
            frm.set_value('notify_on_escalation', 1);
        }
    },

    document_type: function(frm) {
        if (frm.doc.document_type) {
            // Update field queries based on document type
            update_field_queries(frm);
        }
    },

    is_active: function(frm) {
        if (frm.doc.is_active) {
            // Check if workflow is valid before activating
            validate_workflow_before_activation(frm);
        }
    }
});

function update_field_queries(frm) {
    // Update assignee value query for steps
    frm.set_query('assignee_value', 'steps', function() {
        return {
            query: 'pwp_project.pwp_project.doctype.workflow_definition.workflow_definition.get_assignee_options',
            filters: {
                document_type: frm.doc.document_type
            }
        };
    });

    // Update field name query for conditions
    frm.set_query('field_name', 'conditions', function() {
        return {
            query: 'pwp_project.pwp_project.doctype.workflow_definition.workflow_definition.get_document_fields',
            filters: {
                document_type: frm.doc.document_type
            }
        };
    });

    // Update role query for permissions
    frm.set_query('role', 'permissions', function() {
        return {
            filters: {
                'disabled': 0
            }
        };
    });
}

function validate_workflow_before_activation(frm) {
    // Check if workflow has at least one start and one end step
    const start_steps = frm.doc.steps.filter(step => step.step_type === 'Start');
    const end_steps = frm.doc.steps.filter(step => step.step_type === 'End');

    if (start_steps.length !== 1) {
        frappe.msgprint(__('Workflow must have exactly one Start step'));
        frm.set_value('is_active', 0);
        return;
    }

    if (end_steps.length === 0) {
        frappe.msgprint(__('Workflow must have at least one End step'));
        frm.set_value('is_active', 0);
        return;
    }

    // Check if step orders are unique and sequential
    const step_orders = frm.doc.steps.map(step => step.step_order).sort((a, b) => a - b);
    for (let i = 0; i < step_orders.length; i++) {
        if (step_orders[i] !== i + 1) {
            frappe.msgprint(__('Step orders must be unique and sequential starting from 1'));
            frm.set_value('is_active', 0);
            return;
        }
    }
}

function activate_workflow(frm) {
    frappe.call({
        method: 'pwp_project.pwp_project.doctype.workflow_definition.workflow_definition.activate_workflow',
        args: {
            workflow_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({ message: __('Workflow activated successfully'), indicator: 'green' });
                frm.reload_doc();
            }
        }
    });
}

function deactivate_workflow(frm) {
    frappe.call({
        method: 'pwp_project.pwp_project.doctype.workflow_definition.workflow_definition.deactivate_workflow',
        args: {
            workflow_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({ message: __('Workflow deactivated successfully'), indicator: 'green' });
                frm.reload_doc();
            }
        }
    });
}

function duplicate_workflow(frm) {
    frappe.call({
        method: 'pwp_project.pwp_project.doctype.workflow_definition.workflow_definition.duplicate_workflow',
        args: {
            workflow_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({ message: __('Workflow duplicated successfully'), indicator: 'green' });
                frappe.set_route('Form', 'Workflow Definition', r.message);
            }
        }
    });
}

frappe.ui.form.on('Workflow Step', {
    steps_add: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.step_order) {
            const max_order = Math.max(0, ...frm.doc.steps.map(s => s.step_order || 0));
            frappe.model.set_value(cdt, cdn, 'step_order', max_order + 1);
        }
        if (!row.step_type) {
            frappe.model.set_value(cdt, cdn, 'step_type', 'Approval');
        }
        if (!row.assignee_type) {
            frappe.model.set_value(cdt, cdn, 'assignee_type', 'Role');
        }
        if (!row.notify_on_timeout) {
            frappe.model.set_value(cdt, cdn, 'notify_on_timeout', 1);
        }
        if (!row.notify_on_escalation) {
            frappe.model.set_value(cdt, cdn, 'notify_on_escalation', 1);
        }
    },

    step_type: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (row.step_type === 'Start' || row.step_type === 'End') {
            frappe.model.set_value(cdt, cdn, 'assignee_type', 'None');
            frappe.model.set_value(cdt, cdn, 'assignee_value', '');
            frappe.model.set_value(cdt, cdn, 'allowed_roles', []);
            frappe.model.set_value(cdt, cdn, 'time_limit', 0);
            frappe.model.set_value(cdt, cdn, 'timeout_days', 0);
            frappe.model.set_value(cdt, cdn, 'escalation_days', 0);
            frappe.model.set_value(cdt, cdn, 'notify_on_timeout', 0);
            frappe.model.set_value(cdt, cdn, 'notify_on_escalation', 0);
            frappe.model.set_value(cdt, cdn, 'allow_skip', 0);
            frappe.model.set_value(cdt, cdn, 'allow_reject', 0);
        }
    },

    assignee_type: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (row.assignee_type === 'None') {
            frappe.model.set_value(cdt, cdn, 'assignee_value', '');
            frappe.model.set_value(cdt, cdn, 'allowed_roles', []);
        }
    }
});

frappe.ui.form.on('Workflow Transition', {
    transitions_add: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.auto_transition) {
            frappe.model.set_value(cdt, cdn, 'auto_transition', 0);
        }
        if (!row.notify_on_transition) {
            frappe.model.set_value(cdt, cdn, 'notify_on_transition', 1);
        }

        // Set query for from_step and to_step
        frm.set_query('from_step', cdt, cdn, function() {
            return {
                filters: {
                    'parent': frm.doc.name,
                    'parenttype': 'Workflow Definition'
                }
            };
        });

        frm.set_query('to_step', cdt, cdn, function() {
            return {
                filters: {
                    'parent': frm.doc.name,
                    'parenttype': 'Workflow Definition'
                }
            };
        });
    }
});

frappe.ui.form.on('Workflow Condition', {
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

frappe.ui.form.on('Workflow Permission', {
    permissions_add: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.permission_level) {
            frappe.model.set_value(cdt, cdn, 'permission_level', 'Read');
        }
        if (!row.allow_read) {
            frappe.model.set_value(cdt, cdn, 'allow_read', 1);
        }
    },

    permission_level: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        // Set permissions based on permission level
        if (row.permission_level === 'Read') {
            frappe.model.set_value(cdt, cdn, 'allow_read', 1);
            frappe.model.set_value(cdt, cdn, 'allow_write', 0);
            frappe.model.set_value(cdt, cdn, 'allow_create', 0);
            frappe.model.set_value(cdt, cdn, 'allow_delete', 0);
            frappe.model.set_value(cdt, cdn, 'allow_share', 0);
            frappe.model.set_value(cdt, cdn, 'allow_export', 0);
            frappe.model.set_value(cdt, cdn, 'allow_print', 0);
            frappe.model.set_value(cdt, cdn, 'allow_email', 0);
            frappe.model.set_value(cdt, cdn, 'allow_report', 0);
        } else if (row.permission_level === 'Write') {
            frappe.model.set_value(cdt, cdn, 'allow_read', 1);
            frappe.model.set_value(cdt, cdn, 'allow_write', 1);
            frappe.model.set_value(cdt, cdn, 'allow_create', 0);
            frappe.model.set_value(cdt, cdn, 'allow_delete', 0);
            frappe.model.set_value(cdt, cdn, 'allow_share', 0);
            frappe.model.set_value(cdt, cdn, 'allow_export', 1);
            frappe.model.set_value(cdt, cdn, 'allow_print', 1);
            frappe.model.set_value(cdt, cdn, 'allow_email', 1);
            frappe.model.set_value(cdt, cdn, 'allow_report', 1);
        } else if (row.permission_level === 'Full') {
            frappe.model.set_value(cdt, cdn, 'allow_read', 1);
            frappe.model.set_value(cdt, cdn, 'allow_write', 1);
            frappe.model.set_value(cdt, cdn, 'allow_create', 1);
            frappe.model.set_value(cdt, cdn, 'allow_delete', 1);
            frappe.model.set_value(cdt, cdn, 'allow_share', 1);
            frappe.model.set_value(cdt, cdn, 'allow_export', 1);
            frappe.model.set_value(cdt, cdn, 'allow_print', 1);
            frappe.model.set_value(cdt, cdn, 'allow_email', 1);
            frappe.model.set_value(cdt, cdn, 'allow_report', 1);
        }
    }
});

function preview_workflow(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Workflow Preview'),
        fields: [
            { fieldtype: 'HTML', fieldname: 'workflow_preview' }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            dialog.hide();
        }
    });

    const workflow_html = generate_workflow_preview(frm.doc);
    dialog.get_field('workflow_preview').$wrapper.html(workflow_html);
    dialog.show();
}

function generate_workflow_preview(workflow) {
    let html = '<div class="workflow-preview">';
    html += '<h3>' + workflow.workflow_name + '</h3>';
    html += '<p>' + (workflow.description || '') + '</p>';

    // Add workflow metadata
    html += '<div class="workflow-meta">';
    html += '<p><strong>' + __('Document Type') + ':</strong> ' + workflow.document_type + '</p>';
    html += '<p><strong>' + __('Status') + ':</strong> ' + (workflow.is_active ? __('Active') : __('Inactive')) + '</p>';
    html += '<p><strong>' + __('Default') + ':</strong> ' + (workflow.is_default ? __('Yes') : __('No')) + '</p>';
    html += '<p><strong>' + __('Allow Parallel Steps') + ':</strong> ' + (workflow.allow_parallel_steps ? __('Yes') : __('No')) + '</p>';
    html += '<p><strong>' + __('Auto Start on Document Creation') + ':</strong> ' + (workflow.auto_start_on_creation ? __('Yes') : __('No')) + '</p>';
    html += '</div>';

    if (workflow.steps && workflow.steps.length > 0) {
        html += '<div class="workflow-steps">';
        html += '<h4>' + __('Workflow Steps') + '</h4>';
        html += '<div class="step-container">';

        const sorted_steps = workflow.steps.sort((a, b) => a.step_order - b.step_order);

        sorted_steps.forEach((step, index) => {
            html += '<div class="step ' + step.step_type.toLowerCase() + '">';
            html += '<div class="step-number">' + step.step_order + '</div>';
            html += '<div class="step-content">';
            html += '<div class="step-name">' + step.step_name + '</div>';
            html += '<div class="step-type">' + step.step_type + '</div>';
            if (step.description) {
                html += '<div class="step-description">' + step.description + '</div>';
            }
            html += '<div class="step-assignee">' + __('Assignee') + ': ' + get_assignee_display(step) + '</div>';

            // Add step metadata
            if (step.time_limit) {
                html += '<div class="step-meta">' + __('Time Limit') + ': ' + step.time_limit + ' ' + __('hours') + '</div>';
            }
            if (step.timeout_days) {
                html += '<div class="step-meta">' + __('Timeout Days') + ': ' + step.timeout_days + '</div>';
            }
            if (step.escalation_days) {
                html += '<div class="step-meta">' + __('Escalation Days') + ': ' + step.escalation_days + '</div>';
            }

            html += '</div>';
            html += '</div>';

            if (index < sorted_steps.length - 1) {
                html += '<div class="step-arrow">→</div>';
            }
        });

        html += '</div>';
        html += '</div>';
    }

    // Add transitions if any
    if (workflow.transitions && workflow.transitions.length > 0) {
        html += '<div class="workflow-transitions">';
        html += '<h4>' + __('Workflow Transitions') + '</h4>';
        html += '<ul class="transition-list">';
        workflow.transitions.forEach(transition => {
            html += '<li>' + transition.from_step + ' → ' + transition.to_step;
            if (transition.auto_transition) {
                html += ' (' + __('Auto') + ')';
            }
            html += '</li>';
        });
        html += '</ul>';
        html += '</div>';
    }

    // Add conditions if any
    if (workflow.conditions && workflow.conditions.length > 0) {
        html += '<div class="workflow-conditions">';
        html += '<h4>' + __('Workflow Conditions') + '</h4>';
        html += '<ul class="condition-list">';
        workflow.conditions.forEach(condition => {
            html += '<li>' + condition.condition_name + ' (' + condition.condition_type + ')</li>';
        });
        html += '</ul>';
        html += '</div>';
    }

    // Add permissions if any
    if (workflow.permissions && workflow.permissions.length > 0) {
        html += '<div class="workflow-permissions">';
        html += '<h4>' + __('Workflow Permissions') + '</h4>';
        html += '<ul class="permission-list">';
        workflow.permissions.forEach(permission => {
            html += '<li>' + permission.role + ' (' + permission.permission_level + ')</li>';
        });
        html += '</ul>';
        html += '</div>';
    }

    html += '</div>';
    return html;
}

function get_assignee_display(step) {
    if (step.assignee_type === 'None') {
        return __('System');
    } else if (step.assignee_type === 'Role') {
        return __('Role') + ': ' + step.assignee_value;
    } else if (step.assignee_type === 'User') {
        return __('User') + ': ' + step.assignee_value;
    } else if (step.assignee_type === 'Field-based') {
        return __('Field') + ': ' + step.assignee_value;
    } else if (step.assignee_type === 'Dynamic') {
        return __('Dynamic');
    }
    return '';
}

function test_workflow(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Test Workflow'),
        fields: [
            { fieldtype: 'Link', fieldname: 'document', label: __('Test Document'), options: 'Document', reqd: 1 },
            { fieldtype: 'Button', fieldname: 'start_workflow', label: __('Start Workflow') }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            dialog.hide();
        }
    });

    dialog.get_field('start_workflow').$input.on('click', function() {
        const document_name = dialog.get_value('document');
        if (document_name) {
            frappe.call({
                method: 'pwp_project.pwp_project.doctype.workflow_instance.workflow_instance.start_workflow',
                args: {
                    document_name: document_name,
                    workflow_definition: frm.doc.name
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({ message: __('Workflow started successfully'), indicator: 'green' });
                        dialog.hide();
                        frappe.set_route('Form', 'Workflow Instance', r.message);
                    }
                }
            });
        }
    });

    dialog.show();
}

function visualize_workflow(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Workflow Visualization'),
        fields: [
            { fieldtype: 'HTML', fieldname: 'workflow_visualization' }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            dialog.hide();
        }
    });

    const visualization_html = generate_workflow_visualization(frm.doc);
    dialog.get_field('workflow_visualization').$wrapper.html(visualization_html);
    dialog.show();
}

function generate_workflow_visualization(workflow) {
    let html = '<div class="workflow-visualization">';

    if (workflow.steps && workflow.steps.length > 0) {
        const sorted_steps = workflow.steps.sort((a, b) => a.step_order - b.step_order);

        html += '<div class="workflow-diagram">';

        // Create a simple flowchart-like visualization
        sorted_steps.forEach((step, index) => {
            let step_class = 'workflow-step ' + step.step_type.toLowerCase();

            html += '<div class="' + step_class + '">';
            html += '<div class="step-header">' + step.step_name + '</div>';
            html += '<div class="step-body">';
            html += '<div class="step-type">' + step.step_type + '</div>';

            if (step.description) {
                html += '<div class="step-description">' + step.description + '</div>';
            }

            html += '<div class="step-assignee">' + get_assignee_display(step) + '</div>';
            html += '</div>';
            html += '</div>';

            // Add arrow between steps
            if (index < sorted_steps.length - 1) {
                html += '<div class="workflow-arrow">↓</div>';
            }
        });

        html += '</div>';
    } else {
        html += '<p class="text-muted">' + __('No steps defined in this workflow') + '</p>';
    }

    html += '</div>';
    return html;
}
