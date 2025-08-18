frappe.ui.form.on('Workflow Step Condition', {
    refresh: function(frm) {
        if (frm.doc.condition_type === 'Field-based') {
            frm.set_df_property('field_name', 'hidden', 0);
            frm.set_df_property('field_name', 'reqd', 1);
            frm.set_df_property('operator', 'hidden', 0);
            frm.set_df_property('operator', 'reqd', 1);
            frm.set_df_property('value', 'hidden', 0);
            frm.set_df_property('value', 'reqd', 1);
            frm.set_df_property('role', 'hidden', 1);
            frm.set_df_property('role', 'reqd', 0);
        } else if (frm.doc.condition_type === 'Role-based') {
            frm.set_df_property('field_name', 'hidden', 1);
            frm.set_df_property('field_name', 'reqd', 0);
            frm.set_df_property('operator', 'hidden', 1);
            frm.set_df_property('operator', 'reqd', 0);
            frm.set_df_property('value', 'hidden', 1);
            frm.set_df_property('value', 'reqd', 0);
            frm.set_df_property('role', 'hidden', 0);
            frm.set_df_property('role', 'reqd', 1);
        } else {
            frm.set_df_property('field_name', 'hidden', 1);
            frm.set_df_property('field_name', 'reqd', 0);
            frm.set_df_property('operator', 'hidden', 1);
            frm.set_df_property('operator', 'reqd', 0);
            frm.set_df_property('value', 'hidden', 1);
            frm.set_df_property('value', 'reqd', 0);
            frm.set_df_property('role', 'hidden', 1);
            frm.set_df_property('role', 'reqd', 0);
        }
    },
    
    condition_type: function(frm) {
        if (frm.doc.condition_type === 'Field-based') {
            frm.set_value('role', '');
            frm.set_df_property('field_name', 'hidden', 0);
            frm.set_df_property('field_name', 'reqd', 1);
            frm.set_df_property('operator', 'hidden', 0);
            frm.set_df_property('operator', 'reqd', 1);
            frm.set_df_property('value', 'hidden', 0);
            frm.set_df_property('value', 'reqd', 1);
            frm.set_df_property('role', 'hidden', 1);
            frm.set_df_property('role', 'reqd', 0);
        } else if (frm.doc.condition_type === 'Role-based') {
            frm.set_value('field_name', '');
            frm.set_value('operator', '');
            frm.set_value('value', '');
            frm.set_df_property('field_name', 'hidden', 1);
            frm.set_df_property('field_name', 'reqd', 0);
            frm.set_df_property('operator', 'hidden', 1);
            frm.set_df_property('operator', 'reqd', 0);
            frm.set_df_property('value', 'hidden', 1);
            frm.set_df_property('value', 'reqd', 0);
            frm.set_df_property('role', 'hidden', 0);
            frm.set_df_property('role', 'reqd', 1);
        } else {
            frm.set_value('field_name', '');
            frm.set_value('operator', '');
            frm.set_value('value', '');
            frm.set_value('role', '');
            frm.set_df_property('field_name', 'hidden', 1);
            frm.set_df_property('field_name', 'reqd', 0);
            frm.set_df_property('operator', 'hidden', 1);
            frm.set_df_property('operator', 'reqd', 0);
            frm.set_df_property('value', 'hidden', 1);
            frm.set_df_property('value', 'reqd', 0);
            frm.set_df_property('role', 'hidden', 1);
            frm.set_df_property('role', 'reqd', 0);
        }
    }
});